FROM mysql:5.7

ENV MYSQL_ROOT_PASSWORD=mysql_rOOt_passwd100000
ENV MYSQL_DATABASE=tagger
ENV MYSQL_USER=tagger_client
ENV MYSQL_PASSWORD=izzDARu11dul

ADD ["backup/backup.sql.gz", "/docker-entrypoint-initdb.d/backup.sql.gz"]