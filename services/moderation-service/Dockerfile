FROM python:3.12-slim

WORKDIR /app

# Copy shared library
COPY shared /app/shared

# Copy service dependencies
COPY services/moderation-service/requirements.txt /app/services/moderation-service/requirements.txt
RUN pip install --no-cache-dir -r services/moderation-service/requirements.txt

# Copy service code
COPY services/moderation-service /app/services/moderation-service

ENV PYTHONPATH=/app

WORKDIR /app/services/moderation-service

CMD ["uvicorn", "app.core.main:app", "--host", "0.0.0.0", "--port", "8000"]
