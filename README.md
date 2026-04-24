# Sistema de Gestión de Créditos de Consumo

REST API for Colombian consumer credit management. Built with Flask, SQLAlchemy, and PostgreSQL. Implements amortization schedules, payment processing following Colombian legal payment order, double-entry accounting (PUC), and usury rate validation.

## Tech Stack

- **Python 3.12** · **Flask 3.0** · **SQLAlchemy** · **Alembic** · **PostgreSQL 16**
- **uv** for dependency management · **ruff** for linting/formatting · **pre-commit** hooks
- **Marshmallow** for request validation · **python-json-logger** for CloudWatch-compatible structured logs
- **pytest** for unit and integration tests · **Docker Compose** for local development

## Quick Start

```bash
# 1. Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Copy environment config
cp .env.example .env

# 3. Start PostgreSQL
docker-compose up -d db

# 4. Install dependencies
uv sync

# 5. Set up pre-commit hooks
uv run pre-commit install

# 6. Apply migrations
uv run flask db upgrade

# 7. Run the development server
uv run flask run
```

The API will be available at `http://localhost:5000`.

## Running Tests

```bash
docker-compose up -d db_test
uv run pytest
uv run pytest tests/unit/ -v   # unit tests only, no DB needed
```

## API Endpoints

Full documentation in [docs/api.md](docs/api.md).

### POST /api/v1/clients/
Create a client (required before creating a loan).

```json
{
  "document_type": "CC",
  "document_number": "1020304050",
  "full_name": "Camila Torres",
  "credit_score": 720,
  "monthly_income": "4500000"
}
```

### EP-1: Simulate Loan — `POST /api/v1/loans/simulate`

Generates an amortization schedule without persisting anything. Accepts both NMV and EA rates.

```json
{
  "amount": "20000000",
  "interest_rate": "0.24",
  "rate_type": "NOMINAL_MV",
  "term_months": 12,
  "payment_modality": "CUOTA_FIJA"
}
```

### EP-2: Create Loan — `POST /api/v1/loans`

Creates a loan after validating client eligibility (score > 600, no active mora, debt capacity) and confirming rate does not exceed usury ceiling. Generates amortization schedule and disbursement accounting entry.

```json
{
  "client_id": "uuid",
  "amount": "20000000",
  "interest_rate": "0.24",
  "rate_type": "NOMINAL_MV",
  "term_months": 12,
  "payment_modality": "CUOTA_FIJA"
}
```

### EP-3: Register Payment — `POST /api/v1/loans/{loan_id}/payments`

Registers a payment applying the Colombian legal order: (1) judicial costs, (2) insurance, (3) default interest, (4) accrued interest, (5) principal. Returns breakdown by concept. Duplicate payments by `payment_reference` return HTTP 409.

```json
{
  "amount": "1891195.03",
  "payment_reference": "PSE-TXN-20260401-001",
  "payment_date": "2026-04-01",
  "payment_method": "PSE"
}
```

### EP-4: Loan Statement — `GET /api/v1/loans/{loan_id}/statement`

Returns full credit statement: summary, paid/pending installments, current balances, days in default, and default interest calculated to today.

## Project Structure

```
app/
├── __init__.py              # Application Factory
├── config.py                # Dev / Test / Prod configs
├── extensions.py            # SQLAlchemy, Migrate instances
├── errors.py                # Centralized exception handlers
├── logging_config.py        # CloudWatch-compatible JSON logging
├── models/                  # SQLAlchemy models
├── api/v1/loans.py          # Blueprint with all 4 endpoints
├── services/
│   ├── financial.py         # Pure financial math (Decimal, no side effects)
│   ├── loan_service.py      # Business logic + SELECT FOR UPDATE
│   └── accounting_service.py# PUC double-entry generation
└── schemas/loan_schemas.py  # Marshmallow validation schemas

docs/
├── schema.sql               # PostgreSQL DDL with constraints and indexes
├── er_diagram.md            # Mermaid ER diagram
├── design_decisions.md      # Part 1: design rationale + conceptual Q&A
├── aws_architecture.md      # Part 3: AWS diagram + CloudFormation + Q&A
└── financial_answers.md     # Part 4: theory + full amortization table

scripts/
└── fix_production.py        # Part 5: diagnostic queries + remediation
```

## Key Design Decisions

- **`NUMERIC(18,2)` everywhere** — no FLOAT for money; all Python math uses `decimal.Decimal`
- **`UNIQUE(payment_reference)`** — DB-level idempotency for PSE callback replay
- **`SELECT FOR UPDATE`** — row-level lock on loan record during payment processing prevents concurrent double application
- **`CHECK (debit_amount = credit_amount)`** — partida doble enforced at DB level
- **Rate normalization** — all rates stored as EA; NMV converted at input time

## Financial Calculations

```python
# Nominal MV → monthly rate
i = nominal_mv / 12

# Effective Annual → monthly rate
i = (1 + ea) ** (1/12) - 1

# Fixed installment (sistema francés)
C = P * [i * (1+i)^n] / [(1+i)^n - 1]

# Default interest (mora)
I_mora = saldo * (i_corriente * 1.5 / 30) * días_atraso  # capped at usury rate
```

## Production Remediation (Part 5)

```bash
# Diagnose without changing anything
python scripts/fix_production.py --diagnose-only

# Preview all fixes
python scripts/fix_production.py --dry-run --from-date 2026-01-01

# Apply fixes
python scripts/fix_production.py --from-date 2026-01-01 --to-date 2026-04-22
```

Fixes: duplicate payment deduplication, unbalanced accounting entry regeneration, missing interest accrual backfill, and overdue loan status correction.
