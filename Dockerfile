FROM python:3.12-alpine

WORKDIR /app

# environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONOPTIMIZE=1

COPY requirements.txt .
RUN apk add --no-cache \
    nginx-mod-http-upload \
    nginx-mod-stream \
    nginx-mod-http-upload-progress \
    nginx-mod-http-encrypted-session \
    tzdata \
    gettext \
    && pip install --no-cache-dir -r requirements.txt

# Ajouter le script d'initialisation et le rendre exécutable
COPY entrypoint.py /entrypoint.py
RUN chmod +x /entrypoint.py

COPY ./server ./server

ENTRYPOINT ["/entrypoint.py"]
