# backend/routes/user.py
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt

from backend.models import User
from backend.models.token_blacklist import TokenBlacklist
from backend.models.session import SessionManager  # New import
from backend.models.security import SecurityMonitor  # New import
from backend.services.security_validator import SecurityValidator

user_bp = Blueprint('user', __name__, url_prefix='/user')


@user_bp.route('/update', methods=['PUT'])
@jwt_required()
def update_user_profile():
    # Use centralized security validator for sensitive operations
    is_valid, error_response = SecurityValidator.validate_sensitive_operation()

    if not is_valid:
        return error_response

    current_user_id = get_jwt_identity()
    user_id = int(current_user_id)

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
            # If password was changed, invalidate all existing sessions for security
            if password:
                TokenBlacklist.blacklist_user_tokens(user_id)
                current_app.logger.info(f"All sessions invalidated for user {user_id} due to password change")

            return jsonify({"msg": "Данные пользователя успешно обновлены"})
        else:
            return jsonify({"msg": "Нет данных для обновления"}), 400
    except ValueError as e:
        return jsonify({"msg": str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Ошибка обновления данных пользователя: {str(e)}")
        return jsonify({"msg": "Произошла ошибка при обновлении данных пользователя"}), 500