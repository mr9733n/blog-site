import hashlib
import os
import secrets
import sqlite3
import logging
import datetime
import json
import sys
import time

from flask import Flask, request, jsonify, g, make_response
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
    TokenBlacklist.clear_expired_sessions()

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

@app.before_request
def check_csrf():
    if request.method in ['POST', 'PUT', 'DELETE', 'PATCH'] and not request.path.endswith('/login'):
        csrf_from_cookie = request.cookies.get('csrf_state')
        csrf_from_header = request.headers.get('X-CSRF-STATE')

        if not csrf_from_cookie or not csrf_from_header or csrf_from_cookie != csrf_from_header:
            return jsonify({"msg": "CSRF-защита обнаружила проблему"}), 403


@app.before_request
def rotate_csrf_on_interval():
    """Rotate CSRF tokens every few minutes for security"""
    if request.path.startswith('/api/') and request.method in ['GET']:
        try:
            csrf_state = request.cookies.get('csrf_state')
            if not csrf_state:
                return

            # Check if we need to rotate based on timestamp in token
            rotate = False
            try:
                # If the csrf_state follows format "token:timestamp"
                if ':' in csrf_state:
                    token_parts = csrf_state.split(':')
                    if len(token_parts) == 2:
                        timestamp = int(token_parts[1])
                        if time.time() - timestamp > 300:  # 5 minutes
                            rotate = True
            except:
                # If we can't parse, default to not rotating
                pass

            if rotate:
                # Get current user and session if available
                jwt_data = get_jwt()
                session_key = jwt_data.get('session_key')

                if session_key:
                    # Generate new CSRF state with timestamp
                    new_csrf_state = f"{secrets.token_hex(16)}:{int(time.time())}"

                    # Update in database
                    TokenBlacklist.update_session_keys(session_key=session_key, csrf_state=new_csrf_state)

                    # Set the new cookie (will be in response)
                    token_lifetime = app.config['JWT_ACCESS_TOKEN_EXPIRES']
                    response = make_response()
                    response.set_cookie(
                        'csrf_state',
                        new_csrf_state,
                        max_age=token_lifetime,
                        secure=app.config['JWT_COOKIE_SECURE'],
                        httponly=False,
                        samesite=app.config['JWT_COOKIE_SAMESITE']
                    )
                    return response
        except:
            # Continue with the request if rotation fails
            pass

@app.before_request
def detect_ip_anomalies():
    """Detect major IP changes without storing actual IPs"""
    if request.path.startswith('/api/') and request.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
        try:
            # Get JWT data
            jwt_data = get_jwt()
            session_key = jwt_data.get('session_key')

            if not session_key:
                return

            # Get client IP
            client_ip = request.remote_addr

            # Instead of storing IP, store network class hash
            ip_class_hash = None
            if '.' in client_ip:  # IPv4
                # Get first two octets (network class)
                parts = client_ip.split('.')
                if len(parts) >= 2:
                    network_class = f"{parts[0]}.{parts[1]}"
                    ip_class_hash = hashlib.sha256(network_class.encode()).hexdigest()
            elif ':' in client_ip:  # IPv6
                # Get first 4 components of IPv6
                parts = client_ip.split(':')
                if len(parts) >= 4:
                    network_class = ':'.join(parts[:4])
                    ip_class_hash = hashlib.sha256(network_class.encode()).hexdigest()

            if not ip_class_hash:
                return

            # Check if our table has ip_network_hash column
            stored_hash = TokenBlacklist.validate_ip_anomalies(session_key, ip_class_hash)

            # If hash different, log warning and require additional verification for sensitive operations
            if stored_hash != ip_class_hash:
                app.logger.warning(f"Network class change detected for session {session_key[:8]}")
                # Store this fact in g for use by other middleware
                g.network_class_changed = True

                # For sensitive operations, check if extra verification is required
                sensitive_paths = ['/api/user/update', '/api/settings/token-settings']
                if any(request.path.startswith(path) for path in sensitive_paths):
                    # Require additional verification (can be implemented as needed)
                    # This example just forces re-authentication
                    return jsonify({
                        "msg": "Для этой операции требуется повторная аутентификация из соображений безопасности",
                        "code": "REVERIFY_REQUIRED"
                    }), 428
        except:
            # Continue with the request if detection fails
            pass


@app.before_request
def analyze_token_usage_patterns():
    """Analyze token usage patterns for anomalies"""
    if request.path.startswith('/api/') and request.method != 'OPTIONS':
        try:
            # Get JWT data
            jwt_data = get_jwt()
            session_key = jwt_data.get('session_key')

            if not session_key:
                return

            # Check if our tables have required columns
            suspicious = TokenBlacklist.validate_token_usage_patterns(session_key)

            # For sensitive operations, add extra checks on suspicious patterns
            if suspicious:
                # Store fact in g for other middleware
                g.suspicious_activity_pattern = True

                # For sensitive operations, require reverification
                sensitive_paths = ['/api/user/update', '/api/admin']
                if any(request.path.startswith(path) for path in sensitive_paths):
                    return jsonify({
                        "msg": "Обнаружена необычная активность. Для продолжения требуется повторная аутентификация",
                        "code": "SUSPICIOUS_ACTIVITY"
                    }), 428
        except:
            # Continue with the request if analysis fails
            pass

@app.before_request
def update_last_activity():
    if request.path.startswith('/api/') and hasattr(g, 'user_id') and g.user_id:
        TokenBlacklist.update_session_activity(g.user_id)


@app.before_request
def check_extra_security():
    # Only check for sensitive operations (write operations)
    if request.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
        # Paths that modify sensitive user data
        sensitive_paths = [
            '/api/user/update',
            '/api/settings/token-settings',
            '/api/admin/users',
        ]

        # Check if the current path is sensitive
        is_sensitive = False
        for path in sensitive_paths:
            if request.path.startswith(path):
                is_sensitive = True
                break

        # For sensitive paths, enforce fingerprint validation
        if is_sensitive:
            # Get JWT data if available
            try:
                jwt_data = get_jwt()
                session_key = jwt_data.get('session_key')

                # Get device fingerprint
                device_fingerprint = request.headers.get('X-Device-Fingerprint')

                # If both are present, validate fingerprint match
                if session_key and device_fingerprint:
                    fingerprint_match = TokenBlacklist.validate_session_fingerprint(session_key, device_fingerprint)

                    if not fingerprint_match:
                        logger.warning(f"Sensitive operation blocked: fingerprint mismatch on {request.path}")
                        return jsonify({
                            "msg": "Операция заблокирована из соображений безопасности. Пожалуйста, повторите вход в систему."
                        }), 403
            except:
                # If we can't get JWT data, continue to regular auth checks
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
                # Если не удалось получить JWT данные, игнорируем tokenRefreshLoading
                pass
    except Exception as e:
        # В случае ошибки логируем, но не прерываем работу
        app.logger.debug(f"Could not add CSRF token to response: {str(e)}")
    return response


@jwt.token_in_blocklist_loader
def check_if_token_is_revoked(jwt_header, jwt_payload):
    jti = jwt_payload.get('jti')
    session_key = jwt_payload.get('session_key')
    user_id = jwt_payload.get('sub')  # Get user_id directly from payload

    # Get current device fingerprint from request
    device_fingerprint = request.headers.get('X-Device-Fingerprint')

    try:
        # Call the TokenBlacklist method with the user_id from the payload
        is_blacklisted = TokenBlacklist.is_token_blacklisted(jti, user_id)
        session_invalid = session_key and not TokenBlacklist.validate_session_key(session_key)
        session_state = session_key and not TokenBlacklist.validate_session(session_key, user_id)
        session_activity = session_key and not TokenBlacklist.validate_session_activity(session_key)

        # Check fingerprint match
        fingerprint_mismatch = False
        if session_key and device_fingerprint:
            fingerprint_match = TokenBlacklist.validate_session_fingerprint(session_key, device_fingerprint)
            fingerprint_mismatch = not fingerprint_match
            if fingerprint_mismatch:
                logger.warning(f"🔍 Device fingerprint mismatch for user {user_id}")

        if is_blacklisted:
            logger.warning(f"🔒 Заблокированный токен с jti={jti} попытался использоваться")
        if session_invalid:
            logger.warning(f"🔑 Недействительный ключ сессии: {session_key}")
        if session_state:
            logger.warning(f"⚠️ Неактивная сессия: {session_state}")
        if session_activity:
            logger.warning(f"⏰ Session expired: {session_activity}")

        # Reject token if any check fails
        return is_blacklisted or session_invalid or session_state or session_activity or fingerprint_mismatch
    except Exception as e:
        logger.error(f"Error checking token validity: {e}")
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