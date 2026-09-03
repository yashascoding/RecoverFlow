# RecoverFlow — Agent Guide

## Project Overview

RecoverFlow is an autonomous AI payment-recovery system that detects failed payments, investigates root causes, and sends personalized recovery messages through Email to help merchants recover lost revenue.

**Core Flow:** Payment Failed → AI Investigates → Policy Check → Email → Customer Pays → Revenue Recovered → Audit Trail

---

## Architecture

### Tech Stack
- **Backend:** Python 3.12+ / FastAPI / SQLAlchemy (async) / PostgreSQL / Redis
- **Frontend:** React + TypeScript + Vite + Tailwind CSS
- **AI Agent:** LangGraph-based recovery agent
- **Email:** Resend API
- **Payments:** Razorpay integration

### System Components
```
┌─────────────────────────────────────────────────────────────┐
│                    RecoverFlow System                       │
├─────────────────────────────────────────────────────────────┤
│  Frontend (React)  ←→  Backend (FastAPI)  ←→  PostgreSQL   │
│                          ↕                                  │
│                    Redis Queue                              │
│                          ↕                                  │
│                    Event Worker                             │
│                          ↕                                  │
│                    AI Agent (LangGraph)                     │
│                          ↕                                  │
│                    Email Service (Resend)                   │
└─────────────────────────────────────────────────────────────┘
```

---

## Directory Structure

```
RecoverFlow/
├── backend/
│   ├── app/
│   │   ├── api/              # FastAPI route handlers
│   │   ├── agents/           # AI agent definitions
│   │   ├── core/             # Config, logging, utilities
│   │   ├── db/               # Database connection
│   │   ├── events/           # Event bus, dispatcher, queue
│   │   ├── models/           # SQLAlchemy ORM models
│   │   ├── schemas/          # Pydantic request/response schemas
│   │   ├── services/         # Business logic layer
│   │   │   ├── agents/       # Agent service, recovery agent
│   │   │   ├── audit/        # Audit logging service
│   │   │   ├── communication/
│   │   │   ├── consent/      # Customer consent management
│   │   │   ├── customers/    # Customer CRUD
│   │   │   ├── email/        # Resend email service
│   │   │   ├── financial/
│   │   │   ├── payments/     # Payment service, transitions
│   │   │   ├── policy/       # Policy engine
│   │   │   └── recovery/     # Recovery pipeline, diagnosis
│   │   └── workers/          # Background event workers
│   └── alembic/              # Database migrations
├── frontend/
│   └── src/
│       ├── api/              # API client functions
│       ├── components/       # Reusable UI components
│       ├── hooks/            # React hooks
│       ├── lib/              # Utilities
│       ├── pages/            # Page components
│       └── types/            # TypeScript type definitions
├── worker/                   # Standalone worker process
└── data/                     # Local data storage
```

---

## Key Data Models

### Payment (`payments` table)
- `id` (UUID, PK)
- `razorpay_order_id` (string, unique)
- `razorpay_payment_id` (string, nullable)
- `customer_email` (string)
- `amount` (integer, paise)
- `currency` (string, default "INR")
- `status` (string: created | authorized | captured | failed | recovery_pending | refunded | recovered)
- `failure_reason` (text, nullable)
- `metadata_` (JSONB, nullable)
- `created_at`, `updated_at` (timestamptz)

### PaymentEvent (`payment_events` table)
- `id` (UUID, PK)
- `payment_id` (UUID, FK → payments)
- `event_type` (enum: created | authorized | captured | failed | refunded | recovered)
- `payload` (JSONB)
- `created_at` (timestamptz)

### Event (`events` table) — Event sourcing
- `id` (UUID, PK)
- `event_id` (UUID, unique — idempotency key)
- `event_type` (string)
- `payload` (JSONB)
- `status` (pending | processing | processed | failed | duplicate)

---

## Payment Status Transitions

```
created → authorized → captured → refunded
   ↓          ↓
failed    failed → recovery_pending → recovered
```

---

## Event System

### Event Flow
1. Razorpay webhook arrives at `/api/webhooks/razorpay`
2. Event is dispatched to `EventBus`
3. Event persisted to `events` table (dedup check)
4. Event pushed to Redis queue
5. Event Worker picks up and processes
6. Handler executes business logic

### Event Types
- `payment.created`, `payment.authorized`, `payment.captured`, `payment.failed`, `payment.refunded`
- `email.message.sent`, `email.delivered`, `email.opened`, `email.bounced`

---

## Recovery Pipeline

The full recovery flow in `recovery_pipeline.py`:

1. **Find Payment** — Locate payment by order_id
2. **Link Customer** — Link customer if not already linked
3. **Check Recovery State** — Skip if already recovered
4. **Consent Check** — Verify customer has email consent
5. **AI Agent Diagnosis** — Run LangGraph agent for analysis
6. **Policy Evaluation** — Run deterministic policy engine
7. **Transition Payment** — Move to `recovery_pending` status
8. **Create Recovery Attempt** — Record the attempt
9. **Send Recovery Email** — Send via Resend API
10. **Audit Log** — Record all actions

---

## API Endpoints

### Payment Endpoints
- `POST /api/payments/create` — Create new payment
- `GET /api/payments/` — List payments
- `GET /api/payments/{id}` — Get payment by ID
- `GET /api/payments/stats/overview` — Get overview metrics
- `GET /api/payments/recent-activity` — Recent activity feed

### Recovery Endpoints
- `GET /api/recovery/v2/incidents` — List failed payment incidents
- `GET /api/recovery/v2/diagnose` — Diagnose failure reason
- `POST /api/recovery/v2/payments/{id}/link` — Create recovery link

### Agent Endpoints
- `GET /api/agents/runs` — List agent runs
- `GET /api/agents/runs/{id}` — Get agent run details

### Simulation Endpoints
- `POST /api/simulate/failure` — Simulate payment failure
- `POST /api/simulate/capture` — Simulate payment capture

---

## Frontend Pages

- `/overview` — Dashboard with metrics, activity, system health
- `/payments` — Payment list with filters
- `/payments/:id` — Payment detail view
- `/incidents` — Failed payment incidents
- `/incidents/:id` — Incident detail
- `/recovery` — Recovery attempts
- `/agent-runs` — AI agent run history
- `/agent-runs/:id` — Agent run detail with stages
- `/audit` — Audit log
- `/policies` — Policy configuration

---

## Configuration

### Environment Variables (.env)
```
# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=recoverflow
POSTGRES_PASSWORD=recoverflow123
POSTGRES_DB=recoverflow

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Razorpay
RAZORPAY_KEY_ID=rzp_test_...
RAZORPAY_KEY_SECRET=...
RAZORPAY_WEBHOOK_SECRET=...

# Resend
RESEND_API_KEY=re_...
RESEND_WEBHOOK_SECRET=...
RECOVERY_EMAIL_FROM=recovery@yourdomain.com
```

---

## Development Workflow

### Running Locally
```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev

# Worker
cd backend
python -m app.workers.event_worker
```

### Testing
```bash
# Backend tests
cd backend
pytest

# Frontend lint
cd frontend
npm run lint
```

---

## Adding New Features

### Backend (New API Endpoint)
1. Create schema in `backend/app/schemas/`
2. Create/update service in `backend/app/services/`
3. Add route in `backend/app/api/`
4. Register router in `backend/app/main.py`

### Frontend (New Page)
1. Create types in `frontend/src/types/index.ts`
2. Create API function in `frontend/src/api/`
3. Create page component in `frontend/src/pages/`
4. Add route in `frontend/src/App.tsx`
5. Add nav item in `frontend/src/components/layout/Sidebar.tsx`

---

## Key Patterns

- **Idempotency:** All events use `event_id` for dedup
- **Async Processing:** Webhooks return 200 immediately, process in background
- **Policy Engine:** Deterministic rules before any customer contact
- **Audit Trail:** Every action logged for compliance
- **Consent Gate:** Hard check for customer consent before emails
