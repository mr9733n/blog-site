# backend/auth/__init__.py
from flask_jwt_extended import JWTManager

from backend.auth.middlewares import register_auth_middlewares
from backend.auth.jwt_handlers import setup_jwt_handlers
from backend.models.token_blacklist import TokenBlacklist
from backend.models.session import SessionManager


def init_auth(app):
    """
    Initialize all authentication components

    Args:
        app: Flask application instance

    Returns:
        flask_jwt_extended.JWTManager: Configured JWT manager
    """
    # Initialize JWT manager
    jwt = JWTManager(app)

    # Setup JWT handlers
    setup_jwt_handlers(jwt)

    # Register authentication middlewares
    register_auth_middlewares(app)

    # Clean up expired tokens and sessions
    with app.app_context():
        TokenBlacklist.clear_expired_tokens()
        SessionManager.clear_expired()

    return jwt