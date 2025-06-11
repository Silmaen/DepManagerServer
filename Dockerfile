FROM alpine:3.21

# environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONOPTIMIZE=1

# Ports
EXPOSE 80

# copy the data
COPY bootstrap /bootstrap
COPY server /server

# Entry point
ENTRYPOINT ["/bootstrap/start.py"]

# Volumes
VOLUME ["/data"]

# Run installation script
RUN /bin/sh /bootstrap/install.sh
