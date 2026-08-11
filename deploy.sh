#!/usr/bin/env bash
#
# All-in-one deployment for DepManagerServer: git, version stamp, build, start, health check.
#
# Migrations, static collection, message compilation and the creation of the first admin
# account are all done by entrypoint.py when the container starts, so this script never
# repeats them. What it does instead is everything that must happen *around* the container.
#
#   ./deploy.sh                  full deployment (pull + stamp + backup + build + up + wait)
#   ./deploy.sh --no-pull        skip the git update
#   ./deploy.sh --no-backup      skip the database snapshot
#   ./deploy.sh --no-cache       rebuild the image from scratch
#   ./deploy.sh --recreate       recreate the container instead of reusing it
#   ./deploy.sh --tests          run the test suite before starting
#   ./deploy.sh --dry-run        print what would run, execute nothing
#   ./deploy.sh check            only look for a pending update, change nothing
#   ./deploy.sh status           service status, deployed version, repository content
#   ./deploy.sh logs [service]   follow the logs
#   ./deploy.sh stop             stop everything
#   ./deploy.sh restart          restart without rebuilding
#   ./deploy.sh backup           snapshot data/packages.db, change nothing else
#   ./deploy.sh tests [app]      run the tests in a throwaway container
#   ./deploy.sh superuser        create an admin account
#   ./deploy.sh shell            Django shell inside the container
#   ./deploy.sh format           run black on the sources
#   ./deploy.sh messages         refresh the translation catalogues (en, fr)
#   ./deploy.sh help             this help
#
# `check` (alias `--check`) exits with a status meant to be scripted:
#   0   already up to date
#   10  an update is pending
#   1   cannot tell (not a git repository, no upstream, fetch failed)
#
# Nothing is installed on this machine: python, django, black and gettext all live in the
# image, and every command below runs inside a container.
#
set -euo pipefail

# The whole script sits inside a brace group because it runs `git pull`, which can rewrite
# this very file. Bash reads a script as it executes it: a file that changes mid-run makes it
# resume at an offset that no longer means anything, silently skipping whole chunks. Wrapping
# everything forces bash to parse the entire block before running its first line.
{

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

SERVICE=ui
# manage.py is reached by its full path: the image ENTRYPOINT is entrypoint.py, which starts
# the whole server, so one-shot commands must bypass it.
MANAGE=(python3 /app/server/scripts/manage.py)
HEALTH_TIMEOUT=180
BACKUP_KEEP=10

PULL=1
BACKUP=1
TESTS=0
RECREATE=0
NO_CACHE=0
DRY_RUN=0

# --- Output ------------------------------------------------------------------

if [ -t 1 ]; then
    C_STEP=$'\033[1;34m'; C_OK=$'\033[0;32m'; C_WARN=$'\033[0;33m'
    C_ERR=$'\033[0;31m'; C_DIM=$'\033[2m'; C_END=$'\033[0m'
else
    C_STEP=""; C_OK=""; C_WARN=""; C_ERR=""; C_DIM=""; C_END=""
fi

step() { printf '\n%s==> %s%s\n' "$C_STEP" "$1" "$C_END"; }
ok()   { printf '%s  ✓ %s%s\n' "$C_OK" "$1" "$C_END"; }
info() { printf '%s  · %s%s\n' "$C_DIM" "$1" "$C_END"; }
warn() { printf '%s  ! %s%s\n' "$C_WARN" "$1" "$C_END"; }
fail() { printf '%s  ✗ %s%s\n' "$C_ERR" "$1" "$C_END" >&2; exit 1; }

# Run a command, or just print it in --dry-run mode.
run() {
    if [ "$DRY_RUN" -eq 1 ]; then
        printf '  [dry-run] %s\n' "$*"
        return 0
    fi
    "$@"
}

# The help text is the file header: one place to keep up to date.
usage() {
    awk 'NR > 1 && /^#/ { sub(/^# ?/, ""); print; next } NR > 1 { exit }' "${BASH_SOURCE[0]}"
}

dc() { docker compose "$@"; }
# Same thing through run(), for the calls that change something: --dry-run must print the
# real command line, not the name of this helper.
run_dc() { run docker compose "$@"; }

# --- Environment -------------------------------------------------------------

# Read a variable from .env, falling back to the given default. Read on demand rather than
# once at start-up: on a fresh clone .env does not exist yet when this script begins, it is
# written below, and a single early read would cache the wrong port.
env_value() {
    local key="$1" default="${2:-}" line
    line="$(grep -E "^${key}=" .env 2>/dev/null | tail -1 || true)"
    if [ -z "$line" ]; then
        printf '%s' "$default"
    else
        printf '%s' "${line#*=}"
    fi
}

port()      { env_value PORT 8180; }
data_uid()  { env_value PUID "$(id -u)"; }
data_gid()  { env_value PGID "$(id -g)"; }

check_tools() {
    command -v docker >/dev/null 2>&1 || fail "docker not found."
    docker compose version >/dev/null 2>&1 \
        || fail "the 'docker compose' plugin is missing (docker-compose v1 is not supported)."
    docker info >/dev/null 2>&1 \
        || fail "the docker daemon is not responding: is it running, and is your account in the docker group?"
    dc config -q || fail "docker-compose.yml is invalid."
    ok "docker responds, the composition is valid"
}

# A .env created before a setting was introduced simply does not have it, and the fallback
# value then applies in silence — which is how a server ends up refusing POST requests
# because DOMAIN_NAME was never there. Keys the sample has and .env lacks are appended;
# keys already present are never touched.
complete_env() {
    local added="" key
    while IFS= read -r key; do
        [ -n "$key" ] || continue
        [ "$key" = "GIT_HASH" ] && continue    # rewritten at every deployment, see stamp_version
        if ! grep -qE "^${key}=" .env; then
            grep -E "^${key}=" .env_sample >> .env
            added="$added $key"
        fi
    done <<< "$(grep -E '^[A-Z_]+=' .env_sample | cut -d= -f1)"
    [ -n "$added" ] && warn "settings added to .env from .env_sample:$added"
    return 0
}

check_env() {
    if [ ! -f .env ]; then
        [ -f .env_sample ] || fail "neither .env nor .env_sample: incomplete checkout."
        sed -e "s/^PUID=.*/PUID=$(id -u)/" -e "s/^PGID=.*/PGID=$(id -g)/" .env_sample > .env
        warn ".env created from .env_sample, with PUID=$(id -u) PGID=$(id -g)"
        fail "edit .env (at least DOMAIN_NAME, ADMIN_NAME, ADMIN_PASSWD) then run again."
    fi
    complete_env

    # DOMAIN_NAME is not cosmetic: it is what CSRF validation compares POST requests
    # against, so a wrong value makes every upload and every form fail at run time only.
    local domain
    domain="$(env_value DOMAIN_NAME)"
    case "$domain" in
        ""|example.com|example.net)
            warn "DOMAIN_NAME is '${domain:-unset}': POST requests (uploads, forms) will be rejected" ;;
        *)  ok "DOMAIN_NAME: $domain" ;;
    esac

    [ "$(env_value ADMIN_PASSWD)" = "admin" ] \
        && warn "ADMIN_PASSWD is still 'admin': change it once the first admin exists"
    [ "$(env_value DEBUG false)" = "true" ] \
        && warn "DEBUG=true: tracebacks are served to visitors, not for a public instance"

    # The container chowns everything under data/ to PUID:PGID. If those are not yours, the
    # uploaded packages stop being yours either, and you can no longer clean the directory.
    if [ "$(data_uid)" != "$(id -u)" ] || [ "$(data_gid)" != "$(id -g)" ]; then
        warn "PUID/PGID in .env are $(data_uid):$(data_gid) but you are $(id -u):$(id -g)"
        info "data/ will not belong to you; fix .env if that is not deliberate"
    fi
    ok ".env present"
}

# data/ is a bind mount and is not versioned. Any of these directories missing when `up`
# runs gets created by Docker **owned by root**; entrypoint.py does chown them back, but
# creating them here first keeps the ownership right from the very first second.
prepare_directories() {
    local created=""
    local dir
    for dir in data data/packages data/log data/migrations data/backup \
               data/_upload/{0,1,2,3,4,5,6,7,8,9}; do
        if [ ! -d "$dir" ]; then
            run mkdir -p "$dir"
            created="$created $dir"
        fi
    done
    [ -n "$created" ] && ok "data directories created:$created"
    return 0
}

# The image bakes server/ in, VERSION included, and settings.py reads version, api_version
# and hash from server/VERSION. So the stamp must be written **before** the build, and after
# the pull: otherwise the UI proudly displays the commit of the previous deployment.
stamp_version() {
    step "Stamping the version"
    local hash="unknown"
    if [ -d .git ]; then
        hash="$(git rev-parse --short HEAD)"
    fi
    if [ "$DRY_RUN" -eq 1 ]; then
        printf '  [dry-run] write server/VERSION (hash: %s) and GIT_HASH in .env\n' "$hash"
        return 0
    fi
    { cat VERSION; printf 'hash: %s\n' "$hash"; } > server/VERSION
    if grep -qE '^GIT_HASH=' .env; then
        sed -i -e "s/^GIT_HASH=.*/GIT_HASH=$hash/" .env
    else
        printf 'GIT_HASH=%s\n' "$hash" >> .env
    fi
    ok "$(grep -E '^version:' VERSION | cut -d: -f2 | tr -d ' ') / api $(grep -E '^api_version:' VERSION | cut -d: -f2 | tr -d ' ') / $hash"
}

# --- Database snapshot -------------------------------------------------------

# packages.db holds the users, the package index and every setting: it is the only piece of
# state a rebuild could not reconstruct. entrypoint.py runs makemigrations *and* migrate at
# every start, so a deployment does touch the schema — hence a snapshot beforehand.
backup_database() {
    step "Snapshotting the database"
    if [ ! -f data/packages.db ]; then
        info "no data/packages.db yet: nothing to snapshot"
        return 0
    fi
    local stamp target
    stamp="$(date '+%Y%m%d-%H%M%S')"
    target="data/backup/packages-${stamp}.db"
    [ -d data/backup ] || run mkdir -p data/backup
    if [ "$DRY_RUN" -eq 1 ]; then
        printf '  [dry-run] snapshot data/packages.db -> %s\n' "$target"
        return 0
    fi

    # A live SQLite file copied with `cp` can catch a write halfway through. When the
    # container is up we go through the sqlite backup API instead, which takes a consistent
    # snapshot of a database in use. Run under PUID:PGID so the copy belongs to the owner
    # of data/, not to root.
    if [ -n "$(dc ps -q "$SERVICE" 2>/dev/null)" ]; then
        dc exec -T --user "$(data_uid):$(data_gid)" "$SERVICE" python3 -c "
import sqlite3
src = sqlite3.connect('/app/data/packages.db')
dst = sqlite3.connect('/app/$target')
src.backup(dst)
dst.close(); src.close()
" || fail "the snapshot failed: refusing to deploy over a database with no backup."
        ok "consistent snapshot (service running): $target"
    else
        cp data/packages.db "$target" || fail "could not copy data/packages.db."
        ok "snapshot (service stopped): $target"
    fi

    # Keep the last few and no more: these files grow with the repository.
    local old
    old="$(ls -1t data/backup/packages-*.db 2>/dev/null | tail -n "+$((BACKUP_KEEP + 1))" || true)"
    if [ -n "$old" ]; then
        printf '%s\n' "$old" | xargs -r rm -f
        info "$(printf '%s\n' "$old" | wc -l) old snapshot(s) removed (keeping $BACKUP_KEEP)"
    fi
}

# --- Repository --------------------------------------------------------------

update_repository() {
    step "Updating the repository"
    if [ ! -d .git ]; then
        warn "not a git repository, skipping the update"
        return 0
    fi
    if ! git rev-parse --abbrev-ref '@{upstream}' >/dev/null 2>&1; then
        warn "branch $(git branch --show-current) tracks no upstream, skipping the update"
        return 0
    fi
    if [ -n "$(git status --porcelain)" ]; then
        git status --short
        fail "the repository has local changes: commit them, stash them, or use --no-pull."
    fi

    local before fingerprint
    before="$(git rev-parse HEAD)"
    fingerprint="$(sha256sum "${BASH_SOURCE[0]}" | cut -d' ' -f1)"
    run git pull --ff-only || fail "the pull failed (diverged? conflict?)."
    [ "$DRY_RUN" -eq 1 ] && return 0

    # The pull may have brought a new setting: complete .env now rather than one deployment
    # later, since the sample is what the pull just updated.
    complete_env

    # The pull may also have renamed or deleted this script. Say so, instead of dying on an
    # unreadable file in the middle of its own deployment.
    if [ ! -f "${BASH_SOURCE[0]}" ]; then
        if [ -x "$ROOT/deploy.sh" ]; then
            warn "this script was renamed by the pull: resuming with $ROOT/deploy.sh"
            export DEPLOY_RESTARTED=1
            exec "$ROOT/deploy.sh" ${ORIGINAL_ARGS[@]+"${ORIGINAL_ARGS[@]}"}
        fi
        fail "this script vanished from the repository during the pull: start the new one by hand."
    fi

    # It may also have rewritten this very script. Whatever fix it carries must apply to
    # *this* run, not the next one, so we start over with the new version. The guard rules
    # out an endless loop if the file keeps changing.
    if [ "$(sha256sum "${BASH_SOURCE[0]}" | cut -d' ' -f1)" != "$fingerprint" ]; then
        [ "${DEPLOY_RESTARTED:-0}" = 1 ] \
            && fail "deploy.sh changes on every restart: stopping as a precaution."
        warn "deploy.sh was updated by this pull: restarting with the new version"
        export DEPLOY_RESTARTED=1
        exec "${BASH_SOURCE[0]}" ${ORIGINAL_ARGS[@]+"${ORIGINAL_ARGS[@]}"}
    fi

    local after
    after="$(git rev-parse HEAD)"
    if [ "$before" = "$after" ]; then
        ok "already up to date ($(git rev-parse --short HEAD))"
    else
        ok "updated: $(git rev-parse --short "$before") -> $(git rev-parse --short "$after")"
        git --no-pager log --oneline "$before..$after" | head -10 | sed 's/^/       /'
    fi
}

# Report whether the remote is ahead, and touch nothing else. `git fetch` only writes
# remote-tracking refs, never the working tree, so this is safe to run on a schedule — and
# Docker is deliberately not involved: knowing whether there is something new must not
# depend on the daemon.
check_update() {
    step "Checking for a pending update"
    [ -d .git ] || fail "not a git repository, cannot check for updates."

    local branch upstream
    branch="$(git rev-parse --abbrev-ref HEAD)"
    # On a branch with no upstream, `git rev-parse` writes its complaint to stderr but still
    # echoes '@{upstream}' verbatim on stdout, exit code included in the command substitution.
    # Testing the emptiness of the result is therefore not enough: the literal must be caught
    # too, or the comparison below runs on a revision that does not exist.
    upstream="$(git rev-parse --abbrev-ref --symbolic-full-name '@{upstream}' 2>/dev/null || true)"
    if [ -z "$upstream" ] || [ "$upstream" = "@{upstream}" ]; then
        fail "branch '$branch' tracks no upstream: nothing to compare against."
    fi

    if [ "$DRY_RUN" -eq 1 ]; then
        printf '  [dry-run] git fetch --quiet\n'
        warn "comparing against the remote refs already on disk"
    else
        git fetch --quiet || fail "git fetch failed: is the remote reachable?"
    fi

    local behind ahead
    read -r behind ahead <<< "$(git rev-list --left-right --count "${upstream}...HEAD")"
    ok "branch '$branch' tracking '$upstream'"

    # Said *before* the verdict: uncommitted changes block the pull, so announcing "there is
    # something new" without mentioning them would send you straight into a wall.
    if [ -n "$(git status --porcelain)" ]; then
        warn "local changes are not committed: a deployment would need --no-pull"
        git status --short | head -8 | sed 's/^/       /'
    fi
    [ "$ahead" -gt 0 ] && warn "$ahead local commit(s) not pushed"

    if [ "$behind" -eq 0 ]; then
        ok "up to date ($(git rev-parse --short HEAD))"
        return 0
    fi
    if [ "$ahead" -gt 0 ]; then
        warn "branches have diverged: $behind incoming, $ahead local commit(s)"
    else
        warn "$behind commit(s) pending"
    fi
    git --no-pager log --oneline --no-decorate "HEAD..${upstream}" | head -10 | sed 's/^/       /'

    # What changes tells whether to deploy now or let it wait: a template tweak and a change
    # to entrypoint.py or to the nginx configuration do not carry the same risk.
    info "$(git diff --name-only "HEAD..${upstream}" | wc -l) file(s) would change"
    local pattern count
    for pattern in entrypoint.py Dockerfile docker-compose.yml deploy.sh requirements.txt \
                   server/config/ server/scripts/ server/locale/; do
        count="$(git diff --name-only "HEAD..${upstream}" -- "$pattern" | wc -l)"
        [ "$count" -gt 0 ] && info "  $pattern → $count file(s)"
    done
    printf '\n   %sTo apply:%s ./deploy.sh\n' "$C_DIM" "$C_END"
    exit 10
}

# --- Build and start ---------------------------------------------------------

build_image() {
    step "Building the image"
    if [ "$NO_CACHE" -eq 1 ]; then
        run_dc build --no-cache
    else
        run_dc build
    fi
    ok "image built (the running one kept serving meanwhile)"
}

run_tests() {
    local target="${1:-}"
    step "Tests${target:+ ($target)}"
    # A throwaway container, no published port: the Django test runner builds its own
    # in-memory SQLite database, so this touches neither data/packages.db nor the service.
    run_dc run --rm -T --no-deps --entrypoint python3 "$SERVICE" \
        "${MANAGE[@]:1}" test ${target:+"$target"} --noinput
    ok "tests passed"
}

start_services() {
    step "Starting the service"
    if [ "$RECREATE" -eq 1 ]; then
        info "recreation requested: full shutdown first"
        run_dc down --remove-orphans
        run_dc up -d --force-recreate
    else
        [ -n "$(dc ps -q "$SERVICE" 2>/dev/null)" ] \
            && info "the service is running: an unchanged container would be reused"
        run_dc up -d
    fi
    ok "service started"
}

# --- Health ------------------------------------------------------------------

# Ask the app itself, over the published port when curl is available — that is the path a
# real client takes. Without curl, probe from inside the container, which at least proves
# nginx and gunicorn are both answering.
http_status() {
    if command -v curl >/dev/null 2>&1; then
        curl -sS -m 10 -o /dev/null -w '%{http_code}' "http://127.0.0.1:$(port)/" 2>/dev/null || printf '000'
        return 0
    fi
    if dc exec -T "$SERVICE" python3 -c \
        "import urllib.request; urllib.request.urlopen('http://127.0.0.1:80/', timeout=5)" \
        >/dev/null 2>&1; then
        printf '200'
    else
        printf '000'
    fi
}

# entrypoint.py never lets the container die: on any failure it calls fall_back(), which
# sleeps forever. So a container reported "running" proves nothing at all — the only way to
# tell a working server from a dead one is to read what the entrypoint said on its way down.
check_fallback() {
    if dc logs --tail 200 "$SERVICE" 2>/dev/null | grep -q 'Falling back'; then
        printf '\n'
        dc logs --tail 40 "$SERVICE" || true
        fail "entrypoint.py fell back: the container is alive but serves nothing (see above)."
    fi
}

# The image carries server/ inside it, so a container started from a stale image serves
# stale code without a word. Compare the stamp on disk with the one being served.
check_served_version() {
    local inside outside
    inside="$(dc exec -T "$SERVICE" cat /app/server/VERSION 2>/dev/null | tr -d '\r' || true)"
    outside="$(cat server/VERSION 2>/dev/null || true)"
    if [ -z "$inside" ]; then
        warn "could not read the version inside the container"
        return 0
    fi
    if [ "$inside" != "$outside" ]; then
        warn "the container serves another version than the sources on disk:"
        printf '%s\n' "$inside" | sed 's/^/       container: /'
        printf '%s\n' "$outside" | sed 's/^/       disk:      /'
        info "the image was not rebuilt; retry with --recreate"
        return 0
    fi
    ok "served version matches the sources ($(grep -E '^hash:' server/VERSION | cut -d: -f2 | tr -d ' '))"
}

check_health() {
    step "Checking health"
    if [ "$DRY_RUN" -eq 1 ]; then
        printf '  [dry-run] would wait up to %ss for %s to answer\n' "$HEALTH_TIMEOUT" "$SERVICE"
        return 0
    fi

    local cid
    cid="$(dc ps -q "$SERVICE" 2>/dev/null || true)"
    [ -n "$cid" ] || fail "service $SERVICE did not start."

    local elapsed=0 status code
    while [ "$elapsed" -lt "$HEALTH_TIMEOUT" ]; do
        status="$(docker inspect -f '{{.State.Status}}' "$cid")"
        if [ "$status" != "running" ]; then
            printf '\n'
            dc logs --tail 40 "$SERVICE" || true
            fail "the container is '$status' (see the logs above)."
        fi
        check_fallback
        code="$(http_status)"
        if [ "$code" = "200" ]; then
            printf '\r\033[K'
            ok "the server answers on http://127.0.0.1:$(port)/ (200)"
            check_served_version
            return 0
        fi
        sleep 3
        elapsed=$((elapsed + 3))
        # The first start is the slow one: migrations, collectstatic and compilemessages all
        # run before gunicorn binds.
        printf '\r  ... starting up: %s (%ss)' "${code:-none}" "$elapsed"
    done
    printf '\n'
    dc logs --tail 40 "$SERVICE" || true
    fail "$SERVICE did not answer within ${HEALTH_TIMEOUT}s."
}

# --- Reporting ---------------------------------------------------------------

show_status() {
    step "Service status"
    dc ps --format '  {{.Service}}\t{{.Status}}\t{{.Ports}}' 2>/dev/null || dc ps

    step "Version"
    if [ -f server/VERSION ]; then
        sed 's/^/  · /' server/VERSION
    else
        warn "server/VERSION missing: never stamped, run ./deploy.sh"
    fi
    [ -d .git ] && info "commit: $(git log -1 --format='%h %s (%ar)' 2>/dev/null || echo unknown)"

    step "Repository content"
    if [ -d data/packages ]; then
        info "$(find data/packages -type f | wc -l) package file(s), $(du -sh data/packages 2>/dev/null | cut -f1)"
    else
        warn "data/packages missing"
    fi
    [ -f data/packages.db ] && info "database: $(du -h data/packages.db | cut -f1)"
    if [ -d data/backup ] && [ -n "$(ls -1 data/backup 2>/dev/null)" ]; then
        info "last snapshot: $(ls -1t data/backup/packages-*.db 2>/dev/null | head -1)"
    else
        warn "no database snapshot yet"
    fi
    # Uploads land in data/_upload/N and are moved once the package is registered. Leftovers
    # there mean uploads that were interrupted, or failed to register.
    local pending
    pending="$(find data/_upload -type f 2>/dev/null | wc -l)"
    [ "$pending" -gt 0 ] && warn "$pending file(s) left in data/_upload (interrupted uploads)"
    return 0
}

summary() {
    step "Deployed"
    dc ps --format '  {{.Service}}\t{{.Status}}' 2>/dev/null || true
    printf '\n'
    ok "server available at http://localhost:$(port)/"
    printf '     admin:   http://localhost:%s/admin/\n' "$(port)"
    printf '     %slogs:%s ./deploy.sh logs   ·   %sstatus:%s ./deploy.sh status   ·   %sstop:%s ./deploy.sh stop\n' \
        "$C_DIM" "$C_END" "$C_DIM" "$C_END" "$C_DIM" "$C_END"
}

deploy() {
    step "Deploying DepManagerServer"
    [ "$DRY_RUN" -eq 1 ] && warn "--dry-run mode: no command is executed"
    check_tools
    check_env
    prepare_directories
    [ "$PULL" -eq 1 ] && update_repository
    stamp_version
    [ "$BACKUP" -eq 1 ] && backup_database
    build_image
    [ "$TESTS" -eq 1 ] && run_tests
    start_services
    check_health
    [ "$DRY_RUN" -eq 0 ] && summary
    return 0
}

# --- Entry point -------------------------------------------------------------

ORIGINAL_ARGS=("$@")
COMMAND="deploy"
ARGUMENT=""

while [ $# -gt 0 ]; do
    case "$1" in
        --no-pull)   PULL=0 ;;
        --no-backup) BACKUP=0 ;;
        --tests)     TESTS=1 ;;
        --recreate)  RECREATE=1 ;;
        --no-cache)  NO_CACHE=1 ;;
        --dry-run)   DRY_RUN=1 ;;
        --check)     COMMAND="check" ;;
        -h|--help|help) usage; exit 0 ;;
        deploy|check|status|logs|stop|restart|backup|tests|superuser|shell|format|messages)
            COMMAND="$1"
            if [ $# -gt 1 ] && [[ "$2" != -* ]]; then
                ARGUMENT="$2"
                shift
            fi
            ;;
        *) fail "unknown argument: $1 (see ./deploy.sh help)" ;;
    esac
    shift
done

case "$COMMAND" in
    deploy)  deploy ;;
    check)   check_update ;;
    status)  check_tools; show_status ;;
    logs)    dc logs -f ${ARGUMENT:+"$ARGUMENT"} ;;
    stop)    step "Stopping"; dc down --remove-orphans; ok "service stopped" ;;
    restart) step "Restarting"; dc restart; check_health; summary ;;
    backup)  check_tools; backup_database ;;
    tests)   check_tools; check_env; run_tests "$ARGUMENT" ;;

    superuser) dc exec "$SERVICE" "${MANAGE[@]}" createsuperuser ;;
    shell)     dc exec "$SERVICE" "${MANAGE[@]}" shell ;;

    # black and gettext are in the image and nowhere else. The sources are mounted so the
    # results land on the host, and the container runs under your own ids so the rewritten
    # files stay yours.
    format)
        step "Formatting with black"
        dc run --rm -T --no-deps --user "$(id -u):$(id -g)" \
            -v "$ROOT:/work" -w /work --entrypoint black "$SERVICE" server entrypoint.py
        ok "sources formatted" ;;
    messages)
        step "Refreshing the translation catalogues"
        dc run --rm -T --no-deps --user "$(id -u):$(id -g)" \
            -v "$ROOT/server:/app/server" -w /app/server/scripts \
            --entrypoint python3 "$SERVICE" manage.py makemessages -l en -l fr
        ok "server/locale updated (compiled at container start)" ;;
esac

}
