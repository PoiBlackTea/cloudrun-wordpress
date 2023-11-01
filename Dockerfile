FROM bitnami/wordpress-nginx



## Change user to perform privileged actions
## Install
USER root
COPY run.sh /opt/bitnami/scripts/nginx-php-fpm/run.sh
RUN install_packages nfs-common && \
    usermod -a -G root daemon && \
    chmod 755 /opt/bitnami/scripts/nginx-php-fpm/run.sh