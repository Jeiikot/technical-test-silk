import json
from decimal import Decimal


SIMULATE_PAYLOAD = {
    "amount": "20000000",
    "interest_rate": "0.24",
    "rate_type": "NOMINAL_MV",
    "term_months": 12,
    "payment_modality": "CUOTA_FIJA",
}


class TestSimulateLoan:
    def test_simulate_returns_12_rows(self, client):
        resp = client.post(
            "/api/v1/loans/simulate",
            data=json.dumps(SIMULATE_PAYLOAD),
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["schedule"]) == 12

    def test_simulate_last_balance_is_zero(self, client):
        resp = client.post(
            "/api/v1/loans/simulate",
            data=json.dumps(SIMULATE_PAYLOAD),
            content_type="application/json",
        )
        schedule = resp.get_json()["schedule"]
        assert Decimal(schedule[-1]["capital_balance"]) == Decimal("0.00")

    def test_simulate_totals_present(self, client):
        resp = client.post(
            "/api/v1/loans/simulate",
            data=json.dumps(SIMULATE_PAYLOAD),
            content_type="application/json",
        )
        totals = resp.get_json()["totals"]
        assert "total_interest" in totals
        assert "total_paid" in totals
        assert Decimal(totals["total_interest"]) > 0

    def test_simulate_usury_exceeded_returns_422(self, client):
        payload = dict(SIMULATE_PAYLOAD, interest_rate="0.30")
        resp = client.post(
            "/api/v1/loans/simulate",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert resp.status_code == 422
        assert resp.get_json()["error"] == "USURY_CEILING_EXCEEDED"

    def test_simulate_constant_capital_has_decreasing_installments(self, client):
        payload = dict(SIMULATE_PAYLOAD, payment_modality="ABONO_CONSTANTE")
        resp = client.post(
            "/api/v1/loans/simulate",
            data=json.dumps(payload),
            content_type="application/json",
        )
        schedule = resp.get_json()["schedule"]
        totals = [Decimal(r["total_due"]) for r in schedule]
        for i in range(len(totals) - 1):
            assert totals[i] > totals[i + 1]

    def test_simulate_validation_error_on_missing_fields(self, client):
        resp = client.post(
            "/api/v1/loans/simulate",
            data=json.dumps({"amount": "1000000"}),
            content_type="application/json",
        )
        assert resp.status_code == 422
        assert "VALIDATION_ERROR" in resp.get_json()["error"]


class TestCreateLoan:
    def test_create_loan_success(self, client, sample_client):
        payload = {
            **SIMULATE_PAYLOAD,
            "client_id": str(sample_client.id),
        }
        resp = client.post(
            "/api/v1/loans",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["loan"]["status"] == "AL_DIA"
        assert len(data["schedule"]) == 12

    def test_create_loan_low_score_returns_422(self, client, db):
        from app.models import Client
        from app.models.client import DocumentType, RiskClassification

        low_score_client = Client(
            document_type=DocumentType.CC,
            document_number="99999999",
            full_name="Low Score User",
            credit_score=500,
            risk_class=RiskClassification.C,
            monthly_income=Decimal("5000000"),
        )
        db.session.add(low_score_client)
        db.session.commit()

        payload = {**SIMULATE_PAYLOAD, "client_id": str(low_score_client.id)}
        resp = client.post(
            "/api/v1/loans",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert resp.status_code == 422
        assert "CLIENT_NOT_ELIGIBLE" in resp.get_json()["error"]

    def test_create_loan_unknown_client_returns_404(self, client):
        import uuid
        payload = {**SIMULATE_PAYLOAD, "client_id": str(uuid.uuid4())}
        resp = client.post(
            "/api/v1/loans",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert resp.status_code == 404


class TestPaymentFlow:
    def _create_loan(self, client, sample_client):
        payload = {**SIMULATE_PAYLOAD, "client_id": str(sample_client.id)}
        resp = client.post(
            "/api/v1/loans",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert resp.status_code == 201
        return resp.get_json()["loan"]["id"]

    def test_register_payment_success(self, client, sample_client):
        loan_id = self._create_loan(client, sample_client)
        payment_payload = {
            "amount": "1900000",
            "payment_reference": "PSE-001-TEST",
            "payment_date": "2026-04-23",
            "payment_method": "PSE",
        }
        resp = client.post(
            f"/api/v1/loans/{loan_id}/payments",
            data=json.dumps(payment_payload),
            content_type="application/json",
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["payment"]["payment_reference"] == "PSE-001-TEST"

    def test_duplicate_payment_returns_409(self, client, sample_client):
        loan_id = self._create_loan(client, sample_client)
        payment_payload = {
            "amount": "1900000",
            "payment_reference": "PSE-DUPLICATE-TEST",
            "payment_date": "2026-04-23",
            "payment_method": "PSE",
        }
        first = client.post(
            f"/api/v1/loans/{loan_id}/payments",
            data=json.dumps(payment_payload),
            content_type="application/json",
        )
        assert first.status_code == 201

        second = client.post(
            f"/api/v1/loans/{loan_id}/payments",
            data=json.dumps(payment_payload),
            content_type="application/json",
        )
        assert second.status_code == 409
        assert "DUPLICATE_PAYMENT" in second.get_json()["error"]

    def test_statement_returns_correct_structure(self, client, sample_client):
        loan_id = self._create_loan(client, sample_client)
        resp = client.get(f"/api/v1/loans/{loan_id}/statement")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "capital_balance" in data
        assert "paid_installments" in data
        assert "pending_installments" in data
        assert len(data["pending_installments"]) == 12

    def test_statement_unknown_loan_returns_404(self, client):
        import uuid
        resp = client.get(f"/api/v1/loans/{uuid.uuid4()}/statement")
        assert resp.status_code == 404
