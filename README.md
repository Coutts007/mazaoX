# MazaoX

A mobile-first agricultural produce marketplace prototype for Kenya, connecting farmers who publish produce listings with buyers who discover produce, place orders and follow fulfilment.

> Academic prototype. Payments are simulated; no real money or payment credentials are handled.

## Architecture

Service-Oriented Architecture: a React frontend, an API gateway and independently deployable FastAPI services, each owning its own PostgreSQL database, communicating over REST and RabbitMQ events.

## Repository layout (planned)

```
app/
├── frontend/          React + TypeScript web client
├── gateway/           API gateway
├── services/          One FastAPI service per domain
├── shared/            Event contracts only (no business logic)
├── infrastructure/    Docker Compose and environment setup
└── README.md
```

## Getting started

Setup instructions will be added as the foundation is built.
