FROM postgis/postgis:16-3.4

# The base image is Debian bullseye. The live PostgreSQL apt repository
# (apt.postgresql.org) dropped bullseye, so `apt-get update` fails against it.
# The archive repository is frozen and still serves bullseye-pgdg, including
# postgresql-16-pgvector. Moving to a newer base image is the owner's decision,
# because it changes the image the development database volume was created with.
RUN sed -i 's|http://apt.postgresql.org/|http://apt-archive.postgresql.org/|' \
       /etc/apt/sources.list.d/*.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
       postgresql-16-pgvector \
    && rm -rf /var/lib/apt/lists/*
