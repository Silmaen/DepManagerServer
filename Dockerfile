FROM alpine
ENV PYTHONUNBUFFERED 1
EXPOSE 80
ENTRYPOINT ["/bootstrap/start.py"]
VOLUME ["/data"]
COPY bootstrap /bootstrap
COPY server /server
RUN /bin/sh /bootstrap/install.sh
