from flask import jsonify


class APIError(Exception):
    status_code = 500
    error_code = "INTERNAL_ERROR"

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class ClientNotFoundError(APIError):
    status_code = 404
    error_code = "CLIENT_NOT_FOUND"


class LoanNotFoundError(APIError):
    status_code = 404
    error_code = "LOAN_NOT_FOUND"


class ClientNotEligibleError(APIError):
    status_code = 422
    error_code = "CLIENT_NOT_ELIGIBLE"


class DuplicatePaymentError(APIError):
    status_code = 409
    error_code = "DUPLICATE_PAYMENT"


class UsuryCeilingExceededError(APIError):
    status_code = 422
    error_code = "USURY_CEILING_EXCEEDED"


def register_error_handlers(app):
    @app.errorhandler(APIError)
    def handle_api_error(e):
        return jsonify({"error": e.error_code, "message": e.message, "status_code": e.status_code}), e.status_code

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "NOT_FOUND", "message": "The requested resource was not found.", "status_code": 404}), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({"error": "METHOD_NOT_ALLOWED", "message": "HTTP method not allowed.", "status_code": 405}), 405

    @app.errorhandler(422)
    def unprocessable(e):
        return jsonify({"error": "VALIDATION_ERROR", "message": str(e), "status_code": 422}), 422

    @app.errorhandler(500)
    def internal_error(e):
        return jsonify({"error": "INTERNAL_ERROR", "message": "An unexpected error occurred.", "status_code": 500}), 500
