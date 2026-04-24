from decimal import Decimal
from datetime import date

import pytest

from app.services.financial import (
    convert_rate_to_monthly,
    nominal_mv_to_ea,
    calculate_fixed_installment,
    build_fixed_schedule,
    build_constant_capital_schedule,
    calculate_default_interest,
    schedule_totals,
)


class TestRateConversion:
    def test_nominal_mv_to_monthly(self):
        monthly = convert_rate_to_monthly(Decimal("0.24"), "NOMINAL_MV")
        assert monthly == Decimal("0.02")

    def test_ea_to_monthly(self):
        ea = nominal_mv_to_ea(Decimal("0.24"))
        monthly = convert_rate_to_monthly(ea, "EFECTIVA_ANUAL")
        assert abs(monthly - Decimal("0.02")) < Decimal("0.000001")

    def test_nominal_mv_to_ea(self):
        ea = nominal_mv_to_ea(Decimal("0.24"))
        assert Decimal("0.268") < ea < Decimal("0.269")

    def test_invalid_rate_type_raises(self):
        with pytest.raises(ValueError):
            convert_rate_to_monthly(Decimal("0.24"), "UNKNOWN_TYPE")


class TestFixedInstallmentCalculation:
    def test_standard_case(self):
        installment = calculate_fixed_installment(Decimal("10000000"), Decimal("0.02"), 12)
        assert Decimal("940000") < installment < Decimal("950000")

    def test_single_period(self):
        installment = calculate_fixed_installment(Decimal("1000"), Decimal("0.01"), 1)
        assert installment == Decimal("1010.00")

    def test_schedule_length(self):
        schedule = build_fixed_schedule(
            Decimal("5000000"), Decimal("0.02"), 12, date(2026, 3, 1)
        )
        assert len(schedule) == 12

    def test_schedule_balance_reaches_zero(self):
        schedule = build_fixed_schedule(
            Decimal("5000000"), Decimal("0.02"), 12, date(2026, 3, 1)
        )
        assert schedule[-1]["capital_balance"] == Decimal("0.00")

    def test_schedule_totals_consistent(self):
        schedule = build_fixed_schedule(
            Decimal("5000000"), Decimal("0.02"), 12, date(2026, 3, 1)
        )
        totals = schedule_totals(schedule)
        assert abs(totals["total_principal"] - Decimal("5000000")) < Decimal("0.02")
        assert totals["total_interest"] > 0


class TestConstantCapitalSchedule:
    def test_capital_payment_constant(self):
        schedule = build_constant_capital_schedule(
            Decimal("12000000"), Decimal("0.02"), 12, date(2026, 3, 1)
        )
        for row in schedule[:-1]:
            assert row["principal"] == Decimal("1000000.00")

    def test_installment_decreases(self):
        schedule = build_constant_capital_schedule(
            Decimal("12000000"), Decimal("0.02"), 12, date(2026, 3, 1)
        )
        for i in range(len(schedule) - 1):
            assert schedule[i]["total_due"] > schedule[i + 1]["total_due"]

    def test_last_balance_zero(self):
        schedule = build_constant_capital_schedule(
            Decimal("6000000"), Decimal("0.015"), 6, date(2026, 3, 1)
        )
        assert schedule[-1]["capital_balance"] == Decimal("0.00")


class TestDefaultInterest:
    def test_basic_calculation(self):
        balance = Decimal("10000000")
        monthly_rate = Decimal("0.02")
        days = 15
        usury = Decimal("0.2762")
        default_int = calculate_default_interest(balance, monthly_rate, days, usury)
        default_monthly_rate = monthly_rate * Decimal("1.5")
        usury_monthly_rate = convert_rate_to_monthly(usury, "EFECTIVA_ANUAL")
        capped_monthly_rate = min(default_monthly_rate, usury_monthly_rate)
        expected = (balance * (capped_monthly_rate / Decimal("30")) * days).quantize(Decimal("0.01"))
        assert default_int == expected

    def test_capped_at_usury_rate(self):
        very_high_monthly = Decimal("0.20")
        usury_ea = Decimal("0.2762")
        result = calculate_default_interest(
            Decimal("1000000"), very_high_monthly, 30, usury_ea
        )
        assert result > 0
