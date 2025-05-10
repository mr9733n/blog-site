# backend/auth/jwt_handlers.py
from flask import jsonify, current_app

from backend.models.token_blacklist import TokenBlacklist
from backend.auth.middlewares import check_if_token_revoked

def setup_jwt_handlers(jwt):
    """
    Configure JWT handlers and callbacks

    Args:
        jwt: Flask-JWT-Extended JWTManager instance
    """

    @jwt.invalid_token_loader
    def invalid_token_callback(error_string):
        """Handle invalid tokens"""
        current_app.logger.error(f"Invalid token error: {error_string}")
        return jsonify({"msg": f"Invalid token: {error_string}"}), 422

    @jwt.unauthorized_loader
    def unauthorized_callback(error_string):
        """Handle unauthorized access"""
        current_app.logger.error(f"Unauthorized error: {error_string}")
        return jsonify({"msg": f"Unauthorized: {error_string}"}), 401

    @jwt.token_in_blocklist_loader
    def check_if_token_is_revoked(jwt_header, jwt_payload):
        """Check if token is blacklisted"""
        return check_if_token_revoked(jwt_header, jwt_payload)

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        """Handle expired tokens"""
        return jsonify({
            'msg': 'The token has expired',
            'error': 'token_expired'
        }), 401

    @jwt.needs_fresh_token_loader
    def fresh_token_required_callback(jwt_header, jwt_payload):
        """Handle fresh token requirements"""
        return jsonify({
            'msg': 'Fresh token required',
            'error': 'fresh_token_required'
        }), 401