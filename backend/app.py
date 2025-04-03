import os
import sqlite3
import logging
import datetime
import json
import sys

from flask import Flask, request, jsonify, g
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from dotenv import load_dotenv
from jwt import decode

from backend.config import get_config
from backend.models.user import User
from backend.models.base import get_db
from backend.models.token_blacklist import TokenBlacklist
from backend.routes.admin import admin_bp
from backend.routes.posts import posts_bp
from backend.routes.images import images_bp
from backend.routes.auth import auth_bp, jwt_handlers

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
load_dotenv()

def configure_logging(app):
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

app = Flask(__name__)
app.config.from_object(get_config())
logger = configure_logging(app)

logging.debug(f"Server time: {datetime.datetime.now().isoformat()}")
logging.debug(f"JWT_SECRET_KEY: {app.config['JWT_SECRET_KEY']}")

# Настройка CORS на основе окружения
if os.environ.get('FLASK_ENV') == 'production':
    CORS(app, resources={r"/api/*": {"origins": app.config['CORS_ORIGINS_PROD']}})
else:
    CORS(app, resources={r"/api/*": {"origins": app.config['CORS_ORIGINS_DEV']}})

# Настройка JWT
jwt = JWTManager(app)

# Регистрация обработчиков JWT
jwt_handlers(jwt)

# In app.py
app.config['JWT_IDENTITY_CLAIM'] = 'sub'  # Ensure this is 'sub' (default)

# Закрытие соединения с БД после обработки запроса
@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# Инициализация базы данных
def init_db():
    with app.app_context():
        db = g._database = sqlite3.connect(app.config['DATABASE_PATH'])
        schema = app.config['SCHEMA_PATH']
        with app.open_resource(schema, mode='r', encoding='utf-8') as f:
            db.cursor().executescript(f.read())
        db.commit()

# Создание таблиц если их нет
def setup():
    with app.app_context():
        if not os.path.exists(app.config['DATABASE_PATH']):
            init_db()

# Регистрация функции инициализации БД
with app.app_context():
    # Запускаем функцию setup() при старте приложения
    setup()
    TokenBlacklist.clear_expired_tokens()

@app.before_request
def log_request_info():
    if 'Authorization' in request.headers:
        logger.debug(f"DEBUG: Auth header received: {request.headers['Authorization'][:20]}...")
    else:
        logger.warning("DEBUG: No Authorization header in request")
        logger.debug(f"DEBUG: Available headers: {list(request.headers.keys())}")

# Проверка блокировки пользователя при аутентификации
@app.before_request
def check_if_user_blocked():
    # Проверяем только запросы API, которые не являются авторизацией
    if request.path.startswith('/api/') and request.path != '/api/login' and request.path != '/api/register':
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            try:
                token = auth_header.split(' ')[1]

                # Декодируем токен без проверки сигнатуры
                payload = decode(token, options={"verify_signature": False})

                user_id = payload.get('sub')

                # Проверяем, заблокирован ли пользователь
                if user_id and User.is_user_blocked(user_id):
                    return jsonify({"msg": "Ваш аккаунт заблокирован администратором"}), 403
            except Exception as e:
                # Пропускаем ошибки декодирования токена
                pass

@jwt.token_in_blocklist_loader
def check_if_token_is_revoked(jwt_header, jwt_payload):
    jti = jwt_payload.get('jti')
    is_blacklisted = TokenBlacklist.is_token_blacklisted(jti)
    if is_blacklisted:
        logger.warning(f"🔒 Заблокированный токен с jti={jti} попытался использоваться")
    return is_blacklisted

# Регистрация Blueprint-ов
app.register_blueprint(auth_bp, url_prefix='/api')
app.register_blueprint(admin_bp, url_prefix='/api/admin')
app.register_blueprint(posts_bp, url_prefix='/api')
app.register_blueprint(images_bp, url_prefix='/api')

if __name__ == '__main__':
    app.run(debug=app.config['DEBUG'])