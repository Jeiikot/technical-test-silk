import logging
import uuid
from pythonjsonlogger import jsonlogger
from flask import g, request


class RequestContextFilter(logging.Filter):
    def filter(self, record):
        record.request_id = getattr(g, "request_id", "N/A") if request else "N/A"
        record.path = request.path if request else "N/A"
        record.method = request.method if request else "N/A"
        return True


def setup_logging(app):
    handler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s %(request_id)s %(path)s %(method)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    handler.setFormatter(formatter)
    handler.addFilter(RequestContextFilter())

    log_level = logging.DEBUG if app.debug else logging.INFO
    app.logger.setLevel(log_level)
    app.logger.handlers = [handler]
    app.logger.propagate = False

    @app.before_request
    def assign_request_id():
        g.request_id = str(uuid.uuid4())

    @app.after_request
    def log_request(response):
        app.logger.info(
            "request completed",
            extra={
                "status_code": response.status_code,
                "request_id": getattr(g, "request_id", "N/A"),
            },
        )
        return response
