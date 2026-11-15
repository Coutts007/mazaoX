# MazaoX — Your Agricultural Marketplace

Kenyan agricultural produce marketplace (academic prototype). Farmers publish listings and manage stock,
buyers search, order and pay (**simulated payments only**), administrators moderate. This repository is the
**backend** (Django + Django REST Framework + PostgreSQL + Redis); the React frontend comes next.

## Architecture
Service-oriented modular monolith: one Django project, one PostgreSQL database, one app per domain under
`backend/apps/`. Domains talk only through each other's `services.py` (writes) and `selectors.py` (reads);
a test (`core/tests/test_boundaries.py`) fails if a domain imports another domain's models.

| Domain app | Owns |
|---|---|
| identity | accounts, roles, JWT auth |
| profiles | farmer/buyer profile, public farmer page |
| catalogue | categories, listings, photos, moderation flags |
| inventory | stock, movements, expiring reservations |
| orders | orders, lines, status history, cancellation/expiry |
| payments | simulated payment attempts |
| notifications | in-app notifications |
| delivery | delivery records and status flow |
| reviews | verified-purchase reviews |
| issues | order issues and resolution |
| quality | independent inspection records |
| demand | buyer demand requests and matching |
| audit / administration | audit log, admin operations and reports |

## Run with Docker (recommended)
```bash
cp .env.example .env                 # then set real local values (never commit .env)
docker compose up -d --build         # db :5433, redis :6380, API :8010, scheduler
docker compose exec backend python manage.py seed_demo      # optional synthetic demo data
curl http://localhost:8010/api/v1/health
```
- API docs (development): http://localhost:8010/api/v1/docs (OpenAPI: `/api/v1/schema`)
- Django admin (read-only views): http://localhost:8010/admin/ after
  `docker compose exec backend python manage.py createsuperuser`
- Change the API port with `BACKEND_PORT`; stop with `docker compose down` (add `-v` only to wipe data).
- Services: **db** (PostgreSQL 16), **redis** (cache + shared rate limits), **backend** (gunicorn, non-root,
  migrates on start when `RUN_MIGRATIONS=true`), **scheduler** (every minute: expire reservations, unpaid
  orders and overdue demand requests).

## Run locally without Docker for the API
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements-dev.txt
docker compose up -d db redis        # redis is optional (set REDIS_URL to use it)
cd backend && python manage.py migrate && python manage.py runserver 8010
python -m pytest                     # ~310 tests, needs PostgreSQL on :5433
```

## API overview (`/api/v1`, JSON, pagination via `page` / `page_size`, max 100)
Success `{"data": ...}` · lists add `{"pagination": {page, page_size, total_items, total_pages}}` ·
errors `{"error": {"code", "message", "details": [{"field", "message"}]}}`.

| Area | Endpoints |
|---|---|
| Auth | `POST auth/register, login, refresh, logout` · `GET auth/me` |
| Profiles | `GET/PATCH profiles/me` · `GET farmers/{id}` · `GET farmers/{id}/reviews` |
| Catalogue | `GET categories` · `GET/POST listings` · `GET/PATCH listings/{id}` · `POST listings/{id}/deactivate, activate` · `POST listings/{id}/media` · `DELETE listings/{id}/media/{mid}` · `GET media/{id}` |
| Inventory | `GET inventory/listings/{id}` · `POST .../adjustments` · `GET .../movements, availability` |
| Orders | `POST/GET orders` (`Idempotency-Key`) · `GET orders/{id}, history` · `POST orders/{id}/cancel` |
| Payments (simulated) | `POST orders/{id}/payment-simulation` · `POST payments/simulations/{id}/complete` · `GET payments/simulations/{id}` |
| Delivery | `GET/POST orders/{id}/delivery` · `PATCH deliveries/{id}` |
| Notifications | `GET notifications` · `POST notifications/{id}/read` |
| Reviews / issues | `POST orders/{id}/reviews` · `GET/POST orders/{id}/issues` |
| Quality | `GET/POST listings/{id}/inspections` · `PATCH inspections/{id}` |
| Demand | `POST/GET demand-requests` · `GET demand-requests/market, {id}, {id}/matches` · `POST .../close` |
| Admin | `GET admin/users, listings, issues, reviews, audit-logs, reports/summary` · `PATCH admin/users/{id}/status, admin/listings/{id}/moderation, admin/issues/{id}, admin/reviews/{id}/moderation` |

Listing search filters: `q, category_id, county, locality, min_price, max_price, min_quantity, quantity_unit,
declared_grade, ordering (newest|price_asc|price_desc|harvest_newest), mine`.

## Platform features
- **Redis**: shared cache for anonymous public reads (categories, listing search/detail, farmer pages and
  reviews) with version-based invalidation after commit; authenticated requests bypass it. Shared rate-limit
  counters across gunicorn workers. Every cache/throttle path **fails open** if Redis is down.
- **Rate limiting**: 120/min anonymous, 600/min authenticated, 20/min on auth endpoints.
- **CORS** for the frontend origin(s) in `CORS_ALLOWED_ORIGINS` (credentials allowed; `Idempotency-Key` allowed;
  `Idempotent-Replay`, `X-Request-ID`, `X-Cache` exposed).
- **Security**: JWT access token in the response body + rotating httpOnly refresh cookie (blacklisted on logout),
  server-side authorization and ownership checks, strong password rules, image re-encoding (EXIF stripped),
  security headers, `no-store` on API responses, optional HTTPS mode (`SECURE_SSL=true`), weak-secret check.
- **Observability**: `X-Request-ID` on every response and log line; health endpoint reports database and cache.
- **Money/stock integrity**: decimal money and quantities, row-locked stock reservations, idempotent order creation,
  all-or-nothing order + reservation transaction, payment success decided only by backend logic.

## Hosted-environment checklist
`DJANGO_DEBUG=false`, strong `DJANGO_SECRET_KEY`, `SECURE_SSL=true`, `PAYMENT_SIMULATION_ENABLED=false`,
`API_DOCS_ENABLED=false` (optional), `CORS_ALLOWED_ORIGINS` / `CSRF_TRUSTED_ORIGINS` set to the real frontend,
managed PostgreSQL and Redis, persistent volume or object storage for `MEDIA_ROOT`. Never run `seed_demo` there.
