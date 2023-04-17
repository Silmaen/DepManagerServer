FROM registry.argawaen.net/base_django_server
ENV PYTHONUNBUFFERED 1
EXPOSE 80
ENTRYPOINT ["python3 /bootstrap/start.py"]
VOLUME ["/server/data"]
COPY bootstrap /
RUN /bootstrap/install.sh
COPY server /
