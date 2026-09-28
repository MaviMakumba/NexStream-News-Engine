FROM alpine:3.20

# gnupg: yedek şifreleme (opt-in, BACKUP_GPG_PASSPHRASE)
# rclone: offsite upload (opt-in, RCLONE_REMOTE + mounted rclone.conf) — S3/B2/vb.
# tek bir araçla çok sağlayıcı desteklediği için tercih edildi, sağlayıcı kilitlemez.
RUN apk add --no-cache bash postgresql16-client tar gzip findutils gnupg rclone

COPY backup.sh /usr/local/bin/backup.sh
RUN chmod +x /usr/local/bin/backup.sh
# busybox crond root'a ait OLMAYAN crontab'ları sessizce yok sayar — host'tan
# bind-mount edilen dosya uid 1000'e aitti, 28 Tem-28 Eyl 2026 arası tek bir
# zamanlanmış yedek alınmadı. COPY root sahipliğiyle yazar.
COPY crontab /etc/crontabs/root

CMD ["crond", "-f", "-d", "8"]
