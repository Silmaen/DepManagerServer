# Instructions for GitHub Copilot

## General

- All comments and documentation must be in English
- All messages shown to users must be in English
- Write clear, concise, and descriptive comments
- use Docstrings with format reStructuredText (reST)
- Follow PEP 8 conventions
- Prefer type hints for all functions

## Project conventions

- Use `pathlib.Path` rather than `os.path`
- Use `depmanager.api.internal.messaging.log` for logging
- Log levels : `log.debug()`, `log.info()`, `log.warn()`, `log.error()`, `log.fatal()`

## Security

- Never store plaintext credentials
- Never log sensitive information in plaintext (replace by '*')
- Usu `PasswordManager` for credential storage
- Strict permissions for sensitive files (0o600)

## UI

- Use `rich` for progress bar
- Format : `SpinnerColumn`, `TextColumn`, `BarColumn`, `DownloadColumn`, `TransferSpeedColumn`

## Error handling

- Always catch exceptions with clear message
- Log error with complete traceback
- Return `False` or `None` in case of failure, never raise unless critical

## Code style

- Variable names in snake_case
- Class name in PascalCase
- Limit 88 char per line (Black formatter)
