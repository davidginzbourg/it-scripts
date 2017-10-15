## Simple script to upload compressed log files to S3
In this example we are rotating logs for Vault and uploading the lateset file to S3

### Logrotate config
_vi /etc/logrotate.conf_
```
    /var/log/vault.audit {
        missingok
        copytruncate
        daily
        compress
        create 0666 root root
        rotate 365
    }
```
### Have crontab run the script daily
_crontab -e_
```
0 06 * * * /usr/bin/python /home/ubuntu/upload_vault_audit_log.py
```
