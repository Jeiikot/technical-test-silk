from datetime import date
from decimal import Decimal

from flask import Blueprint, current_app, jsonify, request
from marshmallow import ValidationError

from app.schemas.loan_schemas import CreateLoanSchema, RegisterPaymentSchema, SimulateLoanSchema
from app.services import financial as fin
from app.services import loan_service

loans_bp = Blueprint("loans", __name__, url_prefix="/api/v1/loans")

_simulate_schema = SimulateLoanSchema()
_create_schema = CreateLoanSchema()
_payment_schema = RegisterPaymentSchema()


def _usury_rate() -> Decimal:
    return current_app.config["USURY_RATE_EA"]


@loans_bp.post("/simulate")
def simulate_loan():
    try:
        data = _simulate_schema.load(request.get_json(force=True) or {})
    except ValidationError as e:
        return jsonify({"error": "VALIDATION_ERROR", "details": e.messages}), 422

    amount = Decimal(str(data["amount"]))
    rate = Decimal(str(data["interest_rate"]))
    rate_type = data["rate_type"]
    term = data["term_months"]
    modality = data["payment_modality"]

    monthly_rate = fin.convert_rate_to_monthly(rate, rate_type)

    if rate_type == "NOMINAL_MV":
        rate_ea = fin.nominal_mv_to_ea(rate)
    else:
        rate_ea = rate

    if rate_ea > _usury_rate():
        return jsonify({
            "error": "USURY_CEILING_EXCEEDED",
            "message": f"Rate {float(rate_ea)*100:.4f}% EA exceeds usury ceiling {float(_usury_rate())*100:.2f}% EA.",
        }), 422

    disbursement_date = date.today()
    if modality == "CUOTA_FIJA":
        schedule = fin.build_fixed_schedule(amount, monthly_rate, term, disbursement_date)
    else:
        schedule = fin.build_constant_capital_schedule(amount, monthly_rate, term, disbursement_date)

    totals = fin.schedule_totals(schedule)

    serialized_schedule = []
    for row in schedule:
        serialized_schedule.append({
            "installment_num": row["installment_num"],
            "due_date": row["due_date"].isoformat(),
            "principal": str(row["principal"]),
            "interest": str(row["interest"]),
            "life_insurance": str(row["life_insurance"]),
            "other_charges": str(row["other_charges"]),
            "total_due": str(row["total_due"]),
            "capital_balance": str(row["capital_balance"]),
        })

    return jsonify({
        "simulation": {
            "amount": str(amount),
            "interest_rate_input": str(rate),
            "rate_type": rate_type,
            "interest_rate_ea": str(rate_ea.quantize(Decimal("0.000001"))),
            "monthly_rate": str(monthly_rate.quantize(Decimal("0.000001"))),
            "term_months": term,
            "payment_modality": modality,
        },
        "schedule": serialized_schedule,
        "totals": {k: str(v) for k, v in totals.items()},
    }), 200


@loans_bp.post("")
@loans_bp.post("/")
def create_loan():
    try:
        data = _create_schema.load(request.get_json(force=True) or {})
    except ValidationError as e:
        return jsonify({"error": "VALIDATION_ERROR", "details": e.messages}), 422

    loan = loan_service.create_loan(data, _usury_rate())

    schedule_out = []
    for inst in loan.schedule:
        schedule_out.append({
            "installment_num": inst.installment_num,
            "due_date": inst.due_date.isoformat(),
            "principal": str(inst.principal),
            "interest": str(inst.interest),
            "total_due": str(inst.total_due),
            "capital_balance": str(inst.capital_balance),
        })

    return jsonify({
        "loan": {
            "id": str(loan.id),
            "client_id": str(loan.client_id),
            "approved_amount": str(loan.approved_amount),
            "interest_rate_ea": str(loan.interest_rate),
            "term_months": loan.term_months,
            "payment_modality": loan.payment_modality.value,
            "status": loan.status.value,
            "disbursement_date": loan.disbursement_date.isoformat(),
        },
        "schedule": schedule_out,
    }), 201


@loans_bp.post("/<uuid:loan_id>/payments")
def register_payment(loan_id):
    try:
        data = _payment_schema.load(request.get_json(force=True) or {})
    except ValidationError as e:
        return jsonify({"error": "VALIDATION_ERROR", "details": e.messages}), 422

    payment = loan_service.register_payment(str(loan_id), data, _usury_rate())

    return jsonify({
        "payment": {
            "id": str(payment.id),
            "loan_id": str(payment.loan_id),
            "payment_reference": payment.payment_reference,
            "payment_date": payment.payment_date.isoformat(),
            "total_amount": str(payment.total_amount),
            "applied_breakdown": {
                "judicial_costs": str(payment.applied_judicial),
                "insurance": str(payment.applied_insurance),
                "default_interest": str(payment.applied_default_int),
                "accrued_interest": str(payment.applied_interest),
                "principal": str(payment.applied_principal),
            },
            "payment_method": payment.payment_method.value,
        }
    }), 201


@loans_bp.get("/<uuid:loan_id>/statement")
def get_statement(loan_id):
    statement = loan_service.get_statement(str(loan_id), _usury_rate())
    return jsonify(statement), 200
