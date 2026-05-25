FROM alpine:3.20

RUN apk add --no-cache bash postgresql16-client tar gzip findutils

COPY backup.sh /usr/local/bin/backup.sh
RUN chmod +x /usr/local/bin/backup.sh

CMD ["crond", "-f", "-d", "8"]
