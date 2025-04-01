# backend/routes/auth.py
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import JWTManager, create_access_token, create_refresh_token, jwt_required, get_jwt_identity, \
    get_jwt
import datetime

from backend.models import User
from backend.services.auth_service import validate_login_credentials

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


# Маршрут для авторизации
@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()

    # Используем сервис для проверки учетных данных
    authentication_result = validate_login_credentials(data['username'], data['password'])
    if not authentication_result['success']:
        return jsonify({"msg": authentication_result['message']}), 401

    user = authentication_result['user']
    user_id_str = str(user['id'])

    # Проверка блокировки пользователя
    if User.is_user_blocked(user['id']):
        return jsonify({"msg": "Ваш аккаунт заблокирован администратором"}), 403

    # Get user's token lifetime setting
    token_lifetime = User.get_token_lifetime(user['id'])

    # Create tokens
    access_token = create_access_token(
        identity=user_id_str,
        expires_delta=datetime.timedelta(seconds=token_lifetime)
    )
    refresh_token = create_refresh_token(identity=user_id_str)

    return jsonify(
        access_token=access_token,
        refresh_token=refresh_token,
        token_lifetime=token_lifetime
    ), 200


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
@jwt_required()  # Вместо jwt_required(refresh=True)
def refresh():
    # Получить claims из текущего токена
    current_token = get_jwt()

    # Проверить, что это refresh токен
    if current_token.get('token_type') != 'refresh':
        return jsonify({"msg": "Требуется refresh token"}), 401

    current_user_id = get_jwt_identity()
    # Convert to int for database lookup
    user_id = int(current_user_id)

    # Get user's token lifetime setting
    token_lifetime = User.get_token_lifetime(user_id)

    # Create new access token
    access_token = create_access_token(
        identity=current_user_id,
        expires_delta=datetime.timedelta(seconds=token_lifetime)
    )

    return jsonify(access_token=access_token, token_lifetime=token_lifetime), 200


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
        expires_delta=datetime.timedelta(seconds=token_lifetime)
    )

    refresh_token = create_refresh_token(
        identity=current_user_id,
        expires_delta=datetime.timedelta(seconds=refresh_token_lifetime)
    )

    return jsonify({
        "msg": "Настройки успешно обновлены",
        "token_lifetime": token_lifetime,
        "refresh_token_lifetime": refresh_token_lifetime,
        "access_token": access_token,
        "refresh_token": refresh_token
    }), 200


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