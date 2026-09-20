FROM python:3.12-slim

WORKDIR /app

# Copy shared library
COPY shared /app/shared

# Copy service dependencies
COPY services/authentication-service/requirements.txt /app/services/authentication-service/requirements.txt
RUN pip install --no-cache-dir -r services/authentication-service/requirements.txt

# Copy service code
COPY services/authentication-service /app/services/authentication-service

ENV PYTHONPATH=/app

WORKDIR /app/services/authentication-service

CMD ["uvicorn", "app.core.main:app", "--host", "0.0.0.0", "--port", "8000"]
