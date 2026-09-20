FROM python:3.12-slim

WORKDIR /app

# Copy shared library
COPY shared /app/shared

# Copy service dependencies
COPY services/user-service/requirements.txt /app/services/user-service/requirements.txt
RUN pip install --no-cache-dir -r services/user-service/requirements.txt

# Copy service code
COPY services/user-service /app/services/user-service

ENV PYTHONPATH=/app

WORKDIR /app/services/user-service

CMD ["uvicorn", "app.core.main:app", "--host", "0.0.0.0", "--port", "8000"]
