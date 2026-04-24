from marshmallow import Schema, fields, validate, validates, ValidationError


VALID_RATE_TYPES = ["NOMINAL_MV", "EFECTIVA_ANUAL"]
VALID_MODALITIES = ["CUOTA_FIJA", "ABONO_CONSTANTE"]
VALID_PAYMENT_METHODS = ["PSE", "CONSIGNACION", "DEBITO_AUTOMATICO", "CORRESPONSAL"]


class SimulateLoanSchema(Schema):
    amount = fields.Decimal(required=True, places=2, as_string=True)
    interest_rate = fields.Decimal(required=True, places=6, as_string=True)
    rate_type = fields.Str(required=True, validate=validate.OneOf(VALID_RATE_TYPES))
    term_months = fields.Int(required=True, validate=validate.Range(min=1, max=360))
    payment_modality = fields.Str(required=True, validate=validate.OneOf(VALID_MODALITIES))

    @validates("amount")
    def validate_amount(self, value, **kwargs):
        from decimal import Decimal
        if Decimal(str(value)) <= 0:
            raise ValidationError("Amount must be greater than zero.")

    @validates("interest_rate")
    def validate_rate(self, value, **kwargs):
        from decimal import Decimal
        r = Decimal(str(value))
        if r <= 0 or r >= 1:
            raise ValidationError("Interest rate must be between 0 and 1 (e.g., 0.24 for 24%).")


class CreateLoanSchema(SimulateLoanSchema):
    client_id = fields.UUID(required=True)
    declared_income = fields.Decimal(load_default=None, places=2, as_string=True)


class RegisterPaymentSchema(Schema):
    amount = fields.Decimal(required=True, places=2, as_string=True)
    payment_reference = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    payment_date = fields.Date(required=True)
    payment_method = fields.Str(required=True, validate=validate.OneOf(VALID_PAYMENT_METHODS))

    @validates("amount")
    def validate_amount(self, value, **kwargs):
        from decimal import Decimal
        if Decimal(str(value)) <= 0:
            raise ValidationError("Payment amount must be greater than zero.")


