FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gdal-bin \
    libgdal-dev \
    libgeos-dev \
    libproj-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements/ /app/requirements/
RUN pip install --no-cache-dir -r requirements/local.txt

COPY . /app/

COPY compose/django/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

COPY compose/django/start.sh /start.sh
RUN chmod +x /start.sh

ENTRYPOINT ["/entrypoint.sh"]
