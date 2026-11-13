# MazaoX — Your Agricultural Marketplace

Kenyan agricultural produce marketplace (academic prototype). Django + Django REST Framework,
PostgreSQL, React frontend (later phase). Payments are **simulated only**.

Architecture: service-oriented modular monolith (one Django project, one app per domain,
communication through `services.py` / `selectors.py` only).

## Run locally
```bash
cp .env.example .env            # then set real local values
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
docker compose up -d db         # PostgreSQL on localhost:5433
cd backend
python manage.py runserver 8010
curl http://localhost:8010/api/v1/health
python -m pytest
```
