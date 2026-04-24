-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================
-- ENUMS
-- ============================================================

CREATE TYPE document_type AS ENUM ('CC', 'CE', 'NIT', 'PASAPORTE');
CREATE TYPE risk_classification AS ENUM ('A', 'B', 'C', 'D', 'E');
CREATE TYPE rate_type AS ENUM ('NOMINAL_MV', 'EFECTIVA_ANUAL');
CREATE TYPE payment_modality AS ENUM ('CUOTA_FIJA', 'ABONO_CONSTANTE');
CREATE TYPE loan_status AS ENUM (
    'RADICADO', 'APROBADO', 'DESEMBOLSADO',
    'AL_DIA', 'EN_MORA', 'REESTRUCTURADO', 'CASTIGADO', 'PAGADO'
);
CREATE TYPE payment_method AS ENUM (
    'PSE', 'CONSIGNACION', 'DEBITO_AUTOMATICO', 'CORRESPONSAL'
);
CREATE TYPE puc_entry_type AS ENUM (
    'DESEMBOLSO', 'CAUSACION_INTERESES', 'RECAUDO', 'MORA'
);

-- ============================================================
-- CLIENTS
-- ============================================================

CREATE TABLE clients (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_type   document_type NOT NULL,
    document_number VARCHAR(20) NOT NULL,
    full_name       VARCHAR(200) NOT NULL,
    email           VARCHAR(150),
    phone           VARCHAR(20),
    city            VARCHAR(100),
    credit_score    INTEGER CHECK (credit_score BETWEEN 0 AND 1000),
    risk_class      risk_classification NOT NULL DEFAULT 'A',
    monthly_income  NUMERIC(18, 2),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_client_document UNIQUE (document_type, document_number)
);

COMMENT ON TABLE clients IS 'Loan clients. Uniquely identified by document type + number.';
COMMENT ON COLUMN clients.risk_class IS 'A=Normal, B=Acceptable, C=Appreciable, D=Significant, E=Unrecoverable';

-- ============================================================
-- LOANS
-- ============================================================

CREATE TABLE loans (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id           UUID NOT NULL REFERENCES clients(id),
    requested_amount    NUMERIC(18, 2) NOT NULL,
    approved_amount     NUMERIC(18, 2),
    interest_rate       NUMERIC(8, 6) NOT NULL,
    rate_type_input     rate_type NOT NULL,
    term_months         INTEGER NOT NULL,
    payment_modality    payment_modality NOT NULL,
    status              loan_status NOT NULL DEFAULT 'RADICADO',
    disbursement_date   DATE,
    declared_income     NUMERIC(18, 2),
    capital_balance     NUMERIC(18, 2),
    accrued_interest    NUMERIC(18, 2) NOT NULL DEFAULT 0,
    days_in_default     INTEGER NOT NULL DEFAULT 0,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_positive_term CHECK (term_months > 0)
);

CREATE INDEX idx_loans_client ON loans (client_id);
CREATE INDEX idx_loans_status ON loans (status);

COMMENT ON TABLE loans IS 'Consumer credit loans. Rate is always stored as EA for consistency.';
COMMENT ON COLUMN loans.interest_rate IS 'Effective annual rate (EA) as decimal. Converted from NMV at input if needed.';
COMMENT ON COLUMN loans.declared_income IS 'Income declared by the client at application time. Used for debt capacity validation.';

-- ============================================================
-- AMORTIZATION SCHEDULE
-- ============================================================

CREATE TABLE amortization_schedule (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    loan_id         UUID NOT NULL REFERENCES loans(id) ON DELETE CASCADE,
    installment_num INTEGER NOT NULL,
    due_date        DATE NOT NULL,
    principal       NUMERIC(18, 2) NOT NULL,
    interest        NUMERIC(18, 2) NOT NULL,
    life_insurance  NUMERIC(18, 2) NOT NULL DEFAULT 0,
    other_charges   NUMERIC(18, 2) NOT NULL DEFAULT 0,
    total_due       NUMERIC(18, 2) NOT NULL,
    capital_balance NUMERIC(18, 2) NOT NULL,
    is_paid         BOOLEAN NOT NULL DEFAULT FALSE,
    paid_at         DATE,

    CONSTRAINT uq_loan_installment UNIQUE (loan_id, installment_num)
);

CREATE INDEX idx_amort_loan ON amortization_schedule (loan_id);
CREATE INDEX idx_amort_unpaid_due ON amortization_schedule (due_date) WHERE NOT is_paid;

COMMENT ON TABLE amortization_schedule IS 'Projected payment schedule. Generated at disbursement time.';

-- ============================================================
-- PAYMENTS
-- ============================================================

CREATE TABLE payments (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    loan_id             UUID NOT NULL REFERENCES loans(id),
    -- Unique reference for idempotency against duplicate PSE gateway callbacks
    payment_reference   VARCHAR(100) NOT NULL,
    payment_date        DATE NOT NULL,
    total_amount        NUMERIC(18, 2) NOT NULL,
    -- Breakdown per Colombian legal payment order (Art. 886 CCo + SFC doctrine)
    applied_judicial    NUMERIC(18, 2) NOT NULL DEFAULT 0,
    applied_insurance   NUMERIC(18, 2) NOT NULL DEFAULT 0,
    applied_default_int NUMERIC(18, 2) NOT NULL DEFAULT 0,
    applied_interest    NUMERIC(18, 2) NOT NULL DEFAULT 0,
    applied_principal   NUMERIC(18, 2) NOT NULL DEFAULT 0,
    payment_method      payment_method NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_payment_reference UNIQUE (payment_reference)
);

CREATE INDEX idx_payments_loan ON payments (loan_id);

COMMENT ON TABLE payments IS 'Registered payments with breakdown by concept.';
COMMENT ON COLUMN payments.payment_reference IS 'Gateway reference (PSE, bank). UNIQUE constraint ensures idempotency against duplicate callbacks.';

-- ============================================================
-- ACCOUNTING ENTRIES (DOUBLE-ENTRY / PUC)
-- ============================================================

CREATE TABLE accounting_entries (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    loan_id         UUID NOT NULL REFERENCES loans(id),
    payment_id      UUID REFERENCES payments(id),
    entry_type      puc_entry_type NOT NULL,
    entry_date      DATE NOT NULL,
    -- Colombian Chart of Accounts (PUC) codes
    puc_debit       VARCHAR(10) NOT NULL,
    puc_credit      VARCHAR(10) NOT NULL,
    debit_amount    NUMERIC(18, 2) NOT NULL,
    credit_amount   NUMERIC(18, 2) NOT NULL,
    description     TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_debit_positive  CHECK (debit_amount > 0),
    CONSTRAINT chk_credit_positive CHECK (credit_amount > 0),
    -- Double-entry principle: debit must always equal credit per entry
    CONSTRAINT chk_partida_doble   CHECK (debit_amount = credit_amount)
);

CREATE INDEX idx_accounting_loan ON accounting_entries (loan_id);
CREATE INDEX idx_accounting_date ON accounting_entries (entry_date);

COMMENT ON TABLE accounting_entries IS
    'Double-entry accounting records. Each row is one balanced debit/credit pair.
     PUC accounts used:
       141005 – Cartera consumo capital (Asset)
       270505 – Accrued interest receivable (Asset)
       411005 – Interest income from consumer loans (Income)
       410520 – Default interest income (Income)
       111005 – Cash / Banks (Asset)';
