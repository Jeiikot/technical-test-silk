import uuid
import enum
from datetime import datetime, timezone
from app.extensions import db


class PaymentMethod(str, enum.Enum):
    PSE = "PSE"
    CONSIGNACION = "CONSIGNACION"
    DEBITO_AUTOMATICO = "DEBITO_AUTOMATICO"
    CORRESPONSAL = "CORRESPONSAL"


class Payment(db.Model):
    __tablename__ = "payments"

    id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    loan_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey("loans.id"), nullable=False)
    payment_reference = db.Column(db.String(100), nullable=False, unique=True)
    payment_date = db.Column(db.Date, nullable=False)
    total_amount = db.Column(db.Numeric(18, 2), nullable=False)
    applied_judicial = db.Column(db.Numeric(18, 2), nullable=False, default=0)
    applied_insurance = db.Column(db.Numeric(18, 2), nullable=False, default=0)
    applied_default_int = db.Column(db.Numeric(18, 2), nullable=False, default=0)
    applied_interest = db.Column(db.Numeric(18, 2), nullable=False, default=0)
    applied_principal = db.Column(db.Numeric(18, 2), nullable=False, default=0)
    payment_method = db.Column(db.Enum(PaymentMethod), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    loan = db.relationship("Loan", back_populates="payments")
    accounting_entries = db.relationship("AccountingEntry", back_populates="payment")

    def __repr__(self):
        return f"<Payment {self.payment_reference} amount={self.total_amount}>"
