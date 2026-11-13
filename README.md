# MazaoX — Your Agricultural Marketplace

Kenyan agricultural produce marketplace (academic prototype). Django + Django REST Framework,
PostgreSQL, React frontend (later phase). Payments are **simulated only**.

Architecture: service-oriented modular monolith (one Django project, one app per domain,
communication through `services.py` / `selectors.py` only).

## Run with Docker (API + database + scheduler)
```bash
cp .env.example .env            # then set real local values
docker compose up -d --build    # db :5433, API :8010 (override with BACKEND_PORT), scheduler
curl http://localhost:8010/api/v1/health
```
The backend image runs gunicorn as a non-root user and applies migrations on start
(`RUN_MIGRATIONS=true` in compose; remove it to migrate manually). The `scheduler`
service runs `manage.py expire_reservations` every minute. Uploaded media lives in the
`mazaox_media` volume. The Django admin has no CSS in the container (no static-file server yet).

## Run locally (without Docker for the API)
```bash
cp .env.example .env
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements-dev.txt
docker compose up -d db         # PostgreSQL on localhost:5433
cd backend
python manage.py migrate
python manage.py runserver 8010
python -m pytest
```
