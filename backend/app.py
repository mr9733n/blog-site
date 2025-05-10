# backend/app.py
import os
import sqlite3
import logging
import datetime
import sys
from flask import Flask, g, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv

from backend.config import get_config
from backend.models.base import get_db
from backend.auth import init_auth
from backend.routes.admin import admin_bp
from backend.routes.user import user_bp
from backend.routes.posts import posts_bp
from backend.routes.images import images_bp
from backend.routes.auth import auth_bp
from backend.auth.security_middleware import apply_security_middleware


# Add backend directory to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
load_dotenv()


def configure_logging(app):
    """Configure application logging"""
    log_level = logging.DEBUG if app.config['DEBUG'] else logging.INFO

    # Configure the root logger
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Get a logger for your app
    logger = logging.getLogger('blog-app')
    logger.setLevel(log_level)

    # Add it to app for easy access
    app.logger = logger

    if not app.debug:
        security_handler = logging.FileHandler('security.log')
        security_handler.setLevel(logging.WARNING)
        security_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - [SECURITY] %(levelname)s - %(message)s'
        )
        security_handler.setFormatter(security_formatter)
        app.logger.addHandler(security_handler)

    return logger


def configure_cors(app):
    """Configure enhanced CORS settings for the application"""
    from flask_cors import CORS

    # Улучшенные настройки CORS для улучшения безопасности и совместимости
    cors_options = {
        "resources": {r"/api/*": {
            "origins": app.config.get('CORS_ORIGINS_DEV') if app.debug else app.config.get('CORS_ORIGINS_PROD', '*')}},
        "supports_credentials": True,  # Важно для работы с куками аутентификации
        "allow_headers": [
            "Content-Type",
            "Authorization",
            "X-CSRF-TOKEN",
            "X-CSRF-STATE",
            "X-Device-Fingerprint"
        ],
        "expose_headers": ["X-CSRF-TOKEN", "X-CSRF-STATE"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        "vary_header": True,
        "max_age": 600
    }

    CORS(app, **cors_options)

    @app.after_request
    def after_request(response):
        # Логирование CORS запросов для отладки
        origin = request.headers.get('Origin')
        if origin and app.debug:
            app.logger.debug(f"CORS request from: {origin}")
            app.logger.debug(f"CORS headers in response: {response.headers.get('Access-Control-Allow-Origin', None)}")

        return response

    return app

def create_app(config_name=None):
    """Factory function to create and configure Flask application"""
    app = Flask(__name__)

    # Load configuration
    config_name = config_name or os.environ.get('FLASK_ENV', 'default')
    app.config.from_object(get_config())

    # Configure logging
    logger = configure_logging(app)
    logger.debug(f"Server time: {datetime.datetime.now().isoformat()}")

    # Configure CORS
    configure_cors(app)

    # Initialize authentication
    init_auth(app)

    # Apply enhanced security middleware (new)
    apply_security_middleware(app)

    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/api')
    app.register_blueprint(admin_bp, url_prefix='/api')
    app.register_blueprint(posts_bp, url_prefix='/api')
    app.register_blueprint(images_bp, url_prefix='/api')
    app.register_blueprint(user_bp, url_prefix='/api')

    # Configure database connection handling
    @app.teardown_appcontext
    def close_connection(exception):
        db = getattr(g, '_database', None)
        if db is not None:
            db.close()

    # Initialize database if needed
    with app.app_context():
        setup_database(app)

    # Schedule cleanup tasks (replacing @app.before_first_request)
    @app.route('/api/_internal/trigger-cleanup', methods=['POST'])
    def trigger_cleanup():
        # Only allow this endpoint to be called locally
        if request.remote_addr != '127.0.0.1':
            return jsonify({"error": "Unauthorized"}), 403
        cleanup_task()
        return jsonify({"status": "cleanup completed"})

    # Setup background task
    def cleanup_task():
        with app.app_context():
            try:
                # Clean up expired tokens
                from backend.models.token_blacklist import TokenBlacklist
                TokenBlacklist.clear_expired_tokens()

                # Clean up expired sessions
                from backend.models.session import SessionManager
                SessionManager.clear_expired()

                app.logger.info("Security cleanup completed successfully")
            except Exception as e:
                app.logger.error(f"Error during security cleanup: {e}")

    # Start the background scheduler
    if not app.debug or os.environ.get('FLASK_RUN_FROM_CLI') != 'true':
        import threading
        import time

        def run_scheduler():
            while True:
                # Run cleanup
                cleanup_task()
                # Sleep for 1 hour
                time.sleep(3600)

        # Start scheduler in a background thread
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()

    return app



def init_db(app):
    """Initialize the database schema"""
    with app.app_context():
        db = get_db()
        schema = app.config['SCHEMA_PATH']
        with app.open_resource(schema, mode='r', encoding='utf-8') as f:
            db.cursor().executescript(f.read())
        db.commit()


def setup_database(app):
    """Create database tables if they don't exist"""
    if not os.path.exists(app.config['DATABASE_PATH']):
        init_db(app)


# Create the Flask application
app = create_app()

if __name__ == '__main__':
    app.run(debug=app.config['DEBUG'])