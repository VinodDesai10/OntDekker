FROM python:3.12-slim

WORKDIR /app

# Copy shared library
COPY shared /app/shared

# Copy service dependencies
COPY services/community-service/requirements.txt /app/services/community-service/requirements.txt
RUN pip install --no-cache-dir -r services/community-service/requirements.txt

# Copy service code
COPY services/community-service /app/services/community-service

ENV PYTHONPATH=/app

WORKDIR /app/services/community-service

CMD ["uvicorn", "app.core.main:app", "--host", "0.0.0.0", "--port", "8000"]
