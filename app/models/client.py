import enum
import uuid
from datetime import datetime, timezone

from app.extensions import db


class DocumentType(str, enum.Enum):
    CC = "CC"
    CE = "CE"
    NIT = "NIT"
    PASAPORTE = "PASAPORTE"


class RiskClassification(str, enum.Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"


class Client(db.Model):
    __tablename__ = "clients"

    id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_type = db.Column(db.Enum(DocumentType), nullable=False)
    document_number = db.Column(db.String(20), nullable=False)
    full_name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(150))
    phone = db.Column(db.String(20))
    city = db.Column(db.String(100))
    credit_score = db.Column(db.Integer)
    risk_class = db.Column(db.Enum(RiskClassification), nullable=False, default=RiskClassification.A)
    monthly_income = db.Column(db.Numeric(18, 2))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    loans = db.relationship("Loan", back_populates="client", lazy="dynamic")

    __table_args__ = (
        db.UniqueConstraint("document_type", "document_number", name="uq_client_document"),
        db.CheckConstraint("credit_score BETWEEN 0 AND 1000", name="chk_credit_score_range"),
    )

    def __repr__(self):
        return f"<Client {self.document_type.value} {self.document_number}>"
