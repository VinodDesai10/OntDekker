FROM python:3.12-slim

WORKDIR /app

# Copy shared library
COPY shared /app/shared

# Copy service dependencies
COPY services/notification-service/requirements.txt /app/services/notification-service/requirements.txt
RUN pip install --no-cache-dir -r services/notification-service/requirements.txt

# Copy service code
COPY services/notification-service /app/services/notification-service

ENV PYTHONPATH=/app

WORKDIR /app/services/notification-service

CMD ["uvicorn", "app.core.main:app", "--host", "0.0.0.0", "--port", "8000"]
