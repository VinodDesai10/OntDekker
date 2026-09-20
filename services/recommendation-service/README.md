# Recommendation Service

## 👤 Ownership & Domain Info
- **Owner:** Shared
- **Database:** `recommendation_db`
- **Core Domain:** Personalized story ranking & interest profiles

---

## 🚪 Boundaries & Communication

### REST Endpoint Prefix
Exposed publicly at `/api/v1/recommendation/*` (routed and stripped by Traefik API Gateway).

### Permitted DB Access
This service owns database `recommendation_db`. It is strictly prohibited for any other service to directly query or write to this database.

### Kafka Event Publishing
Publishes events on topic `recommendation-events`. Check event contracts in `shared/events/models.py`.

---

## 🚀 Running the Service

### Run Local (Development)
1. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Copy env vars and customize:
   ```bash
   cp .env.example .env
   ```
3. Run the FastAPI development server:
   ```bash
   PYTHONPATH=../.. uvicorn app.core.main:app --reload --port 8000
   ```

### Run inside Docker
Build and start the container using Docker Compose from the project root:
```bash
docker compose up recommendation --build
```

---

## 🗄 Database Migrations (Alembic)

To generate a new database migration script after altering models:
```bash
alembic revision --autogenerate -m "description_of_change"
```

To apply migrations locally:
```bash
alembic upgrade head
```

---

## 🧪 Testing

Run pytest from the service directory:
```bash
PYTHONPATH=../.. pytest
```
