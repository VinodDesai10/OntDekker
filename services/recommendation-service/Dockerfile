FROM python:3.12-slim

WORKDIR /app

# Copy shared library
COPY shared /app/shared

# Copy service dependencies
COPY services/recommendation-service/requirements.txt /app/services/recommendation-service/requirements.txt
RUN pip install --no-cache-dir -r services/recommendation-service/requirements.txt

# Copy service code
COPY services/recommendation-service /app/services/recommendation-service

ENV PYTHONPATH=/app

WORKDIR /app/services/recommendation-service

CMD ["uvicorn", "app.core.main:app", "--host", "0.0.0.0", "--port", "8000"]
