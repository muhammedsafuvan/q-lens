# QueueLens

**Background job observability and reliability intelligence for Python applications.**

QueueLens helps engineering teams understand what's happening inside their background job infrastructure, identify failures, monitor queue health, and detect reliability issues before they impact customers.

We're starting with Celery and Redis, with a focus on making background job systems more observable, predictable, and reliable.

> Know what's happening inside your background jobs, understand why they're failing, and recover safely before customers notice.

## The Problem

Background jobs power critical application workflows such as:

- Payment processing
- Email and notification delivery
- Subscription renewals
- Report generation
- Data synchronization
- Scheduled reconciliation

But as applications scale, teams often struggle to answer:

- Why are jobs failing?
- Which queues are accumulating backlogs?
- Are customers experiencing delayed processing?
- Did an expected scheduled job actually execute?
- Are workers healthy?
- Can a failed job be safely retried?

QueueLens aims to bring these answers into one developer-focused reliability platform.

## Current Scope

The initial implementation focuses on:

- Celery task lifecycle instrumentation
- Redis-backed task queues
- Job execution and failure tracking
- Queue latency and throughput visibility
- Retry and failure analytics
- Worker health monitoring
- Tenant-aware reliability monitoring
- Scheduled job execution monitoring

*This is an evolving project. Features will be marked as implemented as development progresses.*

## Architecture

The initial architecture is designed around a Python-first backend.

```mermaid
flowchart TD
    A["Python Application"] --> B["Celery Workers"]
    B --> C["Redis Broker"]
    B --> D["QueueLens SDK"]
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
├── examples/
│   └── celery-demo/
├── migrations/
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

### 1. Clone the repository

```bash
git clone <YOUR_REPOSITORY_URL>
cd queuelens
```

### 2. Install dependencies

```bash
uv sync
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

Update `.env` with your local development configuration:

```env
APP_NAME=QueueLens
APP_ENV=development

DATABASE_URL=postgresql+psycopg://qlens:qlens_dev@localhost:5432/qlens

REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
```

### 4. Start infrastructure

```bash
docker compose up -d
```

Check service status:

```bash
docker compose ps
```

### 5. Run the API

```bash
uv run uvicorn app.main:app --reload
```

API documentation:

- http://localhost:8000/docs
- http://localhost:8000/redoc

Health endpoint:

- http://localhost:8000/health

## Development Commands

```bash
# Install dependencies
uv sync

# Start infrastructure
docker compose up -d

# Stop infrastructure
docker compose stop

# View logs
docker compose logs -f

# Run tests
uv run pytest

# Lint
uv run ruff check .

# Format
uv run ruff format .
```

## Engineering Principles

QueueLens is being designed around the following principles:

1. **Non-intrusive instrumentation:** Monitoring must not interfere with application workloads.
2. **Reliability first:** Telemetry failures must not cause business tasks to fail.
3. **Privacy by default:** Never capture task arguments or return values by default.
4. **Safe recovery:** Retrying jobs must account for idempotency and duplicate execution risks.
5. **Scalable architecture:** Start simple, with a modular backend that can evolve as usage grows.
6. **Actionable observability:** Prioritize customer impact and operational decisions over vanity metrics.

## Roadmap

- [x] Initial backend project setup
- [x] PostgreSQL and Redis development infrastructure
- [ ] FastAPI application foundation
- [ ] Database models and migrations
- [ ] Celery integration
- [ ] QueueLens instrumentation SDK
- [ ] Job lifecycle event ingestion
- [ ] Queue monitoring and analytics
- [ ] Failure and retry intelligence
- [ ] Tenant-aware reliability monitoring
- [ ] Scheduled job monitoring
- [ ] Alerting integrations
- [ ] Developer dashboard
- [ ] Public beta

## Project Status

QueueLens is currently under active development.

The initial milestone is to establish a reliable backend foundation and build the first working Celery instrumentation workflow.

## Contributing

Contributions, ideas, and feedback are welcome.

This project is currently evolving rapidly. Please open an issue to discuss significant changes before submitting a pull request.

## License

License to be determined.