# backend/services/auth_service.py
from backend.models import User


def validate_login_credentials(username, password):
    """
    Проверяет учетные данные пользователя

    Returns:
        dict: Результат проверки с ключами:
            - success (bool): Успешна ли проверка
            - message (str): Сообщение об ошибке (если есть)
            - user (dict): Информация о пользователе (если успешно)
    """
    if not User.verify_password(username, password):
        return {
            'success': False,
            'message': 'Неверные учетные данные'
        }

    user = User.get_by_username(username)

    return {
        'success': True,
        'user': dict(user)
    }