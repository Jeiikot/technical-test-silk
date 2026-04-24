from flask import Flask

from app.config import config
from app.extensions import db, migrate
from app.errors import register_error_handlers
from app.logging_config import setup_logging


def create_app(config_name: str = "development") -> Flask:
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    db.init_app(app)
    migrate.init_app(app, db)

    setup_logging(app)
    _register_blueprints(app)
    register_error_handlers(app)

    return app


def _register_blueprints(app: Flask) -> None:
    from app.api.v1.loans import loans_bp
    from app.api.v1.clients import clients_bp
    app.register_blueprint(loans_bp)
    app.register_blueprint(clients_bp)

    @app.get("/health")
    def health():
        from flask import jsonify
        return jsonify({"status": "ok"}), 200
