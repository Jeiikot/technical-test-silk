from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.errors import (
    ClientNotEligibleError,
    ClientNotFoundError,
    DuplicatePaymentError,
    LoanNotFoundError,
    UsuryCeilingExceededError,
)
from app.extensions import db
from app.models import (
    AmortizationSchedule,
    Client,
    Loan,
    LoanStatus,
    Payment,
    PaymentMethod,
    PaymentModality,
    RateType,
)
from app.services import accounting_service as acc
from app.services import financial as fin

DEBT_CAPACITY_RATIO = Decimal("0.30")


def _current_days_in_default(loan: Loan, as_of: date) -> int:
    overdue_dates = [inst.due_date for inst in loan.schedule if not inst.is_paid and inst.due_date < as_of]
    if not overdue_dates:
        return 0
    return (as_of - min(overdue_dates)).days


def _apply_payment_to_installments(loan: Loan, applied_amount: Decimal, payment_date: date) -> None:
    remaining_for_schedule = applied_amount

    for inst in sorted(loan.schedule, key=lambda x: x.installment_num):
        if inst.is_paid:
            continue

        installment_due = Decimal(str(inst.total_due))
        if remaining_for_schedule >= installment_due:
            inst.is_paid = True
            inst.paid_at = payment_date
            remaining_for_schedule -= installment_due
        else:
            break


def validate_client_eligibility(
    client: Client, requested_amount: Decimal, declared_income: Decimal | None, usury_rate_ea: Decimal
) -> None:
    if client.credit_score is None or client.credit_score <= 600:
        raise ClientNotEligibleError("Credit score must be greater than 600.")

    active_default = db.session.execute(
        select(Loan).where(Loan.client_id == client.id, Loan.status == LoanStatus.EN_MORA)
    ).scalars().first()
    if active_default:
        raise ClientNotEligibleError("Client has active loans currently in default.")

    income_for_capacity = declared_income
    if income_for_capacity is None and client.monthly_income is not None:
        income_for_capacity = Decimal(str(client.monthly_income))

    if income_for_capacity is not None:
        max_installment = income_for_capacity * DEBT_CAPACITY_RATIO
        monthly_rate = fin.convert_rate_to_monthly(usury_rate_ea, "EFECTIVA_ANUAL")
        estimated_installment = fin.calculate_fixed_installment(requested_amount, monthly_rate, 12)
        if estimated_installment > max_installment:
            raise ClientNotEligibleError(
                f"Requested amount exceeds debt capacity. Max installment: {max_installment:,.2f} COP."
            )


def create_loan(data: dict, usury_rate_ea: Decimal) -> Loan:
    client_id = data["client_id"]
    client = db.session.get(Client, client_id)
    if not client:
        raise ClientNotFoundError(f"Client {client_id} not found.")

    requested_amount = Decimal(str(data["amount"]))
    rate = Decimal(str(data["interest_rate"]))
    rate_type = data["rate_type"]
    term = data["term_months"]
    modality = data["payment_modality"]

    rate_ea = fin.nominal_mv_to_ea(rate) if rate_type == "NOMINAL_MV" else rate

    if rate_ea > usury_rate_ea:
        raise UsuryCeilingExceededError(
            f"Rate {float(rate_ea)*100:.2f}% EA exceeds usury ceiling {float(usury_rate_ea)*100:.2f}% EA."
        )

    declared_income = (
        Decimal(str(data["declared_income"])) if data.get("declared_income") is not None else None
    )
    validate_client_eligibility(client, requested_amount, declared_income, usury_rate_ea)

    monthly_rate = fin.convert_rate_to_monthly(rate, rate_type)
    disbursement_date = date.today()

    if modality == "CUOTA_FIJA":
        schedule_data = fin.build_fixed_schedule(requested_amount, monthly_rate, term, disbursement_date)
    else:
        schedule_data = fin.build_constant_capital_schedule(requested_amount, monthly_rate, term, disbursement_date)

    loan = Loan(
        client_id=client_id,
        requested_amount=requested_amount,
        approved_amount=requested_amount,
        interest_rate=rate_ea,
        rate_type_input=RateType(rate_type),
        term_months=term,
        payment_modality=PaymentModality(modality),
        status=LoanStatus.AL_DIA,
        disbursement_date=disbursement_date,
        declared_income=declared_income,
        capital_balance=requested_amount,
        accrued_interest=Decimal("0"),
    )
    db.session.add(loan)
    db.session.flush()

    for row in schedule_data:
        db.session.add(AmortizationSchedule(
            loan_id=loan.id,
            installment_num=row["installment_num"],
            due_date=row["due_date"],
            principal=row["principal"],
            interest=row["interest"],
            life_insurance=row["life_insurance"],
            other_charges=row["other_charges"],
            total_due=row["total_due"],
            capital_balance=row["capital_balance"],
        ))

    acc.entry_disbursement(loan)
    db.session.commit()
    return loan


def register_payment(loan_id: str, data: dict, usury_rate_ea: Decimal) -> Payment:
    loan = db.session.execute(
        select(Loan).where(Loan.id == loan_id).with_for_update()
    ).scalars().first()
    if not loan:
        raise LoanNotFoundError(f"Loan {loan_id} not found.")

    payment_amount = Decimal(str(data["amount"]))
    payment_date = (
        date.fromisoformat(data["payment_date"])
        if isinstance(data["payment_date"], str)
        else data["payment_date"]
    )

    remaining = payment_amount
    applied_judicial = min(remaining, Decimal("0"))
    remaining -= applied_judicial

    insurance_pending = sum(Decimal(str(i.life_insurance)) for i in loan.schedule if not i.is_paid)
    applied_insurance = min(remaining, insurance_pending)
    remaining -= applied_insurance

    days_in_default_at_payment = _current_days_in_default(loan, payment_date)

    monthly_rate = fin.convert_rate_to_monthly(loan.interest_rate, "EFECTIVA_ANUAL")
    default_interest_due = Decimal("0")
    if days_in_default_at_payment > 0:
        default_interest_due = fin.calculate_default_interest(
            Decimal(str(loan.capital_balance)), monthly_rate, days_in_default_at_payment, usury_rate_ea
        )
    applied_default = min(remaining, default_interest_due)
    remaining -= applied_default

    accrued = Decimal(str(loan.accrued_interest))
    if accrued == 0:
        next_inst = next(
            (i for i in sorted(loan.schedule, key=lambda x: x.installment_num) if not i.is_paid),
            None,
        )
        if next_inst:
            accrued = Decimal(str(next_inst.interest))
    applied_interest = min(remaining, accrued)
    remaining -= applied_interest

    capital_balance = Decimal(str(loan.capital_balance))
    applied_principal = min(remaining, capital_balance)

    payment = Payment(
        loan_id=loan.id,
        payment_reference=data["payment_reference"],
        payment_date=payment_date,
        total_amount=payment_amount,
        applied_judicial=applied_judicial,
        applied_insurance=applied_insurance,
        applied_default_int=applied_default,
        applied_interest=applied_interest,
        applied_principal=applied_principal,
        payment_method=PaymentMethod(data["payment_method"]),
    )

    try:
        db.session.add(payment)
        db.session.flush()
    except IntegrityError:
        db.session.rollback()
        raise DuplicatePaymentError(
            f"Payment reference '{data['payment_reference']}' already processed."
        )

    loan.capital_balance = capital_balance - applied_principal
    loan.accrued_interest = max(accrued - applied_interest, Decimal("0"))

    applied_to_schedule = applied_insurance + applied_interest + applied_principal
    _apply_payment_to_installments(loan, applied_to_schedule, payment_date)

    today = date.today()
    if Decimal(str(loan.capital_balance)) <= 0:
        loan.status = LoanStatus.PAGADO
        loan.days_in_default = 0
    else:
        loan.days_in_default = _current_days_in_default(loan, today)
        loan.status = LoanStatus.EN_MORA if loan.days_in_default > 0 else LoanStatus.AL_DIA

    loan.updated_at = datetime.now(timezone.utc)
    acc.entry_collection(loan, payment)
    db.session.commit()
    return payment


def get_statement(loan_id: str, usury_rate_ea: Decimal) -> dict:
    loan = db.session.get(Loan, loan_id)
    if not loan:
        raise LoanNotFoundError(f"Loan {loan_id} not found.")

    today = date.today()
    days_in_default = _current_days_in_default(loan, today)
    monthly_rate = fin.convert_rate_to_monthly(loan.interest_rate, "EFECTIVA_ANUAL")
    default_interest = Decimal("0")
    if days_in_default > 0:
        default_interest = fin.calculate_default_interest(
            Decimal(str(loan.capital_balance)), monthly_rate, days_in_default, usury_rate_ea
        )

    def _fmt(inst):
        return {
            "installment_num": inst.installment_num,
            "due_date": inst.due_date.isoformat(),
            "principal": str(inst.principal),
            "interest": str(inst.interest),
            "total_due": str(inst.total_due),
            "capital_balance": str(inst.capital_balance),
            "is_paid": inst.is_paid,
            "paid_at": inst.paid_at.isoformat() if inst.paid_at else None,
        }

    return {
        "loan": {
            "id": str(loan.id),
            "client_id": str(loan.client_id),
            "approved_amount": str(loan.approved_amount),
            "interest_rate_ea": str(loan.interest_rate),
            "term_months": loan.term_months,
            "payment_modality": loan.payment_modality.value,
            "status": loan.status.value,
            "disbursement_date": loan.disbursement_date.isoformat() if loan.disbursement_date else None,
        },
        "capital_balance": str(loan.capital_balance),
        "accrued_interest": str(loan.accrued_interest),
        "days_in_default": days_in_default,
        "default_interest_to_date": str(default_interest),
        "paid_installments": [_fmt(i) for i in loan.schedule if i.is_paid],
        "pending_installments": [_fmt(i) for i in loan.schedule if not i.is_paid],
        "statement_date": today.isoformat(),
    }
