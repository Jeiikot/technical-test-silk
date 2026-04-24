from flask import Blueprint, request, jsonify
from marshmallow import Schema, fields, validate, ValidationError

from app.extensions import db
from app.models import Client
from app.models.client import DocumentType, RiskClassification

clients_bp = Blueprint("clients", __name__, url_prefix="/api/v1/clients")


class CreateClientSchema(Schema):
    document_type = fields.Str(required=True, validate=validate.OneOf([t.value for t in DocumentType]))
    document_number = fields.Str(required=True, validate=validate.Length(min=1, max=20))
    full_name = fields.Str(required=True, validate=validate.Length(min=2, max=200))
    email = fields.Email(load_default=None)
    phone = fields.Str(load_default=None)
    city = fields.Str(load_default=None)
    credit_score = fields.Int(load_default=None, validate=validate.Range(min=0, max=1000))
    risk_class = fields.Str(load_default="A", validate=validate.OneOf([r.value for r in RiskClassification]))
    monthly_income = fields.Decimal(load_default=None, places=2, as_string=True)


_schema = CreateClientSchema()


@clients_bp.post("/")
def create_client():
    try:
        data = _schema.load(request.get_json(force=True) or {})
    except ValidationError as e:
        return jsonify({"error": "VALIDATION_ERROR", "details": e.messages}), 422

    existing = db.session.query(Client).filter_by(
        document_type=DocumentType(data["document_type"]),
        document_number=data["document_number"],
    ).first()
    if existing:
        return jsonify({"error": "CONFLICT", "message": "Client with this document already exists."}), 409

    client = Client(
        document_type=DocumentType(data["document_type"]),
        document_number=data["document_number"],
        full_name=data["full_name"],
        email=data.get("email"),
        phone=data.get("phone"),
        city=data.get("city"),
        credit_score=data.get("credit_score"),
        risk_class=RiskClassification(data.get("risk_class", "A")),
        monthly_income=data.get("monthly_income"),
    )
    db.session.add(client)
    db.session.commit()

    return jsonify({
        "client": {
            "id": str(client.id),
            "document_type": client.document_type.value,
            "document_number": client.document_number,
            "full_name": client.full_name,
            "credit_score": client.credit_score,
            "risk_class": client.risk_class.value,
            "monthly_income": str(client.monthly_income) if client.monthly_income else None,
        }
    }), 201


@clients_bp.get("/<uuid:client_id>")
def get_client(client_id):
    c = db.session.get(Client, client_id)
    if not c:
        return jsonify({"error": "CLIENT_NOT_FOUND", "message": "Client not found."}), 404
    return jsonify({
        "id": str(c.id),
        "document_type": c.document_type.value,
        "document_number": c.document_number,
        "full_name": c.full_name,
        "email": c.email,
        "phone": c.phone,
        "city": c.city,
        "credit_score": c.credit_score,
        "risk_class": c.risk_class.value,
        "monthly_income": str(c.monthly_income) if c.monthly_income else None,
    }), 200
