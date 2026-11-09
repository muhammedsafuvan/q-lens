# QueueLens

**Background job observability and reliability intelligence for Python applications.**

QueueLens is a developer-focused observability platform that helps engineering teams understand background job execution, investigate failures, monitor retries, and identify reliability issues before they affect customers.

The initial integration targets **Celery applications**.

> Know what's happening inside your background jobs, understand why they're failing, and recover safely before customers notice.

<p align="center">
  <a href="https://pypi.org/project/queuelens/">
    <img src="https://img.shields.io/pypi/v/queuelens?label=PyPI" alt="PyPI version">
  </a>
  <a href="https://pypi.org/project/queuelens/">
    <img src="https://img.shields.io/pypi/pyversions/queuelens" alt="Python versions">
  </a>
  <img src="https://img.shields.io/badge/Python-3.12+-blue" alt="Python 3.12+">
  <img src="https://img.shields.io/badge/Status-Active%20Development-orange" alt="Project status">
</p>

---

## Project Status

QueueLens is under active development. The backend foundation, event ingestion pipeline, and initial Celery SDK integration are implemented and deployed.

### Implemented

- FastAPI backend
- PostgreSQL database integration
- SQLAlchemy models and database session management
- DBmate-based database migrations
- Workspace and API-key data models
- Workspace-scoped event ingestion
- Batch event ingestion API
- Duplicate-safe event persistence
- Job listing and task detail APIs
- Failure diagnostics and traceback persistence
- Workspace API-key authentication
- Python Celery instrumentation SDK
- SDK published on PyPI
- In-memory event buffering and asynchronous batch delivery
- Retry handling and graceful shutdown flushing in the SDK
- Docker-based local backend development
- Production deployment on Google Cloud Run
- Neon PostgreSQL production database
- Google Secret Manager integration
- GitHub Actions CI and production migration workflow

### Currently Planned

- Google Sign-In and dashboard authentication
- User and workspace membership management
- API-key management through the dashboard
- React and TypeScript developer dashboard
- Queue health and reliability analytics
- Worker health monitoring
- Scheduled job monitoring
- Alerting integrations
- Safe manual job replay

---

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
- How many times has a task been retried?
- Which workers are processing jobs?
- Did an expected scheduled job actually execute?
- Can a failed job be safely retried?

QueueLens aims to bring these answers into one developer-focused reliability platform.

---

## Architecture

QueueLens separates customer infrastructure from the observability platform.

Customers continue to own and operate their Python applications, Celery workers, and message brokers. The QueueLens SDK observes task lifecycle events and sends telemetry to the QueueLens backend.

```mermaid
flowchart TD
    subgraph Customer["Customer Infrastructure"]
        A["Python Application"] --> B["Celery Worker"]
        B <--> C["Redis / Message Broker"]
        B --> D["QueueLens Python SDK"]
        D --> E["In-Memory Event Buffer"]
    end

    subgraph Platform["QueueLens Platform"]
        E -->|"HTTPS Batch Ingestion"| F["FastAPI Ingestion API"]
        F --> G["PostgreSQL"]
        G --> H["Jobs API"]
        H --> I["Developer Dashboard (Planned)"]
    end
```

### Customer-Side Integration

1. Install the QueueLens Python SDK.
2. Configure the QueueLens endpoint and workspace API key.
3. Instrument the existing Celery application.
4. Continue running Celery workers as usual.
5. The SDK captures lifecycle events and delivers them asynchronously.

QueueLens does not execute customer tasks or manage the customer's broker.

The SDK uses a bounded in-memory event buffer. Pending events can be lost if a customer worker process terminates unexpectedly before delivery. Telemetry failures are isolated from normal task execution.

### QueueLens Backend

The backend receives event batches over HTTPS, validates and authenticates requests, and persists events in PostgreSQL.

The backend does not run customer Celery workers and does not require an internal Redis broker.

---

## Python SDK

QueueLens provides a Python SDK for instrumenting existing Celery applications.

- **PyPI:** https://pypi.org/project/queuelens/
- **SDK source code:** https://github.com/muhammedsafuvan/qlens-sdk

### Installation

Install the SDK with Celery support:

```bash
pip install "queuelens[celery]"
```

### Quick Start

Create or use an existing Celery application:

```python
from celery import Celery
from queuelens import QueueLens

app = Celery(
    "orders",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/1",
)

queuelens = QueueLens()
queuelens.instrument(app)
```

Configure the QueueLens workspace API key and ingestion endpoint:

```env
QUEUELENS_API_KEY=your_workspace_api_key
QUEUELENS_ENDPOINT=https://YOUR_QUEUELENS_API/api/v1/events/batch
```

Run your Celery worker as usual:

```bash
celery -A app worker --loglevel=info
```

No changes to existing task definitions are required.

The SDK observes task lifecycle events and asynchronously delivers them to your QueueLens workspace.

**Note:** Configure `QUEUELENS_ENDPOINT` with your actual QueueLens deployment URL. The currently deployed backend ingestion route is `/api/v1/events/batch`.

### Captured Lifecycle Events

| Event | Description |
|---|---|
| `received` | Task received by a worker |
| `started` | Task execution started |
| `succeeded` | Task completed successfully |
| `failed` | Task execution failed |
| `retried` | Task scheduled for retry |

Events can include:

- Task ID
- Task name
- Event type
- Event timestamp
- Worker name
- Queue name
- Attempt number
- Exception type
- Exception message
- Formatted traceback

Task arguments and return values are not captured by default.

### Event Delivery

The SDK provides:

- Bounded in-memory event buffering
- Configurable batch sizes
- Configurable flush intervals
- Asynchronous HTTP delivery
- HTTP timeouts
- Retry handling with exponential backoff and jitter
- Event acknowledgement after successful ingestion
- Graceful shutdown flushing

The event buffer is in-memory, not durable storage. A forced process termination or machine failure can result in the loss of events that have not yet been delivered.

---

## Backend Technology Stack

| Component | Technology |
|---|---|
| Backend API | Python, FastAPI |
| Database | PostgreSQL |
| ORM | SQLAlchemy |
| Database migrations | DBmate |
| Dependency management | uv |
| Customer task queue | Celery |
| Customer message broker | Redis |
| SDK | Python |
| Containers | Docker, Docker Compose |
| Testing | pytest |
| Code quality | Ruff |
| CI/CD | GitHub Actions |
| Container registry | Google Artifact Registry |
| Backend deployment | Google Cloud Run |
| Production database | Neon PostgreSQL |
| Secrets management | Google Secret Manager |
| SDK distribution | PyPI |
| Dashboard | React, TypeScript (planned) |

---

## Backend Project Structure

```text
QLens/
├── app/
│   ├── api/
│   │   ├── health.py
│   │   └── v1/
│   │       └── public/
│   ├── core/
│   ├── db/
│   ├── models/
│   ├── schemas/
│   ├── services/
│   └── main.py
├── db/
│   └── migrations/
├── scripts/
│   ├── bootstrap_dev_workspace.py
│   └── bootstrap_prod_workspace.py
├── tests/
├── .github/
│   └── workflows/
│       └── ci.yml
├── .env.example
├── .gitignore
├── Dockerfile.api
├── docker-compose.yml
├── pyproject.toml
├── uv.lock
└── README.md
```

The customer Celery demo is maintained separately from the backend repository.

---

## Getting Started: Backend Development

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- Docker Desktop or Docker Engine
- Docker Compose
- [DBmate](https://github.com/amacneil/dbmate)

### 1. Clone the Repository

```bash
git clone <YOUR_REPOSITORY_URL>
cd QLens
```

### 2. Install Dependencies

```bash
uv sync
```

### 3. Install DBmate

On macOS:

```bash
brew install dbmate
```

Verify the installation:

```bash
dbmate --version
```

### 4. Configure Environment Variables

Create your local environment file:

```bash
cp .env.example .env
```

The backend requires the following configuration:

```env
APP_NAME=QueueLens
APP_ENV=development

DATABASE_URL=postgresql+psycopg://qlens:qlens_dev@127.0.0.1:5433/qlens

DBMATE_DATABASE_URL=postgres://qlens:qlens_dev@127.0.0.1:5433/qlens?sslmode=disable

QUEUELENS_API_KEY=your_local_workspace_api_key
```

Use `.env.example` as the source of truth for the actual configuration required by the current codebase.

Never commit your actual `.env` file or production credentials.

### 5. Start Backend Infrastructure

The backend Docker Compose environment runs PostgreSQL and the FastAPI API.

```bash
docker compose up -d
```

Check service status:

```bash
docker compose ps
```

View logs:

```bash
docker compose logs -f postgres api
```

The local PostgreSQL host port is `5433`, and the API host port is `8001`.

Customer Redis and Celery workers are separate from the QueueLens backend infrastructure.

### 6. Run Database Migrations

Load environment variables into your shell:

```bash
set -a
source .env
set +a
```

Apply migrations:

```bash
dbmate \
  --url "$DBMATE_DATABASE_URL" \
  --migrations-dir db/migrations \
  up
```

Check migration status:

```bash
dbmate \
  --url "$DBMATE_DATABASE_URL" \
  --migrations-dir db/migrations \
  status
```

### 7. Run the API

```bash
uv run uvicorn app.main:app --reload --port 8001
```

API documentation:

- Swagger UI: http://localhost:8001/docs
- ReDoc: http://localhost:8001/redoc
- OpenAPI schema: http://localhost:8001/openapi.json

### 8. Verify the Backend

Liveness check:

```bash
curl http://localhost:8001/health
```

Database readiness check:

```bash
curl http://localhost:8001/ready
```

---

## API Overview

The current public API includes:

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | API liveness check |
| `GET` | `/ready` | Database readiness check |
| `POST` | `/api/v1/events/batch` | SDK event ingestion |
| `GET` | `/api/v1/jobs` | List workspace jobs |
| `GET` | `/api/v1/jobs/{task_id}` | Retrieve job details |

### Authentication

The current public API uses workspace API keys with Bearer authentication.

```http
Authorization: Bearer <QUEUELENS_API_KEY>
```

The SDK uses a workspace API key to authenticate event ingestion. The current public jobs endpoints also use workspace API-key authentication.

Google Sign-In and user-based dashboard authentication are planned and are not yet part of the deployed API.

---

## Database Migrations

QueueLens uses DBmate for PostgreSQL schema management and SQLAlchemy for application-level database access.

DBmate migrations are the source of truth for schema changes. SQLAlchemy models map application objects to the existing database schema.

### Create a Migration

```bash
dbmate \
  --url "$DBMATE_DATABASE_URL" \
  --migrations-dir db/migrations \
  new migration_name
```

### Apply Migrations

```bash
dbmate \
  --url "$DBMATE_DATABASE_URL" \
  --migrations-dir db/migrations \
  up
```

### Check Migration Status

```bash
dbmate \
  --url "$DBMATE_DATABASE_URL" \
  --migrations-dir db/migrations \
  status
```

### Roll Back the Latest Migration

```bash
dbmate \
  --url "$DBMATE_DATABASE_URL" \
  --migrations-dir db/migrations \
  down
```

Always review generated SQL before applying migrations.

Avoid editing migrations that have already been applied to shared environments. Create a new migration instead.

---

## Testing and Code Quality

Run the test suite:

```bash
uv run pytest -v
```

Run Ruff lint checks:

```bash
uv run ruff check .
```

Check formatting:

```bash
uv run ruff format --check .
```

Format the code:

```bash
uv run ruff format .
```

Inspect installed dependencies:

```bash
uv tree
```

### Continuous Integration

GitHub Actions runs the backend quality pipeline for pull requests and pushes to `main`.

The workflow includes:

- PostgreSQL service for integration tests
- Python and uv setup
- Dependency installation
- DBmate migration execution
- Development workspace bootstrap
- Ruff lint checks
- Ruff formatting checks
- pytest test suite

A separate production migration job runs after successful quality checks on pushes to `main`, using the configured GitHub production environment and Neon database secret.

---

## Production Deployment

The current production backend is deployed on Google Cloud Run.

| Component | Service |
|---|---|
| Backend API | Google Cloud Run |
| Container registry | Google Artifact Registry |
| Database | Neon PostgreSQL |
| Database region | AWS Singapore |
| Application region | Google Cloud `asia-south1` |
| Secrets management | Google Secret Manager |
| CI/CD | GitHub Actions |

The API is publicly reachable for SDK ingestion. Application-level authentication protects the relevant API endpoints.

Production database credentials and workspace API keys are stored as secrets and must never be committed to the repository.

---

## Engineering Principles

1. **Non-intrusive instrumentation:** Monitoring must not interfere with application workloads.
2. **Reliability first:** Telemetry failures must not cause business tasks to fail.
3. **Privacy by default:** Never capture task arguments or return values by default.
4. **Safe recovery:** Retrying jobs must account for idempotency and duplicate execution risks.
5. **Scalable architecture:** Start with a modular backend that can evolve as usage grows.
6. **Actionable observability:** Prioritize customer impact and operational decisions over vanity metrics.
7. **Clear infrastructure boundaries:** Customer execution infrastructure remains separate from QueueLens observability infrastructure.

---

## Roadmap and Milestones

### Milestone 1 — Backend Foundation

- [x] Initial backend project setup
- [x] FastAPI application foundation
- [x] PostgreSQL integration
- [x] SQLAlchemy models and database session management
- [x] DBmate migration setup
- [x] Workspace schema
- [x] Workspace API-key schema
- [x] Workspace isolation for job events

### Milestone 2 — Celery SDK and Event Ingestion

- [x] Python SDK package
- [x] PyPI distribution
- [x] Celery instrumentation
- [x] Task lifecycle event capture
- [x] In-memory event buffering
- [x] Asynchronous batch delivery
- [x] Retry and graceful shutdown handling
- [x] Backend event ingestion API
- [x] Event validation and persistence
- [x] Duplicate-safe event ingestion
- [x] End-to-end customer Celery demo

### Milestone 3 — Production Infrastructure and CI/CD

- [x] Docker-based local backend environment
- [x] Production PostgreSQL on Neon
- [x] Google Artifact Registry
- [x] Google Cloud Run deployment
- [x] Secret Manager integration
- [x] Production health and readiness checks
- [x] GitHub Actions quality workflow
- [x] Automated production database migrations

### Milestone 4 — Authentication and Workspace Management

- [ ] Google Sign-In
- [ ] Provider-independent authentication architecture
- [ ] User and identity management
- [ ] Workspace membership and roles
- [ ] User-based dashboard sessions
- [ ] Refresh-token rotation and revocation
- [ ] Dashboard API-key management
- [ ] Workspace access controls

### Milestone 5 — Observability and Reliability Intelligence

- [x] Job listing API
- [x] Job detail API
- [x] Failure diagnostic persistence
- [ ] Job and attempt timeline
- [ ] Queue latency analytics
- [ ] Throughput and backlog analytics
- [ ] Retry and failure intelligence
- [ ] Worker health monitoring
- [ ] Scheduled job monitoring
- [ ] Alerting integrations

### Milestone 6 — Developer Experience and Product

- [ ] React and TypeScript dashboard
- [ ] Workspace onboarding
- [ ] API-key management UI
- [ ] Job search and filtering
- [ ] Failure investigation experience
- [ ] Safe manual job replay
- [ ] Public beta

---

## Contributing

QueueLens is actively evolving. Contributions, ideas, and feedback are welcome.

Please open an issue to discuss significant changes before submitting a pull request.

## License

License to be determined.