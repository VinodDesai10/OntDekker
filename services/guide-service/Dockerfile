FROM python:3.12-slim

WORKDIR /app

# Install postgresql-client for pg_isready (used by the entrypoint health check)
RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy shared library
COPY shared /app/shared

# Copy service dependencies and install
COPY services/guide-service/requirements.txt /app/services/guide-service/requirements.txt
RUN pip install --no-cache-dir -r services/guide-service/requirements.txt

# Copy service code
COPY services/guide-service /app/services/guide-service

# Copy startup entrypoint
COPY scripts/entrypoint-guide.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENV PYTHONPATH=/app

WORKDIR /app/services/guide-service

ENTRYPOINT ["/entrypoint.sh"]
