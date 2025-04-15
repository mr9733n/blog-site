# backend/routes/user.py
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt

from backend.models import User
from backend.models.token_blacklist import TokenBlacklist
from backend.models.session import SessionManager  # New import
from backend.models.security import SecurityMonitor  # New import

user_bp = Blueprint('user', __name__)


@user_bp.route('/update', methods=['PUT'])
@jwt_required()
def update_user_profile():
    current_user_id = get_jwt_identity()
    user_id = int(current_user_id)

    # Get current token for session validation
    current_token = get_jwt()
    session_key = current_token.get('session_key')

    # Get device fingerprint
    device_fingerprint = request.headers.get('X-Device-Fingerprint')

    # Validate session key for extra security - CHANGED: Use SessionManager
    if session_key and not SessionManager.check_session_valid(session_key):
        return jsonify({"msg": "Недействительная сессия"}), 401

    # Additional check: validate the session belongs to this user - CHANGED: Use SessionManager
    if session_key and not SessionManager.validate_session(session_key, user_id):
        return jsonify({"msg": "Сессия не принадлежит текущему пользователю"}), 403

    # Security check: verify device fingerprint
    if session_key and device_fingerprint and not SessionManager.validate_fingerprint(session_key, device_fingerprint):
        current_app.logger.warning(f"Profile update blocked: fingerprint mismatch for user {user_id}")
        return jsonify({"msg": "Обнаружено несоответствие устройства. Пожалуйста, войдите в систему снова."}), 403

    # Check for network changes and suspicious activity patterns
    if session_key:
        client_ip = request.remote_addr
        # Get network hash
        ip_network_hash = SecurityMonitor.get_ip_network_hash(client_ip)

        if ip_network_hash:
            # Check for network changes
            _, network_changed = SecurityMonitor.check_network_change(session_key, client_ip)
            if network_changed:
                current_app.logger.warning(f"Profile update - network change detected for user {user_id}")

            # Check activity patterns
            _, suspicious_pattern = SecurityMonitor.track_activity_pattern(session_key)
            if suspicious_pattern:
                current_app.logger.warning(f"Profile update - suspicious activity pattern for user {user_id}")

            # If either security check fails for this sensitive operation, require re-auth
            if network_changed or suspicious_pattern:
                return jsonify({
                    "msg": "Обнаружена подозрительная активность. Пожалуйста, войдите в систему снова.",
                    "code": "SECURITY_REAUTH_REQUIRED"
                }), 403

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