FROM python:3.12-slim

WORKDIR /app

# Copy shared library
COPY shared /app/shared

# Copy service dependencies
COPY services/feed-service/requirements.txt /app/services/feed-service/requirements.txt
RUN pip install --no-cache-dir -r services/feed-service/requirements.txt

# Copy service code
COPY services/feed-service /app/services/feed-service

ENV PYTHONPATH=/app

WORKDIR /app/services/feed-service

CMD ["uvicorn", "app.core.main:app", "--host", "0.0.0.0", "--port", "8000"]
