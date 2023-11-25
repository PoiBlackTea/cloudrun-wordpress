# syntax=docker/dockerfile:1
FROM bitnami/wordpress-nginx:6.4.1


## Change user to perform privileged actions
## Install
USER root
COPY --chmod=755 --link run.sh /opt/bitnami/scripts/nginx-php-fpm/run.sh
RUN install_packages nfs-common && \
    usermod -a -G root daemon