# QueueLens

**Background job observability and reliability intelligence for Python applications.**

QueueLens is a developer-focused platform designed to help engineering teams understand background job execution, investigate failures, monitor queue health, and identify reliability issues before they affect customers.

The initial integration targets Celery and Redis.

> Know what's happening inside your background jobs, understand why they're failing, and recover safely before customers notice.

## Project Status

QueueLens is under active development.

The current implementation includes:

- FastAPI backend foundation
- Docker-based PostgreSQL and Redis infrastructure
- SQLAlchemy database integration
- DBmate-based PostgreSQL migrations
- Initial workspace data model
- API health endpoint

The Celery instrumentation SDK, event ingestion pipeline, reliability analytics, and dashboard are planned.

## The Problem

Background jobs power critical application workflows:

- Payment processing
- Email and notification delivery
- Subscription renewals
- Report generation
- Data synchronization
- Scheduled reconciliation

As applications scale, engineering teams often struggle to answer:

- Why are jobs failing?
- Which queues are accumulating backlogs?
- Are customers experiencing delayed processing?
- Did an expected scheduled job actually execute?
- Are workers healthy?
- Can a failed job be safely retried?

QueueLens aims to bring these answers into one developer-focused reliability platform.

## Architecture

The initial architecture is Python-first.

```mermaid
flowchart TD
    A["Python Application"] --> B["Celery Workers"]
    B --> C["Redis Broker"]
    B --> D["QueueLens SDK (planned)"]
    D --> E["QueueLens Ingestion API"]
    E --> F["PostgreSQL"]
    E --> G["Processing Pipeline"]
    G --> F
    F --> H["QueueLens Dashboard"]
```

### Technology Stack

| Component | Technology |
|---|---|
| Backend API | Python, FastAPI |
| Task Queue | Celery |
| Message Broker | Redis |
| Database | PostgreSQL |
| ORM | SQLAlchemy |
| Database Migrations | DBmate |
| Dependency Management | uv |
| Containers | Docker Compose |
| Testing | pytest |
| Code Quality | Ruff |
| Frontend | React, TypeScript (planned) |

## Project Structure

```text
queuelens/
├── app/
│   ├── api/
│   │   └── v1/
│   ├── core/
│   ├── db/
│   ├── models/
│   ├── schemas/
│   ├── services/
│   ├── workers/
│   │   └── tasks/
│   └── main.py
├── db/
│   ├── migrations/
│   └── schema.sql
├── examples/
│   └── celery-demo/
├── tests/
├── .env.example
├── .gitignore
├── docker-compose.yml
├── pyproject.toml
├── uv.lock
└── README.md
```

## Getting Started

### Prerequisites

- Python 3.12+
- uv
- Docker Desktop or Docker Engine
- Docker Compose
- DBmate
- PostgreSQL client (`psql`) — optional

### 1. Clone the repository

```bash
git clone <YOUR_REPOSITORY_URL>
cd queuelens
```

### 2. Install dependencies

```bash
uv sync
```

### 3. Install DBmate

On macOS:

```bash
brew install dbmate
```

Verify:

```bash
dbmate --version
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

The default local development configuration uses:

```env
APP_NAME=QueueLens
APP_ENV=development

DATABASE_URL=postgresql+psycopg://qlens:qlens_dev@127.0.0.1:5433/qlens

DBMATE_DATABASE_URL=postgres://qlens:qlens_dev@127.0.0.1:5433/qlens?sslmode=disable

REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
```

The PostgreSQL host port is `5433` to avoid conflicts with a locally installed PostgreSQL instance. Its container port remains `5432`.

Never commit your actual `.env` file or production credentials.

### 5. Start infrastructure

```bash
docker compose up -d
```

Check service status:

```bash
docker compose ps
```

View logs:

```bash
docker compose logs -f postgres redis
```

### 6. Run database migrations

Load environment variables into your shell:

```bash
set -a
source .env
set +a
```

Apply migrations:

```bash
dbmate --url "$DBMATE_DATABASE_URL" --migrations-dir db/migrations up
```

Check migration status:

```bash
dbmate --url "$DBMATE_DATABASE_URL" --migrations-dir db/migrations status
```

### 7. Run the API

```bash
uv run uvicorn app.main:app --reload
```

API documentation:

- http://localhost:8000/docs
- http://localhost:8000/redoc

Health endpoint:

- http://localhost:8000/api/v1/health

## Database Migrations

QueueLens uses DBmate for PostgreSQL schema management and SQLAlchemy for application-level database access.

DBmate is the source of truth for schema changes. SQLAlchemy models map application objects to the existing database schema.

### Create a migration

```bash
dbmate --url "$DBMATE_DATABASE_URL" --migrations-dir db/migrations new migration_name
```

### Apply migrations

```bash
dbmate --url "$DBMATE_DATABASE_URL" --migrations-dir db/migrations up
```

### Check migration status

```bash
dbmate --url "$DBMATE_DATABASE_URL" --migrations-dir db/migrations status
```

### Roll back the latest migration

```bash
dbmate --url "$DBMATE_DATABASE_URL" --migrations-dir db/migrations down
```

Always review generated SQL before applying migrations. Avoid editing migrations that have already been applied to shared environments; create a new migration instead.

## Development Commands

```bash
# Install dependencies
uv sync

# Start infrastructure
docker compose up -d

# Stop infrastructure
docker compose stop

# View infrastructure logs
docker compose logs -f

# Run tests
uv run pytest -v

# Lint
uv run ruff check .

# Format
uv run ruff format .

# Check installed dependencies
uv tree
```

## Engineering Principles

1. **Non-intrusive instrumentation:** Monitoring must not interfere with application workloads.
2. **Reliability first:** Telemetry failures must not cause business tasks to fail.
3. **Privacy by default:** Never capture task arguments or return values by default.
4. **Safe recovery:** Retrying jobs must account for idempotency and duplicate execution risks.
5. **Scalable architecture:** Start simple with a modular backend that can evolve as usage grows.
6. **Actionable observability:** Prioritize customer impact and operational decisions over vanity metrics.

## Roadmap

### Backend Foundation

- [x] Initial backend project setup
- [x] PostgreSQL and Redis development infrastructure
- [x] FastAPI application foundation
- [x] SQLAlchemy database integration
- [x] DBmate migration setup
- [x] Initial workspace schema

### Background Job Infrastructure

- [ ] Celery application configuration
- [ ] Redis-backed task execution
- [ ] Worker lifecycle management
- [ ] Sample Celery application

### Observability Platform

- [ ] QueueLens instrumentation SDK
- [ ] Task lifecycle event ingestion
- [ ] Job and attempt tracking
- [ ] Queue latency and throughput analytics
- [ ] Failure and retry intelligence
- [ ] Worker health monitoring
- [ ] Tenant-aware reliability monitoring
- [ ] Scheduled job monitoring
- [ ] Alerting integrations

### Product

- [ ] Developer dashboard
- [ ] Workspace and API key management
- [ ] Safe manual job replay
- [ ] Public beta

## Contributing

QueueLens is currently evolving. Contributions, ideas, and feedback are welcome.

Please open an issue to discuss significant changes before submitting a pull request.

## License

License to be determined.