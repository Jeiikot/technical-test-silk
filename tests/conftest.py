import pytest
from sqlalchemy import text

from app import create_app
from app.extensions import db as _db
from app.models import Client
from app.models.client import DocumentType, RiskClassification


@pytest.fixture(scope="session")
def app():
    application = create_app("testing")
    with application.app_context():
        _db.create_all()
        yield application
        _db.drop_all()


@pytest.fixture(scope="function")
def db(app):
    with app.app_context():
        yield _db
        _db.session.rollback()
        _db.session.execute(text(
            "TRUNCATE accounting_entries, payments, amortization_schedule, loans, clients CASCADE"
        ))
        _db.session.commit()


@pytest.fixture(scope="function")
def client(app):
    return app.test_client()


@pytest.fixture(scope="function")
def sample_client(db):
    c = Client(
        document_type=DocumentType.CC,
        document_number="12345678",
        full_name="Juan Pérez",
        email="juan@example.com",
        city="Bogotá",
        credit_score=750,
        risk_class=RiskClassification.A,
    )
    db.session.add(c)
    db.session.commit()
    return c
