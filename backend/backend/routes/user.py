# backend/routes/user.py
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt

from backend.models import User
from backend.models.token_blacklist import TokenBlacklist

user_bp = Blueprint('user', __name__)


@user_bp.route('/update', methods=['PUT'])
@jwt_required()
def update_user_profile():
    current_user_id = get_jwt_identity()
    user_id = int(current_user_id)

    # Get current token for session validation
    current_token = get_jwt()
    session_key = current_token.get('session_key')

    # Validate session key for extra security
    if session_key and not TokenBlacklist.validate_session_key(session_key):
        return jsonify({"msg": "Недействительная сессия"}), 401

    # Additional check: validate the session belongs to this user
    if session_key and not TokenBlacklist.validate_session(session_key, user_id):
        return jsonify({"msg": "Сессия не принадлежит текущему пользователю"}), 403

    try:
        data = request.get_json()
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        current_password = data.get('currentPassword')

        # Get user data from database
        user = User.get_by_id(user_id)
        if not user:
            return jsonify({"msg": "Пользователь не найден"}), 404

        # Verify current password for sensitive changes
        if username != user['username'] or email != user['email'] or password:
            if not current_password:
                return jsonify({"msg": "Для изменения профиля необходимо ввести текущий пароль"}), 400

            # Verify the current password
            if not User.verify_password(user['username'], current_password):
                return jsonify({"msg": "Неверный текущий пароль"}), 400

        # Update user data using existing model method
        result = User.update_user(user_id, username, email, password)

        if result:
            return jsonify({"msg": "Данные пользователя успешно обновлены"})
        else:
            return jsonify({"msg": "Нет данных для обновления"}), 400
    except ValueError as e:
        return jsonify({"msg": str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Ошибка обновления данных пользователя: {str(e)}")
        return jsonify({"msg": "Произошла ошибка при обновлении данных пользователя"}), 500