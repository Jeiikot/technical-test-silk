from decimal import Decimal, ROUND_HALF_UP
from datetime import date
from dateutil.relativedelta import relativedelta


CENTS = Decimal("0.01")


def to_decimal(value) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def convert_rate_to_monthly(rate: Decimal, rate_type: str) -> Decimal:
    rate = to_decimal(rate)
    if rate_type == "NOMINAL_MV":
        return rate / Decimal("12")
    if rate_type == "EFECTIVA_ANUAL":
        return (1 + rate) ** (Decimal("1") / Decimal("12")) - Decimal("1")
    raise ValueError(f"Unknown rate_type: {rate_type}")


def nominal_mv_to_ea(nominal_mv: Decimal) -> Decimal:
    nominal_mv = to_decimal(nominal_mv)
    monthly = nominal_mv / Decimal("12")
    return (Decimal("1") + monthly) ** Decimal("12") - Decimal("1")



def calculate_fixed_installment(principal: Decimal, monthly_rate: Decimal, n: int) -> Decimal:
    principal = to_decimal(principal)
    i = to_decimal(monthly_rate)
    factor = (Decimal("1") + i) ** n
    return (principal * (i * factor) / (factor - Decimal("1"))).quantize(CENTS, rounding=ROUND_HALF_UP)


def build_fixed_schedule(
    principal: Decimal, monthly_rate: Decimal, n: int, disbursement_date: date
) -> list[dict]:
    principal = to_decimal(principal)
    i = to_decimal(monthly_rate)
    installment = calculate_fixed_installment(principal, i, n)
    balance = principal
    schedule = []

    for k in range(1, n + 1):
        interest = (balance * i).quantize(CENTS, rounding=ROUND_HALF_UP)
        if k == n:
            principal_payment = balance
            total = (balance + interest).quantize(CENTS, rounding=ROUND_HALF_UP)
        else:
            principal_payment = installment - interest
            total = installment

        balance = (balance - principal_payment).quantize(CENTS, rounding=ROUND_HALF_UP)
        schedule.append({
            "installment_num": k,
            "due_date": disbursement_date + relativedelta(months=k),
            "principal": principal_payment.quantize(CENTS, rounding=ROUND_HALF_UP),
            "interest": interest,
            "life_insurance": Decimal("0.00"),
            "other_charges": Decimal("0.00"),
            "total_due": total,
            "capital_balance": balance if balance > 0 else Decimal("0.00"),
        })

    return schedule


def build_constant_capital_schedule(
    principal: Decimal, monthly_rate: Decimal, n: int, disbursement_date: date
) -> list[dict]:
    principal = to_decimal(principal)
    i = to_decimal(monthly_rate)
    capital_payment = (principal / n).quantize(CENTS, rounding=ROUND_HALF_UP)
    balance = principal
    schedule = []

    for k in range(1, n + 1):
        interest = (balance * i).quantize(CENTS, rounding=ROUND_HALF_UP)
        actual_capital = balance if k == n else capital_payment
        balance = (balance - actual_capital).quantize(CENTS, rounding=ROUND_HALF_UP)
        schedule.append({
            "installment_num": k,
            "due_date": disbursement_date + relativedelta(months=k),
            "principal": actual_capital,
            "interest": interest,
            "life_insurance": Decimal("0.00"),
            "other_charges": Decimal("0.00"),
            "total_due": (actual_capital + interest).quantize(CENTS, rounding=ROUND_HALF_UP),
            "capital_balance": balance if balance > 0 else Decimal("0.00"),
        })

    return schedule


def calculate_default_interest(
    balance_in_default: Decimal,
    monthly_rate: Decimal,
    days_late: int,
    usury_rate_ea: Decimal,
) -> Decimal:
    balance_in_default = to_decimal(balance_in_default)
    monthly_rate = to_decimal(monthly_rate)

    mora_monthly = monthly_rate * Decimal("1.5")
    usury_monthly = convert_rate_to_monthly(usury_rate_ea, "EFECTIVA_ANUAL")
    mora_monthly = min(mora_monthly, usury_monthly)

    return (balance_in_default * (mora_monthly / Decimal("30")) * days_late).quantize(
        CENTS, rounding=ROUND_HALF_UP
    )


def schedule_totals(schedule: list[dict]) -> dict:
    total_interest = sum(row["interest"] for row in schedule)
    total_principal = sum(row["principal"] for row in schedule)
    total_paid = sum(row["total_due"] for row in schedule)
    return {
        "total_interest": Decimal(str(total_interest)).quantize(CENTS),
        "total_principal": Decimal(str(total_principal)).quantize(CENTS),
        "total_paid": Decimal(str(total_paid)).quantize(CENTS),
    }
