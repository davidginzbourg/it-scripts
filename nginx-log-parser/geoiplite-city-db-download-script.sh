#!/usr/bin/env bash

mkdir -p /root/nginx_logrotate_python
wget http://geolite.maxmind.com/download/geoip/database/GeoLite2-City.tar.gz -q -O /root/nginx_logrotate_python/GeoLite2-City.tar.gz
tar -zxf /root/nginx_logrotate_python/GeoLite2-City.tar.gz --strip-components 1
rm /root/nginx_logrotate_python/GeoLite2-City.tar.gz