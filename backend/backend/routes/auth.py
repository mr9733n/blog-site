# backend/routes/auth.py
import uuid

from flask import Blueprint, request, jsonify, current_app, make_response
from flask_jwt_extended import JWTManager, create_access_token, create_refresh_token, jwt_required, get_jwt_identity, \
    get_jwt, set_access_cookies, set_refresh_cookies, unset_jwt_cookies
from datetime import datetime, timedelta, timezone

from backend.models import User
from backend.services.auth_service import validate_login_credentials
from backend.models.token_blacklist import TokenBlacklist
from backend.models.base import query_db

auth_bp = Blueprint('auth', __name__)


# Функция для настройки JWT обработчиков
def jwt_handlers(jwt):
    @jwt.invalid_token_loader
    def invalid_token_callback(error_string):
        current_app.logger.error(f"DEBUG: Invalid token error: {error_string}")
        return jsonify({"msg": f"Invalid token: {error_string}"}), 422

    @jwt.unauthorized_loader
    def unauthorized_callback(error_string):
        current_app.logger.error(f"DEBUG: Unauthorized error: {error_string}")
        return jsonify({"msg": f"Unauthorized: {error_string}"}), 401

    @jwt.token_in_blocklist_loader
    def check_if_token_is_revoked(jwt_header, jwt_payload):
        jti = jwt_payload.get('jti')
        return TokenBlacklist.is_token_blacklisted(jti)


# Маршрут для авторизации
@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()

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

    # Debug logging
    current_app.logger.debug(f"Login using token_lifetime: {token_lifetime}, refresh_token_lifetime: {refresh_token_lifetime}")

    # Create tokens
    access_token = create_access_token(
        identity=user_id_str,  # Explicitly as string
        expires_delta=timedelta(seconds=token_lifetime),
        additional_claims={'jti': str(uuid.uuid4())}
    )
    refresh_token = create_refresh_token(
        identity=user_id_str,  # Also ensure this is a string
        expires_delta=timedelta(seconds=refresh_token_lifetime)
    )

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

    # Блокируем refresh токен
    TokenBlacklist.blacklist_token(jti, user_id, current_token.get('exp'))

    # Получаем сроки жизни токенов через вспомогательные методы
    token_lifetime = User.get_token_lifetime(user_id)
    refresh_token_lifetime = User.get_refresh_token_lifetime(user_id)

    # Debug logging
    current_app.logger.debug(
        f"Refresh using token_lifetime: {token_lifetime}, refresh_token_lifetime: {refresh_token_lifetime}")

    # Создаем новый access токен
    access_token = create_access_token(
        identity=str(user_id),
        expires_delta=timedelta(seconds=token_lifetime),
        additional_claims={'jti': str(uuid.uuid4())}
    )

    # Get user info for response
    user = User.get_by_id(user_id)

    # Convert sqlite3.Row to dict before accessing with get()
    user_dict = dict(user) if user else {}

    # Create response with token lifetimes
    resp = jsonify({
        "user": {
            "id": user_id,
            "username": user_dict.get('username', '')
        },
        "token_lifetime": token_lifetime,
        "refresh_token_lifetime": refresh_token_lifetime
    })

    # Set cookie with new access token
    set_access_cookies(resp, access_token)

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

    # Получаем текущий токен
    current_token = get_jwt()
    jti = current_token.get('jti')

    # Добавляем токен в черный список
    TokenBlacklist.blacklist_token(jti, user_id, current_token.get('exp'))

    # Create response
    resp = jsonify({"msg": "Вы успешно вышли из системы"})

    # Clear all JWT cookies
    unset_jwt_cookies(resp)

    return resp