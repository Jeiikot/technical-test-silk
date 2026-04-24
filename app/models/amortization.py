import uuid
from app.extensions import db


class AmortizationSchedule(db.Model):
    __tablename__ = "amortization_schedule"

    id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    loan_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey("loans.id", ondelete="CASCADE"), nullable=False)
    installment_num = db.Column(db.Integer, nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    principal = db.Column(db.Numeric(18, 2), nullable=False)
    interest = db.Column(db.Numeric(18, 2), nullable=False)
    life_insurance = db.Column(db.Numeric(18, 2), nullable=False, default=0)
    other_charges = db.Column(db.Numeric(18, 2), nullable=False, default=0)
    total_due = db.Column(db.Numeric(18, 2), nullable=False)
    capital_balance = db.Column(db.Numeric(18, 2), nullable=False)
    is_paid = db.Column(db.Boolean, nullable=False, default=False)
    paid_at = db.Column(db.Date)

    loan = db.relationship("Loan", back_populates="schedule")

    __table_args__ = (
        db.UniqueConstraint("loan_id", "installment_num", name="uq_loan_installment"),
    )

    def __repr__(self):
        return f"<AmortizationSchedule loan={self.loan_id} #{self.installment_num}>"
