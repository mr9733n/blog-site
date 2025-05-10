# backend/routes/admin.py
import time
from datetime import datetime

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt, verify_jwt_in_request
from functools import wraps

from backend.models import User
from backend.models.security import SecurityMonitor
from backend.models.session import SessionManager
from backend.services.security_validator import SecurityValidator
from backend.models.base import query_db
from backend.models.token_blacklist import TokenBlacklist

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def admin_security_check():
    """Enhanced security checks for admin routes"""
    try:
        # Skip for OPTIONS requests (CORS preflight)
        if request.method == 'OPTIONS':
            return

        # Skip for public routes (though they shouldn't be under admin blueprint anyway)
        public_endpoints = ['/api/posts', '/api/images/data']
        if any(request.path.startswith(endpoint) for endpoint in public_endpoints) and request.method == 'GET':
            return

        # Use centralized security validator with JWT verification
        try:
            # First, verify JWT is present
            verify_jwt_in_request()
            # Затем выполняем проверку доступа администратора только один раз
            is_valid, error_response = SecurityValidator.validate_admin_access()
            if not is_valid:
                return error_response
        except Exception as e:
            current_app.logger.warning(f"JWT validation failed in admin route: {e}")
            return jsonify({"msg": "Требуется авторизация"}), 401

        # Получаем данные JWT для дополнительных проверок
        jwt_data = get_jwt()
        user_id = jwt_data.get('sub')
        session_key = jwt_data.get('session_key')

        # Get request data
        device_fingerprint = request.headers.get('X-Device-Fingerprint')
        csrf_token = request.headers.get('X-CSRF-STATE')
        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if client_ip and ',' in client_ip:
            client_ip = client_ip.split(',')[0].strip()

        # 4. Check for suspicious activity patterns
        security_status = SecurityMonitor.perform_comprehensive_checks(session_key, client_ip, request.path)

        if security_status['risk_level'] == 'high':
            current_app.logger.warning(f"Admin access blocked: High security risk for user {user_id}")
            return jsonify({
                "msg": "Доступ запрещен: обнаружена подозрительная активность",
                "details": "Требуется повторная аутентификация"
            }), 403
    except Exception as e:
        current_app.logger.error(f"Error in admin security check: {e}")
        # Fail closed on errors
        return jsonify({"msg": "Ошибка проверки безопасности"}), 500

# Функция-декоратор для проверки прав администратора
def admin_required(fn):
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id)

        # Verify admin rights
        if not User.is_admin(user_id):
            current_app.logger.warning(f"Admin access attempt by non-admin user: {user_id}")
            return jsonify({"msg": "Требуются права администратора"}), 403

        # Additional time-based verification for sensitive admin actions
        jwt_data = get_jwt()
        created_at = jwt_data.get('created_at', 0)
        token_age = int(time.time()) - created_at

        # For very sensitive operations, require a fresh token (< 15 minutes old)
        if token_age > 900:  # 15 minutes
            # Only enforce for state-changing operations
            if request.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
                current_app.logger.warning(f"Admin operation blocked: token too old ({token_age}s)")
                return jsonify({
                    "msg": "Для этой операции требуется свежий токен аутентификации",
                    "code": "FRESH_TOKEN_REQUIRED"
                }), 401

        is_valid, error_response = SecurityValidator.validate_admin_access()

        if not is_valid:
            return error_response

        return fn(*args, **kwargs)

    return wrapper


# Маршрут для получения списка пользователей (только для админа)
@admin_bp.route('/users', methods=['GET'])
@admin_required
def get_users():
    try:
        users = User.get_all_users_with_status()
        # Удаляем хеши паролей из ответа
        for user in users:
            user.pop('password', None)
        return jsonify(users)
    except Exception as e:
        current_app.logger.error(f"Ошибка получения списка пользователей: {str(e)}")
        return jsonify({"msg": "Произошла ошибка при получении списка пользователей"}), 500


# Маршрут для получения подробной информации о пользователе (только для админа)
@admin_bp.route('/users/<int:user_id>', methods=['GET'])
@admin_required
def get_user_details(user_id):
    try:
        user = User.get_user_with_status(user_id)
        if not user:
            return jsonify({"msg": "Пользователь не найден"}), 404

        # Удаляем хеш пароля из ответа
        user.pop('password', None)

        return jsonify(user)
    except Exception as e:
        current_app.logger.error(f"Ошибка получения данных пользователя: {str(e)}")
        return jsonify({"msg": "Произошла ошибка при получении данных пользователя"}), 500


# Маршрут для блокировки/разблокировки пользователя (только для админа)
@admin_bp.route('/users/<int:user_id>/block', methods=['POST'])
@admin_required
def toggle_user_block(user_id):
    try:
        data = request.get_json()
        blocked = data.get('blocked', False)

        result = User.toggle_user_block(user_id, blocked)

        if blocked:
            return jsonify({"msg": "Пользователь успешно заблокирован"})
        else:
            return jsonify({"msg": "Пользователь успешно разблокирован"})
    except ValueError as e:
        return jsonify({"msg": str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Ошибка изменения блокировки пользователя: {str(e)}")
        return jsonify({"msg": "Произошла ошибка при изменении блокировки пользователя"}), 500


# Маршрут для обновления данных пользователя (только для админа)
@admin_bp.route('/users/<int:user_id>', methods=['PUT'])
@admin_required
def update_user(user_id):
    try:
        data = request.get_json()
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')

        # Обновляем данные пользователя
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


# Session management endpoint for administrators
@admin_bp.route('/sessions', methods=['GET'])
@admin_required
def get_all_sessions():
    """Get all active sessions (admin only)"""
    try:
        # Get query parameters
        user_id = request.args.get('user_id', type=int)

        # Build query
        query = '''
            SELECT us.*, users.username 
            FROM user_sessions us
            JOIN users ON us.user_id = users.id
            WHERE us.state = "active"
        '''

        params = []

        # Filter by user if specified
        if user_id:
            query += " AND us.user_id = ?"
            params.append(user_id)

        query += " ORDER BY us.last_activity DESC"

        # Execute query
        sessions = query_db(query, params)

        # Convert to list of dicts and sanitize
        result = []
        for session in sessions:
            session_dict = dict(session)

            # Remove sensitive data
            if 'device_fingerprint' in session_dict:
                session_dict['device_fingerprint'] = session_dict['device_fingerprint'][:8] + "..." if session_dict[
                    'device_fingerprint'] else None

            # Format dates for better readability
            for date_field in ['last_activity', 'created_at', 'expires_at']:
                if session_dict.get(date_field):
                    try:
                        dt = datetime.fromisoformat(session_dict[date_field].replace('Z', '+00:00'))
                        session_dict[date_field] = dt.strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        pass

            # Add security risk assessment
            security_status = SecurityMonitor.perform_comprehensive_checks(
                session_dict['session_key'],
                request_path="/api/admin/sessions"
            )

            session_dict['security_status'] = security_status

            result.append(session_dict)

        return jsonify(result)
    except Exception as e:
        current_app.logger.error(f"Error getting sessions: {e}")
        return jsonify({"msg": "Ошибка при получении списка сессий"}), 500


@admin_bp.route('/sessions/<session_key>', methods=['DELETE'])
@admin_required
def terminate_session(session_key):
    """Terminate a specific session (admin only)"""
    try:
        # Get session info
        session = query_db(
            'SELECT * FROM user_sessions WHERE session_key = ?',
            [session_key],
            one=True
        )

        if not session:
            return jsonify({"msg": "Сессия не найдена"}), 404

        # Convert to dict
        session = dict(session)

        # Check if this is the admin's own current session
        current_token = get_jwt()
        current_session_key = current_token.get('session_key')

        if current_session_key == session_key:
            return jsonify({
                "msg": "Невозможно завершить текущую сессию администратора",
                "hint": "Используйте функцию выхода из системы вместо принудительного завершения сессии"
            }), 400

        # Terminate the session
        success = SessionManager.delete_session(session_key)

        if not success:
            return jsonify({"msg": "Ошибка при завершении сессии"}), 500

        # Record security event
        SecurityMonitor.record_security_event(
            user_id=int(get_jwt_identity()),
            session_key=current_session_key,
            event_type="admin_terminated_session",
            request_path=request.path,
            details={
                "target_user_id": session['user_id'],
                "target_session_key": session_key
            }
        )

        return jsonify({
            "msg": "Сессия успешно завершена",
            "user_id": session['user_id']
        })
    except Exception as e:
        current_app.logger.error(f"Error terminating session: {e}")
        return jsonify({"msg": "Ошибка при завершении сессии"}), 500


@admin_bp.route('/users/<int:target_user_id>/sessions', methods=['DELETE'])
@admin_required
def terminate_user_sessions(target_user_id):
    """Terminate all sessions for a specific user (admin only)"""
    try:
        # Check if user exists
        user = User.get_by_id(target_user_id)
        if not user:
            return jsonify({"msg": "Пользователь не найден"}), 404

        # Check if this is the admin's own account
        admin_id = int(get_jwt_identity())
        if admin_id == target_user_id:
            return jsonify({
                "msg": "Невозможно завершить все сессии администратора",
                "hint": "Используйте функцию выхода из системы вместо принудительного завершения сессий"
            }), 400

        # Get all active sessions for the user
        sessions = query_db(
            'SELECT session_key FROM user_sessions WHERE user_id = ? AND state = "active"',
            [target_user_id]
        )

        if not sessions:
            return jsonify({"msg": "Активные сессии не найдены"}), 404

        # Convert to list
        session_keys = [session['session_key'] for session in sessions]

        # Terminate all sessions
        terminated_count = 0
        for session_key in session_keys:
            if SessionManager.delete_session(session_key):
                terminated_count += 1

        # Block all tokens for this user
        TokenBlacklist.blacklist_user_tokens(target_user_id)

        # Record security event
        SecurityMonitor.record_security_event(
            user_id=admin_id,
            session_key=get_jwt().get('session_key'),
            event_type="admin_terminated_all_sessions",
            request_path=request.path,
            details={
                "target_user_id": target_user_id,
                "sessions_terminated": terminated_count
            }
        )

        return jsonify({
            "msg": f"Все сессии пользователя успешно завершены ({terminated_count})",
            "user_id": target_user_id,
            "terminated_count": terminated_count
        })
    except Exception as e:
        current_app.logger.error(f"Error terminating user sessions: {e}")
        return jsonify({"msg": "Ошибка при завершении сессий пользователя"}), 500

admin_bp.before_request(admin_security_check)