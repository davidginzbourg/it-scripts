#!/usr/bin/env bash

wget https://iptoasn.com/data/ip2asn-v4.tsv.gz -q -O /root/nginx_logrotate_python/ip2asn-v4.tsv.gz
gunzip -dfq /root/nginx_logrotate_python/ip2asn-v4.tsv.gz
python /root/nginx_logrotate_python/cidr_to_org_db_creator.py /root/nginx_logrotate_python/ip2asn-v4.tsv /root/nginx_logrotate_python/cidr_to_org_db.json