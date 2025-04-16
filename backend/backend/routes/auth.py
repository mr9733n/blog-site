# backend/routes/auth.py
import time
import uuid
import secrets
import hashlib

from flask import Blueprint, request, jsonify, current_app, make_response
from flask_jwt_extended import JWTManager, create_access_token, create_refresh_token, jwt_required, get_jwt_identity, \
    get_jwt, set_access_cookies, set_refresh_cookies, unset_jwt_cookies
from datetime import datetime, timedelta, timezone

from backend.models import User
from backend.services.auth_service import validate_login_credentials
from backend.models.token_blacklist import TokenBlacklist
from backend.models.session import SessionManager  # New import
from backend.models.security import SecurityMonitor  # New import
from backend.models.base import query_db

auth_bp = Blueprint('auth', __name__)


# Функция для настройки JWT обработчиков теперь перемещена в auth/jwt_handlers.py
# Маршрут для авторизации
@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()

    # Get device fingerprint from header
    device_fingerprint = request.headers.get('X-Device-Fingerprint')
    if device_fingerprint:
        current_app.logger.debug(f"Login with device fingerprint: {device_fingerprint[:8]}...")

    # Используем сервис для проверки учетных данных
    authentication_result = validate_login_credentials(data['username'], data['password'])
    if not authentication_result['success']:
        return jsonify({"msg": authentication_result['message']}), 401

    user = authentication_result['user']
    user_id = user['id']

    # Debug logging
    current_app.logger.debug(f"User ID type: {type(user_id)}, value: {user_id}")

    # Explicitly convert to string
    user_id_str = str(user_id)
    current_app.logger.debug(f"User ID string type: {type(user_id_str)}, value: {user_id_str}")

    # Проверка блокировки пользователя
    if User.is_user_blocked(user_id):
        return jsonify({"msg": "Ваш аккаунт заблокирован администратором"}), 403

    # Get user's token lifetime settings using helper methods
    token_lifetime = User.get_token_lifetime(user_id)
    refresh_token_lifetime = User.get_refresh_token_lifetime(user_id)
    session_key = secrets.token_hex(16)
    csrf_state = secrets.token_hex(16)
    session_state = "active"

    # Debug logging
    current_app.logger.debug(
        f"Login using token_lifetime: {token_lifetime}, refresh_token_lifetime: {refresh_token_lifetime}")

    # Create a fingerprint hash for JWT claims if available
    fp_hash = None
    if device_fingerprint:
        # Create a hash of the fingerprint to include in the token
        fp_hash = hashlib.sha256(device_fingerprint.encode()).hexdigest()

    # Get client IP info for the token
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if client_ip and ',' in client_ip:
        # If multiple IPs in X-Forwarded-For, take the first one (client IP)
        client_ip = client_ip.split(',')[0].strip()

    # Generate IP network hash for the token
    ip_network_hash = None
    if client_ip:
        ip_network_hash = SecurityMonitor.get_ip_network_hash(client_ip)

    additional_claims = {
        'jti': str(uuid.uuid4()),
        'session_key': session_key,
        'fp_hash': fp_hash,  # Add fingerprint hash as claim
        'ip_net': ip_network_hash,  # Add IP network hash as claim
        'ua_hash': hashlib.sha256(request.headers.get('User-Agent', '').encode()).hexdigest()[:16]  # User agent hash
    }

    # Create tokens with the enhanced claims
    access_token = create_access_token(
        identity=user_id_str,
        expires_delta=timedelta(seconds=token_lifetime),
        additional_claims=additional_claims
    )

    refresh_token = create_refresh_token(
        identity=user_id_str,
        expires_delta=timedelta(seconds=refresh_token_lifetime),
        additional_claims=additional_claims
    )

    # Store session with device fingerprint - CHANGED FROM TokenBlacklist to SessionManager
    SessionManager.store_session(
        user_id,
        session_key,
        csrf_state,
        session_state,
        (datetime.now(timezone.utc) + timedelta(seconds=refresh_token_lifetime)).isoformat(),
        device_fingerprint
    )

    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if client_ip and ',' in client_ip:
        # If multiple IPs in X-Forwarded-For, take the first one (client IP)
        client_ip = client_ip.split(',')[0].strip()

    _, network_changed = SecurityMonitor.check_network_change(session_key, client_ip)

    # Create response with user data and token lifetimes
    resp = jsonify({
        "user": {
            "id": user_id,
            "username": user.get('username')
        },
        "token_lifetime": token_lifetime,
        "refresh_token_lifetime": refresh_token_lifetime
    })

    # Set cookies
    set_access_cookies(resp, access_token)
    set_refresh_cookies(resp, refresh_token)

    resp.set_cookie(
        'csrf_state',
        csrf_state,
        max_age=refresh_token_lifetime,
        secure=current_app.config['JWT_COOKIE_SECURE'],
        httponly=False,  # Доступно для JavaScript
        samesite=current_app.config['JWT_COOKIE_SAMESITE']
    )

    return resp, 200


# Маршрут для регистрации
@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()

    try:
        User.create(data['username'], data['email'], data['password'])
        return jsonify({"msg": "Пользователь успешно зарегистрирован"}), 201
    except ValueError as e:
        return jsonify({"msg": str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Ошибка регистрации: {str(e)}")
        return jsonify({"msg": "Произошла ошибка при регистрации"}), 500


# Маршрут для обновления токена
@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    current_token = get_jwt()
    jti = current_token.get('jti')
    user_id = int(get_jwt_identity())
    session_state = "active"

    # Get device fingerprint from request
    device_fingerprint = request.headers.get('X-Device-Fingerprint')

    # Get client IP and User-Agent for verification
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if client_ip and ',' in client_ip:
        client_ip = client_ip.split(',')[0].strip()

    user_agent = request.headers.get('User-Agent', '')

    # Get claims from the current token for validation
    token_fp_hash = current_token.get('fp_hash')
    token_ip_net = current_token.get('ip_net')
    token_ua_hash = current_token.get('ua_hash')

    # Validate device binding if claims exist (tokens created after upgrade)
    if token_fp_hash and device_fingerprint:
        current_fp_hash = hashlib.sha256(device_fingerprint.encode()).hexdigest()
        if token_fp_hash != current_fp_hash:
            current_app.logger.warning(f"Refresh rejected: device fingerprint mismatch for user {user_id}")
            return jsonify({"msg": "Недействительный токен обновления - несоответствие устройства"}), 403

    # Blacklist the current refresh token immediately
    TokenBlacklist.blacklist_token(jti, user_id, current_token.get('exp'))

    # Get token lifetimes
    token_lifetime = User.get_token_lifetime(user_id)
    refresh_token_lifetime = User.get_refresh_token_lifetime(user_id)

    current_app.logger.debug(
        f"Refresh using token_lifetime: {token_lifetime}, refresh_token_lifetime: {refresh_token_lifetime}")

    # Get session info and validate
    session_key = current_token.get('session_key')

    # Используем тот же session_key вместо создания нового,
    # чтобы избежать создания новой сессии при каждом обновлении токена
    new_session_key = session_key

    csrf_state = f"{secrets.token_hex(16)}:{int(time.time())}"  # Add timestamp

    # Validate session
    if not session_key or not SessionManager.check_session_valid(session_key):
        return jsonify({"msg": "Недействительный токен обновления"}), 401

    # Verify device fingerprint matches the saved one
    if device_fingerprint and not SessionManager.validate_fingerprint(session_key, device_fingerprint):
        current_app.logger.warning(f"Fingerprint mismatch during refresh for user {user_id}")
        return jsonify({"msg": "Недействительный токен обновления - несоответствие устройства"}), 403

    # Prepare new claims for the tokens
    # Create a fingerprint hash for JWT claims if available
    fp_hash = None
    if device_fingerprint:
        # Create a hash of the fingerprint to include in the token
        fp_hash = hashlib.sha256(device_fingerprint.encode()).hexdigest()

    # Generate IP network hash for the token
    ip_network_hash = None
    if client_ip:
        ip_network_hash = SecurityMonitor.get_ip_network_hash(client_ip)

    # Generate User-Agent hash
    ua_hash = hashlib.sha256(user_agent.encode()).hexdigest()[:16]

    # Create tokens with device-binding claims
    additional_claims = {
        'jti': str(uuid.uuid4()),
        'session_key': new_session_key,
        'fp_hash': fp_hash,
        'ip_net': ip_network_hash,
        'ua_hash': ua_hash,
        'created_at': int(time.time())  # Add creation timestamp
    }

    # Create new access token with enhanced claims
    access_token = create_access_token(
        identity=str(user_id),
        expires_delta=timedelta(seconds=token_lifetime),
        additional_claims=additional_claims
    )

    # Create new refresh token with the same claims
    new_refresh_token = create_refresh_token(
        identity=str(user_id),
        expires_delta=timedelta(seconds=refresh_token_lifetime),
        additional_claims=additional_claims
    )

    # Update session with new CSRF state but keep the same session key
    SessionManager.update_session(
        session_key,
        None,  # Не меняем session_key
        csrf_state,
        session_state,
        device_fingerprint
    )

    # Further security checks...
    SecurityMonitor.track_request_counter(session_key)
    SecurityMonitor.track_activity_pattern(session_key)

    # Get user info for response
    user = User.get_by_id(user_id)
    user_dict = dict(user) if user else {}

    # Create response
    resp = jsonify({
        "user": {
            "id": user_id,
            "username": user_dict.get('username', '')
        },
        "token_lifetime": token_lifetime,
        "refresh_token_lifetime": refresh_token_lifetime
    })

    # Set cookies with new tokens
    set_access_cookies(resp, access_token)
    set_refresh_cookies(resp, new_refresh_token)  # Set the new refresh token

    # Set new CSRF state with timestamp
    resp.set_cookie(
        'csrf_state',
        csrf_state,
        max_age=refresh_token_lifetime,
        secure=current_app.config['JWT_COOKIE_SECURE'],
        httponly=False,  # Must be accessible by JavaScript
        samesite=current_app.config['JWT_COOKIE_SAMESITE']
    )

    return resp


# Маршрут для обновления настроек токена
@auth_bp.route('/settings/token-settings', methods=['PUT'])
@jwt_required()
def update_token_settings():
    current_user_id = get_jwt_identity()
    user_id = int(current_user_id)

    data = request.get_json()
    token_lifetime = data.get('token_lifetime')
    refresh_token_lifetime = data.get('refresh_token_lifetime')

    # Валидация входных данных
    if not token_lifetime or not isinstance(token_lifetime, int) or token_lifetime < 300 or token_lifetime > 86400:
        return jsonify({"msg": "Недопустимое значение времени жизни токена. Должно быть от 5 минут до 24 часов."}), 400

    if not refresh_token_lifetime or not isinstance(refresh_token_lifetime,
                                                    int) or refresh_token_lifetime < 86400 or refresh_token_lifetime > 2592000:
        return jsonify({"msg": "Недопустимое значение времени жизни refresh токена. Должно быть от 1 до 30 дней."}), 400

    # Обновление настроек в базе данных
    User.update_token_settings(user_id, token_lifetime, refresh_token_lifetime)

    # Создаем новые токены с обновленными настройками
    access_token = create_access_token(
        identity=current_user_id,
        expires_delta=timedelta(seconds=token_lifetime)
    )

    refresh_token = create_refresh_token(
        identity=current_user_id,
        expires_delta=timedelta(seconds=refresh_token_lifetime)
    )

    # Create response
    resp = jsonify({
        "msg": "Настройки успешно обновлены",
        "token_lifetime": token_lifetime,
        "refresh_token_lifetime": refresh_token_lifetime
    })

    # Set cookies with new tokens
    set_access_cookies(resp, access_token)
    set_refresh_cookies(resp, refresh_token)

    return resp


# Маршрут для получения информации о текущем пользователе
@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    current_user_id = get_jwt_identity()
    # Convert string ID back to integer
    current_user_id = int(current_user_id)
    user = User.get_by_id(current_user_id)

    if not user:
        return jsonify({"msg": "Пользователь не найден"}), 404

    # Не возвращаем хеш пароля
    user_data = dict(user)
    user_data.pop('password', None)

    return jsonify(user_data)


@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    current_user_id = get_jwt_identity()
    user_id = int(current_user_id)

    # Get device fingerprint from request
    device_fingerprint = request.headers.get('X-Device-Fingerprint')

    # Получаем текущий токен
    current_token = get_jwt()
    jti = current_token.get('jti')
    session_key = current_token.get('session_key')

    # Optional fingerprint validation - we should still allow logout even if fingerprint doesn't match
    # This just logs a warning if something suspicious happens - CHANGED: Use SessionManager
    if session_key and device_fingerprint and not SessionManager.validate_fingerprint(session_key, device_fingerprint):
        current_app.logger.warning(f"Suspicious logout: fingerprint mismatch for user {user_id}")

    # Delete the session and blacklist token regardless of fingerprint
    if session_key:
        # CHANGED: Use SessionManager
        SessionManager.delete_session(session_key)

    # Добавляем токен в черный список
    TokenBlacklist.blacklist_token(jti, user_id, current_token.get('exp'))

    # Create response
    resp = jsonify({"msg": "Вы успешно вышли из системы"})

    # Clear all JWT cookies
    unset_jwt_cookies(resp)

    return resp

@auth_bp.route('/token-info', methods=['GET'])
def token_info():
    """Endpoint for debugging token information"""
    # Collect information about cookies
    cookies = {}
    for name, value in request.cookies.items():
        # Mask sensitive values
        if 'token' in name.lower():
            cookies[name] = f"{value[:8]}..." if value else None
        else:
            cookies[name] = value

    # Collect information about CSRF tokens
    csrf_info = {
        'csrf_access_cookie': request.cookies.get('csrf_access_token', None),
        'csrf_refresh_cookie': request.cookies.get('csrf_refresh_token', None),
        'csrf_state_cookie': request.cookies.get('csrf_state', None),
        'csrf_header': request.headers.get('X-CSRF-TOKEN', None),
        'csrf_state_header': request.headers.get('X-CSRF-STATE', None),
    }

    # Collect request headers
    headers = {}
    for name, value in request.headers.items():
        # Skip sensitive headers
        if name.lower() in ['cookie', 'authorization']:
            continue
        headers[name] = value

    response_data = {
        'message': 'Token debug information',
        'cookies': cookies,
        'csrf_info': csrf_info,
        'request_headers': headers,
        'server_time': datetime.now(timezone.utc).isoformat()
    }

    # Add authentication status
    try:
        # Try to verify JWT without cookie/header errors
        jwt_data = get_jwt()
        response_data['authenticated'] = True
        response_data['jwt_info'] = {
            'user_id': jwt_data.get('sub'),
            'jti': jwt_data.get('jti'),
            'session_key': jwt_data.get('session_key', None)[:8] + '...' if jwt_data.get('session_key') else None,
            'exp': datetime.fromtimestamp(jwt_data.get('exp')).isoformat() if jwt_data.get('exp') else None
        }
    except Exception as e:
        response_data['authenticated'] = False
        response_data['auth_error'] = str(e)

    return jsonify(response_data)