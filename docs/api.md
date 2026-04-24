# API Reference

Base URL: `http://localhost:5000`

---

## Clients

### POST /api/v1/clients/
Create a client.

```json
{
  "document_type": "CC",
  "document_number": "1020304050",
  "full_name": "Camila Torres",
  "email": "camila@email.com",
  "city": "Medellín",
  "credit_score": 720,
  "risk_class": "A",
  "monthly_income": "4500000"
}
```

Response `201`:
```json
{
  "client": {
    "id": "uuid",
    "document_type": "CC",
    "document_number": "1020304050",
    "full_name": "Camila Torres",
    "credit_score": 720,
    "risk_class": "A",
    "monthly_income": "4500000.00"
  }
}
```

Errors: `422` validation, `409` duplicate document.

### GET /api/v1/clients/{client_id}
Retrieve client by ID. `404` if not found.

---

## Loans

### POST /api/v1/loans/simulate
Simulate amortization without persisting. Accepts `NOMINAL_MV` or `EFECTIVA_ANUAL` rates.

```json
{
  "amount": "20000000",
  "interest_rate": "0.24",
  "rate_type": "NOMINAL_MV",
  "term_months": 12,
  "payment_modality": "CUOTA_FIJA"
}
```

`payment_modality`: `CUOTA_FIJA` | `ABONO_CONSTANTE`

Response `200`:
```json
{
  "simulation": {
    "interest_rate_ea": "0.268242",
    "monthly_rate": "0.020000"
  },
  "schedule": [
    {
      "installment_num": 1,
      "due_date": "2026-05-24",
      "principal": "1491195.03",
      "interest": "400000.00",
      "total_due": "1891195.03",
      "capital_balance": "18508804.97"
    }
  ],
  "totals": {
    "total_interest": "...",
    "total_principal": "20000000.00",
    "total_paid": "..."
  }
}
```

Errors: `422` if rate exceeds usury ceiling (27.62% EA).

### POST /api/v1/loans/
Create a loan. Validates: credit score > 600, no active defaults, debt capacity ≤ 30% income, rate ≤ usury.

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

Response `201`: loan object + full schedule. Disbursement accounting entry (débito 141005 / crédito 111005) created automatically.

Errors: `404` client not found, `422` eligibility or usury.

### POST /api/v1/loans/{loan_id}/payments
Register a payment. Colombian legal order applied: judicial costs → insurance → default interest → accrued interest → principal.

```json
{
  "amount": "1891195.03",
  "payment_reference": "PSE-TXN-20260501-001",
  "payment_date": "2026-05-01",
  "payment_method": "PSE"
}
```

`payment_method`: `PSE` | `CONSIGNACION` | `DEBITO_AUTOMATICO` | `CORRESPONSAL`

Response `201`:
```json
{
  "payment": {
    "payment_reference": "PSE-TXN-20260501-001",
    "total_amount": "1891195.03",
    "applied_breakdown": {
      "judicial_costs": "0.00",
      "insurance": "0.00",
      "default_interest": "0.00",
      "accrued_interest": "400000.00",
      "principal": "1491195.03"
    }
  }
}
```

Errors: `409` duplicate `payment_reference`, `404` loan not found.

### GET /api/v1/loans/{loan_id}/statement
Full credit statement.

Response `200`:
```json
{
  "loan": { "status": "AL_DIA", "approved_amount": "20000000.00", ... },
  "capital_balance": "18508804.97",
  "accrued_interest": "0.00",
  "days_in_default": 0,
  "default_interest_to_date": "0.00",
  "paid_installments": [...],
  "pending_installments": [...],
  "statement_date": "2026-05-01"
}
```

---

## Error format

All errors return:
```json
{
  "error": "ERROR_CODE",
  "message": "Human-readable description.",
  "status_code": 422
}
```

| Code | HTTP |
|---|---|
| `VALIDATION_ERROR` | 422 |
| `CLIENT_NOT_FOUND` | 404 |
| `LOAN_NOT_FOUND` | 404 |
| `CLIENT_NOT_ELIGIBLE` | 422 |
| `DUPLICATE_PAYMENT` | 409 |
| `USURY_CEILING_EXCEEDED` | 422 |
