import os
import sqlite3
import logging
import datetime
import json
import sys

from flask import Flask, request, jsonify, g
from flask_cors import CORS
from flask_jwt_extended import JWTManager, get_csrf_token, get_jwt
from dotenv import load_dotenv
from jwt import decode

from backend.config import get_config
from backend.models.user import User
from backend.models.base import get_db
from backend.models.token_blacklist import TokenBlacklist
from backend.routes.admin import admin_bp
from backend.routes.user import user_bp
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

# Configure JWT to use cookies
app.config['JWT_COOKIE_SECURE'] = os.environ.get('FLASK_ENV') == 'production'  # True in production

# Enable CORS to work with credentials
if os.environ.get('FLASK_ENV') == 'production':
    CORS(app, resources={r"/api/*": {"origins": app.config['CORS_ORIGINS_PROD']}}, supports_credentials=True)
else:
    CORS(app, resources={r"/api/*": {"origins": app.config['CORS_ORIGINS_DEV']}}, supports_credentials=True)

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
    if 'Cookie' in request.headers:
        logger.debug(f"DEBUG: Auth header received: {request.headers['Cookie'][:20]}...")
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


@app.after_request
def add_csrf_token_to_response(response):
    """Добавляет CSRF-токен в заголовок ответа"""
    try:
        # Ищем CSRF токен в куках
        csrf_token = None
        for cookie_name in ['csrf_access_token', 'csrf_refresh_token']:
            if cookie_name in request.cookies:
                csrf_token = request.cookies.get(cookie_name)
                break

        # Если нашли CSRF токен в куках, добавляем его в заголовок
        if csrf_token:
            response.headers['X-CSRF-TOKEN'] = csrf_token
        else:
            # Если не нашли в куках, пробуем получить из JWT токена
            try:
                # Получаем JWT данные текущего пользователя
                jwt_data = get_jwt()
                # Получаем CSRF из JWT данных
                if 'csrf' in jwt_data:
                    response.headers['X-CSRF-TOKEN'] = jwt_data['csrf']
            except:
                # Если не удалось получить JWT данные, игнорируемtokenRefreshLoading
                pass
    except Exception as e:
        # В случае ошибки логируем, но не прерываем работу
        app.logger.debug(f"Could not add CSRF token to response: {str(e)}")
    return response


@jwt.token_in_blocklist_loader
def check_if_token_is_revoked(jwt_header, jwt_payload):
    jti = jwt_payload.get('jti')
    user_id = jwt_payload.get('sub')  # Get user_id directly from payload

    try:
        # Call the TokenBlacklist method with the user_id from the payload
        is_blacklisted = TokenBlacklist.is_token_blacklisted(jti, user_id)
        if is_blacklisted:
            logger.warning(f"🔒 Заблокированный токен с jti={jti} попытался использоваться")
        return is_blacklisted
    except Exception as e:
        logger.error(f"Error checking token blacklist: {e}")
        # In case of error, deny token to be safe
        return True


# Регистрация Blueprint-ов
app.register_blueprint(auth_bp, url_prefix='/api')
app.register_blueprint(admin_bp, url_prefix='/api/admin')
app.register_blueprint(posts_bp, url_prefix='/api')
app.register_blueprint(images_bp, url_prefix='/api')
app.register_blueprint(user_bp, url_prefix='/api/user')


if __name__ == '__main__':
    app.run(debug=app.config['DEBUG'])