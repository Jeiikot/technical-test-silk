"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-04-23
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Enums
    document_type = postgresql.ENUM("CC", "CE", "NIT", "PASAPORTE", name="documenttype")
    risk_classification = postgresql.ENUM("A", "B", "C", "D", "E", name="riskclassification")
    rate_type = postgresql.ENUM("NOMINAL_MV", "EFECTIVA_ANUAL", name="ratetype")
    payment_modality = postgresql.ENUM("CUOTA_FIJA", "ABONO_CONSTANTE", name="paymentmodality")
    loan_status = postgresql.ENUM(
        "RADICADO", "APROBADO", "DESEMBOLSADO", "AL_DIA",
        "EN_MORA", "REESTRUCTURADO", "CASTIGADO", "PAGADO",
        name="loanstatus",
    )
    payment_method = postgresql.ENUM(
        "PSE", "CONSIGNACION", "DEBITO_AUTOMATICO", "CORRESPONSAL",
        name="paymentmethod",
    )
    puc_entry_type = postgresql.ENUM(
        "DESEMBOLSO", "CAUSACION_INTERESES", "RECAUDO", "MORA",
        name="pucentrytype",
    )

    for enum in [document_type, risk_classification, rate_type, payment_modality,
                 loan_status, payment_method, puc_entry_type]:
        enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "clients",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("document_type", sa.Enum("CC", "CE", "NIT", "PASAPORTE", name="documenttype"), nullable=False),
        sa.Column("document_number", sa.String(20), nullable=False),
        sa.Column("full_name", sa.String(200), nullable=False),
        sa.Column("email", sa.String(150)),
        sa.Column("phone", sa.String(20)),
        sa.Column("city", sa.String(100)),
        sa.Column("credit_score", sa.Integer),
        sa.Column("risk_class", sa.Enum("A", "B", "C", "D", "E", name="riskclassification"), nullable=False, server_default="A"),
        sa.Column("monthly_income", sa.Numeric(18, 2)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("document_type", "document_number", name="uq_client_document"),
        sa.CheckConstraint("credit_score BETWEEN 0 AND 1000", name="chk_credit_score_range"),
    )

    op.create_table(
        "loans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("requested_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("approved_amount", sa.Numeric(18, 2)),
        sa.Column("interest_rate", sa.Numeric(8, 6), nullable=False),
        sa.Column("rate_type_input", sa.Enum("NOMINAL_MV", "EFECTIVA_ANUAL", name="ratetype"), nullable=False),
        sa.Column("term_months", sa.Integer, nullable=False),
        sa.Column("payment_modality", sa.Enum("CUOTA_FIJA", "ABONO_CONSTANTE", name="paymentmodality"), nullable=False),
        sa.Column("status", sa.Enum("RADICADO", "APROBADO", "DESEMBOLSADO", "AL_DIA", "EN_MORA", "REESTRUCTURADO", "CASTIGADO", "PAGADO", name="loanstatus"), nullable=False, server_default="RADICADO"),
        sa.Column("disbursement_date", sa.Date),
        sa.Column("declared_income", sa.Numeric(18, 2)),
        sa.Column("capital_balance", sa.Numeric(18, 2)),
        sa.Column("accrued_interest", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("days_in_default", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.CheckConstraint("term_months > 0", name="chk_positive_term"),
    )
    op.create_index("idx_loans_client", "loans", ["client_id"])
    op.create_index("idx_loans_status", "loans", ["status"])

    op.create_table(
        "amortization_schedule",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("loan_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("loans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("installment_num", sa.Integer, nullable=False),
        sa.Column("due_date", sa.Date, nullable=False),
        sa.Column("principal", sa.Numeric(18, 2), nullable=False),
        sa.Column("interest", sa.Numeric(18, 2), nullable=False),
        sa.Column("life_insurance", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("other_charges", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("total_due", sa.Numeric(18, 2), nullable=False),
        sa.Column("capital_balance", sa.Numeric(18, 2), nullable=False),
        sa.Column("is_paid", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("paid_at", sa.Date),
        sa.UniqueConstraint("loan_id", "installment_num", name="uq_loan_installment"),
    )
    op.create_index("idx_amort_loan", "amortization_schedule", ["loan_id"])

    op.create_table(
        "payments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("loan_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("loans.id"), nullable=False),
        sa.Column("payment_reference", sa.String(100), nullable=False),
        sa.Column("payment_date", sa.Date, nullable=False),
        sa.Column("total_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("applied_judicial", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("applied_insurance", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("applied_default_int", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("applied_interest", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("applied_principal", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("payment_method", sa.Enum("PSE", "CONSIGNACION", "DEBITO_AUTOMATICO", "CORRESPONSAL", name="paymentmethod"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("payment_reference", name="uq_payment_reference"),
    )
    op.create_index("idx_payments_loan", "payments", ["loan_id"])

    op.create_table(
        "accounting_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("loan_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("loans.id"), nullable=False),
        sa.Column("payment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("payments.id"), nullable=True),
        sa.Column("entry_type", sa.Enum("DESEMBOLSO", "CAUSACION_INTERESES", "RECAUDO", "MORA", name="pucentrytype"), nullable=False),
        sa.Column("entry_date", sa.Date, nullable=False),
        sa.Column("puc_debit", sa.String(10), nullable=False),
        sa.Column("puc_credit", sa.String(10), nullable=False),
        sa.Column("debit_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("credit_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.CheckConstraint("debit_amount > 0", name="chk_debit_positive"),
        sa.CheckConstraint("credit_amount > 0", name="chk_credit_positive"),
        sa.CheckConstraint("debit_amount = credit_amount", name="chk_partida_doble"),
    )
    op.create_index("idx_accounting_loan", "accounting_entries", ["loan_id"])
    op.create_index("idx_accounting_date", "accounting_entries", ["entry_date"])


def downgrade():
    op.drop_table("accounting_entries")
    op.drop_table("payments")
    op.drop_table("amortization_schedule")
    op.drop_table("loans")
    op.drop_table("clients")

    for name in ["documenttype", "riskclassification", "ratetype", "paymentmodality",
                 "loanstatus", "paymentmethod", "pucentrytype"]:
        op.execute(f"DROP TYPE IF EXISTS {name}")
