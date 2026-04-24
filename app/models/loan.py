import uuid
import enum
from datetime import datetime, timezone
from app.extensions import db


class RateType(str, enum.Enum):
    NOMINAL_MV = "NOMINAL_MV"
    EFECTIVA_ANUAL = "EFECTIVA_ANUAL"


class PaymentModality(str, enum.Enum):
    CUOTA_FIJA = "CUOTA_FIJA"
    ABONO_CONSTANTE = "ABONO_CONSTANTE"


class LoanStatus(str, enum.Enum):
    RADICADO = "RADICADO"
    APROBADO = "APROBADO"
    DESEMBOLSADO = "DESEMBOLSADO"
    AL_DIA = "AL_DIA"
    EN_MORA = "EN_MORA"
    REESTRUCTURADO = "REESTRUCTURADO"
    CASTIGADO = "CASTIGADO"
    PAGADO = "PAGADO"


class Loan(db.Model):
    __tablename__ = "loans"

    id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey("clients.id"), nullable=False)
    requested_amount = db.Column(db.Numeric(18, 2), nullable=False)
    approved_amount = db.Column(db.Numeric(18, 2))
    interest_rate = db.Column(db.Numeric(8, 6), nullable=False)
    rate_type_input = db.Column(db.Enum(RateType), nullable=False)
    term_months = db.Column(db.Integer, nullable=False)
    payment_modality = db.Column(db.Enum(PaymentModality), nullable=False)
    status = db.Column(db.Enum(LoanStatus), nullable=False, default=LoanStatus.RADICADO)
    disbursement_date = db.Column(db.Date)
    declared_income = db.Column(db.Numeric(18, 2))
    capital_balance = db.Column(db.Numeric(18, 2))
    accrued_interest = db.Column(db.Numeric(18, 2), nullable=False, default=0)
    days_in_default = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    client = db.relationship("Client", back_populates="loans")
    schedule = db.relationship("AmortizationSchedule", back_populates="loan", order_by="AmortizationSchedule.installment_num", cascade="all, delete-orphan")
    payments = db.relationship("Payment", back_populates="loan", order_by="Payment.payment_date")
    accounting_entries = db.relationship("AccountingEntry", back_populates="loan")

    __table_args__ = (
        db.CheckConstraint("term_months > 0", name="chk_positive_term"),
    )

    def __repr__(self):
        return f"<Loan {self.id} status={self.status.value}>"
