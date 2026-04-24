from datetime import date
from decimal import Decimal

from app.extensions import db
from app.models.accounting import AccountingEntry, PUCEntryType

PUC_CARTERA = "141005"
PUC_INTERESES_CAUSADOS = "270505"
PUC_INGRESO_INTERESES = "411005"
PUC_INGRESO_MORA = "410520"
PUC_CAJA = "111005"


def _entry(loan_id, entry_type, entry_date, puc_debit, puc_credit, amount, description, payment_id=None):
    e = AccountingEntry(
        loan_id=loan_id,
        payment_id=payment_id,
        entry_type=entry_type,
        entry_date=entry_date,
        puc_debit=puc_debit,
        puc_credit=puc_credit,
        debit_amount=amount,
        credit_amount=amount,
        description=description,
    )
    db.session.add(e)
    return e


def entry_disbursement(loan) -> AccountingEntry:
    amount = Decimal(str(loan.approved_amount))
    return _entry(
        loan_id=loan.id,
        entry_type=PUCEntryType.DESEMBOLSO,
        entry_date=loan.disbursement_date,
        puc_debit=PUC_CARTERA,
        puc_credit=PUC_CAJA,
        amount=amount,
        description=f"Disbursement {amount:,.2f} COP",
    )


def entry_interest_accrual(loan, interest_amount: Decimal, accrual_date: date) -> AccountingEntry:
    return _entry(
        loan_id=loan.id,
        entry_type=PUCEntryType.CAUSACION_INTERESES,
        entry_date=accrual_date,
        puc_debit=PUC_INTERESES_CAUSADOS,
        puc_credit=PUC_INGRESO_INTERESES,
        amount=interest_amount,
        description=f"Interest accrual {accrual_date.strftime('%Y-%m')}",
    )


def entry_collection(loan, payment) -> list[AccountingEntry]:
    entries = []
    applied_interest = Decimal(str(payment.applied_interest))
    applied_principal = Decimal(str(payment.applied_principal))
    applied_default = Decimal(str(payment.applied_default_int))

    if applied_interest > 0:
        entries.append(_entry(
            loan_id=loan.id,
            payment_id=payment.id,
            entry_type=PUCEntryType.RECAUDO,
            entry_date=payment.payment_date,
            puc_debit=PUC_CAJA,
            puc_credit=PUC_INTERESES_CAUSADOS,
            amount=applied_interest,
            description=f"Payment {payment.payment_reference} -interest",
        ))

    if applied_principal > 0:
        entries.append(_entry(
            loan_id=loan.id,
            payment_id=payment.id,
            entry_type=PUCEntryType.RECAUDO,
            entry_date=payment.payment_date,
            puc_debit=PUC_CAJA,
            puc_credit=PUC_CARTERA,
            amount=applied_principal,
            description=f"Payment {payment.payment_reference} -principal",
        ))

    if applied_default > 0:
        entries.append(_entry(
            loan_id=loan.id,
            payment_id=payment.id,
            entry_type=PUCEntryType.MORA,
            entry_date=payment.payment_date,
            puc_debit=PUC_CAJA,
            puc_credit=PUC_INGRESO_MORA,
            amount=applied_default,
            description=f"Payment {payment.payment_reference} -default interest",
        ))

    return entries
