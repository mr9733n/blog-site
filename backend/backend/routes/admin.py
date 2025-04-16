# backend/routes/admin.py
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from functools import wraps

from backend.models import User

admin_bp = Blueprint('admin', __name__)


# Функция-декоратор для проверки прав администратора
def admin_required(fn):
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id)

        # Проверка административных прав
        if not User.is_admin(user_id):
            return jsonify({"msg": "Требуются права администратора"}), 403

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