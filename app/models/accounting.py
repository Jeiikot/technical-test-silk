import uuid
import enum
from datetime import datetime, timezone
from app.extensions import db


class PUCEntryType(str, enum.Enum):
    DESEMBOLSO = "DESEMBOLSO"
    CAUSACION_INTERESES = "CAUSACION_INTERESES"
    RECAUDO = "RECAUDO"
    MORA = "MORA"


class AccountingEntry(db.Model):
    __tablename__ = "accounting_entries"

    id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    loan_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey("loans.id"), nullable=False)
    payment_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey("payments.id"), nullable=True)
    entry_type = db.Column(db.Enum(PUCEntryType), nullable=False)
    entry_date = db.Column(db.Date, nullable=False)
    puc_debit = db.Column(db.String(10), nullable=False)
    puc_credit = db.Column(db.String(10), nullable=False)
    debit_amount = db.Column(db.Numeric(18, 2), nullable=False)
    credit_amount = db.Column(db.Numeric(18, 2), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    loan = db.relationship("Loan", back_populates="accounting_entries")
    payment = db.relationship("Payment", back_populates="accounting_entries")

    __table_args__ = (
        db.CheckConstraint("debit_amount > 0", name="chk_debit_positive"),
        db.CheckConstraint("credit_amount > 0", name="chk_credit_positive"),
        db.CheckConstraint("debit_amount = credit_amount", name="chk_partida_doble"),
    )

    def __repr__(self):
        return f"<AccountingEntry {self.entry_type.value} {self.debit_amount}>"
