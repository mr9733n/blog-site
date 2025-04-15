# backend/app.py
import os
import sqlite3
import logging
import datetime
import sys
from flask import Flask, g
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

    return logger


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
    if os.environ.get('FLASK_ENV') == 'production':
        CORS(app, resources={r"/api/*": {"origins": app.config['CORS_ORIGINS_PROD']}},
             supports_credentials=True)
    else:
        CORS(app, resources={r"/api/*": {"origins": app.config['CORS_ORIGINS_DEV']}},
             supports_credentials=True)

    # Initialize authentication
    init_auth(app)

    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/api')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    app.register_blueprint(posts_bp, url_prefix='/api')
    app.register_blueprint(images_bp, url_prefix='/api')
    app.register_blueprint(user_bp, url_prefix='/api/user')

    # Configure database connection handling
    @app.teardown_appcontext
    def close_connection(exception):
        db = getattr(g, '_database', None)
        if db is not None:
            db.close()

    # Initialize database if needed
    with app.app_context():
        setup_database(app)

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