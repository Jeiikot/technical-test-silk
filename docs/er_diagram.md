# ER Diagram – Sistema de Créditos de Consumo

Generated with [Mermaid](https://mermaid.js.org/). Paste into any Mermaid renderer or [mermaid.live](https://mermaid.live).

```mermaid
erDiagram
    clients {
        UUID id PK
        document_type document_type
        VARCHAR(20) document_number
        VARCHAR(200) full_name
        VARCHAR(150) email
        VARCHAR(20) phone
        VARCHAR(100) city
        INTEGER credit_score
        risk_classification risk_class
        NUMERIC(18-2) monthly_income
        TIMESTAMPTZ created_at
        TIMESTAMPTZ updated_at
    }

    loans {
        UUID id PK
        UUID client_id FK
        NUMERIC(18-2) requested_amount
        NUMERIC(18-2) approved_amount
        NUMERIC(8-6) interest_rate
        rate_type rate_type_input
        INTEGER term_months
        payment_modality payment_modality
        loan_status status
        DATE disbursement_date
        NUMERIC(18-2) declared_income
        NUMERIC(18-2) capital_balance
        NUMERIC(18-2) accrued_interest
        INTEGER days_in_default
        TIMESTAMPTZ created_at
        TIMESTAMPTZ updated_at
    }

    amortization_schedule {
        UUID id PK
        UUID loan_id FK
        INTEGER installment_num
        DATE due_date
        NUMERIC(18-2) principal
        NUMERIC(18-2) interest
        NUMERIC(18-2) life_insurance
        NUMERIC(18-2) other_charges
        NUMERIC(18-2) total_due
        NUMERIC(18-2) capital_balance
        BOOLEAN is_paid
        DATE paid_at
    }

    payments {
        UUID id PK
        UUID loan_id FK
        VARCHAR(100) payment_reference
        DATE payment_date
        NUMERIC(18-2) total_amount
        NUMERIC(18-2) applied_judicial
        NUMERIC(18-2) applied_insurance
        NUMERIC(18-2) applied_default_int
        NUMERIC(18-2) applied_interest
        NUMERIC(18-2) applied_principal
        payment_method payment_method
        TIMESTAMPTZ created_at
    }

    accounting_entries {
        UUID id PK
        UUID loan_id FK
        UUID payment_id FK
        puc_entry_type entry_type
        DATE entry_date
        VARCHAR(10) puc_debit
        VARCHAR(10) puc_credit
        NUMERIC(18-2) debit_amount
        NUMERIC(18-2) credit_amount
        TEXT description
        TIMESTAMPTZ created_at
    }

    clients ||--o{ loans : "has"
    loans ||--o{ amortization_schedule : "generates"
    loans ||--o{ payments : "receives"
    loans ||--o{ accounting_entries : "triggers"
    payments ||--o{ accounting_entries : "linked_to"
```

## Enum Types

| Type | Values |
|---|---|
| `document_type` | CC, CE, NIT, PASAPORTE |
| `risk_classification` | A (Normal), B (Aceptable), C (Apreciable), D (Significativo), E (Irrecuperable) |
| `rate_type` | NOMINAL_MV, EFECTIVA_ANUAL |
| `payment_modality` | CUOTA_FIJA, ABONO_CONSTANTE |
| `loan_status` | RADICADO, APROBADO, DESEMBOLSADO, AL_DIA, EN_MORA, REESTRUCTURADO, CASTIGADO, PAGADO |
| `payment_method` | PSE, CONSIGNACION, DEBITO_AUTOMATICO, CORRESPONSAL |
| `puc_entry_type` | DESEMBOLSO, CAUSACION_INTERESES, RECAUDO, MORA |
