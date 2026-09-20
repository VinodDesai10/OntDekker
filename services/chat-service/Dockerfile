FROM python:3.12-slim

WORKDIR /app

# Copy shared library
COPY shared /app/shared

# Copy service dependencies
COPY services/chat-service/requirements.txt /app/services/chat-service/requirements.txt
RUN pip install --no-cache-dir -r services/chat-service/requirements.txt

# Copy service code
COPY services/chat-service /app/services/chat-service

ENV PYTHONPATH=/app

WORKDIR /app/services/chat-service

CMD ["uvicorn", "app.core.main:app", "--host", "0.0.0.0", "--port", "8000"]
