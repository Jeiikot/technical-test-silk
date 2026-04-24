from decimal import Decimal


def apply_payment_order(amount, judicial, insurance, default_int, accrued_interest, capital):
    remaining = amount
    results = {}

    results["judicial"] = min(remaining, judicial)
    remaining -= results["judicial"]

    results["insurance"] = min(remaining, insurance)
    remaining -= results["insurance"]

    results["default_interest"] = min(remaining, default_int)
    remaining -= results["default_interest"]

    results["accrued_interest"] = min(remaining, accrued_interest)
    remaining -= results["accrued_interest"]

    results["principal"] = min(remaining, capital)
    remaining -= results["principal"]

    results["unallocated"] = remaining
    return results


class TestPaymentApplicationOrder:
    def test_full_payment_no_mora(self):
        result = apply_payment_order(
            amount=Decimal("1000000"),
            judicial=Decimal("0"),
            insurance=Decimal("0"),
            default_int=Decimal("0"),
            accrued_interest=Decimal("200000"),
            capital=Decimal("800000"),
        )
        assert result["accrued_interest"] == Decimal("200000")
        assert result["principal"] == Decimal("800000")
        assert result["unallocated"] == Decimal("0")

    def test_partial_payment_covers_interest_only(self):
        result = apply_payment_order(
            amount=Decimal("150000"),
            judicial=Decimal("0"),
            insurance=Decimal("0"),
            default_int=Decimal("0"),
            accrued_interest=Decimal("200000"),
            capital=Decimal("800000"),
        )
        assert result["accrued_interest"] == Decimal("150000")
        assert result["principal"] == Decimal("0")

    def test_mora_applied_before_interest(self):
        result = apply_payment_order(
            amount=Decimal("500000"),
            judicial=Decimal("0"),
            insurance=Decimal("0"),
            default_int=Decimal("300000"),
            accrued_interest=Decimal("200000"),
            capital=Decimal("800000"),
        )
        assert result["default_interest"] == Decimal("300000")
        assert result["accrued_interest"] == Decimal("200000")
        assert result["principal"] == Decimal("0")

    def test_judicial_costs_have_highest_priority(self):
        result = apply_payment_order(
            amount=Decimal("100000"),
            judicial=Decimal("80000"),
            insurance=Decimal("50000"),
            default_int=Decimal("50000"),
            accrued_interest=Decimal("50000"),
            capital=Decimal("1000000"),
        )
        assert result["judicial"] == Decimal("80000")
        assert result["insurance"] == Decimal("20000")
        assert result["default_interest"] == Decimal("0")

    def test_overpayment_leaves_unallocated(self):
        result = apply_payment_order(
            amount=Decimal("2000000"),
            judicial=Decimal("0"),
            insurance=Decimal("0"),
            default_int=Decimal("0"),
            accrued_interest=Decimal("200000"),
            capital=Decimal("800000"),
        )
        assert result["unallocated"] == Decimal("1000000")
