import sqlite3

from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask import current_app

from backend.models.base import get_db, query_db, commit_db


class User:
    """Модель пользователя"""

    def is_admin(user_id):
        """Check if a user has admin privileges"""
        # Simple check - user with ID 1 is admin
        return int(user_id) == 1

    @staticmethod
    def get_by_id(user_id):
        """Получить пользователя по ID"""
        return query_db('SELECT * FROM users WHERE id = ?', [user_id], one=True)

    @staticmethod
    def get_by_username(username):
        """Получить пользователя по имени пользователя"""
        return query_db('SELECT * FROM users WHERE username = ?', [username], one=True)

    @staticmethod
    def create(username, email, password):
        """Создать нового пользователя"""
        # Проверка наличия пользователя
        if User.get_by_username(username):
            raise ValueError("Пользователь с таким именем уже существует")

        # Проверка наличия email
        if query_db('SELECT * FROM users WHERE email = ?', [email], one=True):
            raise ValueError("Пользователь с таким email уже существует")

        # Хеширование пароля и сохранение пользователя
        password_hash = generate_password_hash(password)
        db = get_db()
        db.execute(
            'INSERT INTO users (username, password, email, created_at) VALUES (?, ?, ?, ?)',
            [username, password_hash, email, datetime.now().isoformat()]
        )
        commit_db()
        return User.get_by_username(username)

    @staticmethod
    def verify_password(username, password):
        """Проверить пароль пользователя"""
        user = User.get_by_username(username)
        if not user:
            return False
        return check_password_hash(user['password'], password)

    @staticmethod
    def get_token_lifetime(user_id):
        """Get token lifetime setting for a user (in seconds)"""
        try:
            setting = query_db(
                'SELECT token_lifetime FROM user_settings WHERE user_id = ?',
                [user_id], one=True
            )
            if setting:
                return setting['token_lifetime']

            # Create default setting if not exists
            db = get_db()

            default_lifetime = current_app.config['JWT_ACCESS_TOKEN_EXPIRES']
            db.execute(
                'INSERT INTO user_settings (user_id, token_lifetime) VALUES (?, ?)',
                [user_id, default_lifetime]
            )
            commit_db()
            return default_lifetime
        except sqlite3.OperationalError as e:
            if "no such table" in str(e):
                # Таблица не существует, используем значение по умолчанию

                return current_app.config['JWT_ACCESS_TOKEN_EXPIRES']
            raise  # Пробрасываем другие ошибки

    @staticmethod
    def update_token_settings(user_id, token_lifetime, refresh_token_lifetime):
        """Update token lifetime settings for a user"""
        db = get_db()
        # Проверяем, существуют ли настройки
        setting = query_db(
            'SELECT * FROM user_settings WHERE user_id = ?',
            [user_id], one=True
        )

        if setting:
            db.execute(
                'UPDATE user_settings SET token_lifetime = ?, refresh_token_lifetime = ? WHERE user_id = ?',
                [token_lifetime, refresh_token_lifetime, user_id]
            )
        else:
            db.execute(
                'INSERT INTO user_settings (user_id, token_lifetime, refresh_token_lifetime) VALUES (?, ?, ?)',
                [user_id, token_lifetime, refresh_token_lifetime]
            )
        commit_db()
        return True


    @staticmethod
    def get_all_users():
        """Получить список всех пользователей"""
        return query_db('SELECT id, username, email, created_at FROM users ORDER BY id')


    @staticmethod
    def update_user(user_id, username=None, email=None, password=None):
        """Обновить данные пользователя"""
        db = get_db()
        update_parts = []
        params = []

        if username:
            # Проверка уникальности нового имени пользователя
            existing = query_db('SELECT id FROM users WHERE username = ? AND id != ?',
                                [username, user_id], one=True)
            if existing:
                raise ValueError("Пользователь с таким именем уже существует")
            update_parts.append("username = ?")
            params.append(username)

        if email:
            # Проверка уникальности нового email
            existing = query_db('SELECT id FROM users WHERE email = ? AND id != ?',
                                [email, user_id], one=True)
            if existing:
                raise ValueError("Пользователь с таким email уже существует")
            update_parts.append("email = ?")
            params.append(email)

        if password:
            password_hash = generate_password_hash(password)
            update_parts.append("password = ?")
            params.append(password_hash)

        if not update_parts:
            return False  # Нечего обновлять

        # Формируем SQL запрос
        query = f"UPDATE users SET {', '.join(update_parts)} WHERE id = ?"
        params.append(user_id)

        # Выполняем запрос
        db.execute(query, params)
        commit_db()

        return True


    @staticmethod
    def toggle_user_block(user_id, blocked_status):
        """Заблокировать или разблокировать пользователя"""
        # Проверяем, что не блокируем админа (пользователя с id=1)
        if int(user_id) == 1:
            raise ValueError("Невозможно заблокировать администратора")

        # Проверяем, существует ли таблица user_status
        db = get_db()
        try:
            # Проверяем существование таблицы user_status
            db.execute("SELECT 1 FROM user_status LIMIT 1")
        except sqlite3.OperationalError:
            # Таблица не существует, создаем её
            db.execute('''
                CREATE TABLE IF NOT EXISTS user_status (
                    user_id INTEGER PRIMARY KEY,
                    is_blocked INTEGER NOT NULL DEFAULT 0,
                    blocked_at TEXT,
                    blocked_reason TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            ''')
            commit_db()

        # Теперь работаем с таблицей
        if blocked_status:
            # Блокируем пользователя
            now = datetime.now().isoformat()
            db.execute('''
                INSERT INTO user_status (user_id, is_blocked, blocked_at) 
                VALUES (?, 1, ?) 
                ON CONFLICT(user_id) DO UPDATE SET is_blocked = 1, blocked_at = ?
            ''', [user_id, now, now])
        else:
            # Разблокируем пользователя
            db.execute('''
                INSERT INTO user_status (user_id, is_blocked, blocked_at) 
                VALUES (?, 0, NULL) 
                ON CONFLICT(user_id) DO UPDATE SET is_blocked = 0, blocked_at = NULL
            ''', [user_id])

        commit_db()
        return True


    @staticmethod
    def is_user_blocked(user_id):
        """Проверить, заблокирован ли пользователь"""
        try:
            status = query_db(
                'SELECT is_blocked FROM user_status WHERE user_id = ?',
                [user_id], one=True
            )
            return status and status['is_blocked'] == 1
        except sqlite3.OperationalError:
            # Таблица user_status не существует, значит никто не заблокирован
            return False


    @staticmethod
    def get_user_with_status(user_id):
        """Получить информацию о пользователе вместе со статусом блокировки"""
        user = User.get_by_id(user_id)
        if not user:
            return None

        user_dict = dict(user)

        try:
            status = query_db(
                'SELECT is_blocked, blocked_at, blocked_reason FROM user_status WHERE user_id = ?',
                [user_id], one=True
            )

            if status:
                user_dict['is_blocked'] = status['is_blocked'] == 1
                user_dict['blocked_at'] = status['blocked_at']
                user_dict['blocked_reason'] = status['blocked_reason']
            else:
                user_dict['is_blocked'] = False
                user_dict['blocked_at'] = None
                user_dict['blocked_reason'] = None
        except sqlite3.OperationalError:
            # Таблица не существует
            user_dict['is_blocked'] = False
            user_dict['blocked_at'] = None
            user_dict['blocked_reason'] = None

        return user_dict


    @staticmethod
    def get_all_users_with_status():
        """Получить список всех пользователей с информацией о блокировке"""
        users = User.get_all_users()
        users_list = [dict(user) for user in users]

        try:
            # Пытаемся получить статусы пользователей
            statuses = query_db('SELECT user_id, is_blocked, blocked_at, blocked_reason FROM user_status')
            statuses_dict = {status['user_id']: status for status in statuses}

            # Добавляем информацию о блокировке к каждому пользователю
            for user in users_list:
                user_id = user['id']
                if user_id in statuses_dict:
                    status = statuses_dict[user_id]
                    user['is_blocked'] = status['is_blocked'] == 1
                    user['blocked_at'] = status['blocked_at']
                    user['blocked_reason'] = status['blocked_reason']
                else:
                    user['is_blocked'] = False
                    user['blocked_at'] = None
                    user['blocked_reason'] = None
        except sqlite3.OperationalError:
            # Таблица user_status не существует
            # Задаём всем статус "не заблокирован"
            for user in users_list:
                user['is_blocked'] = False
                user['blocked_at'] = None
                user['blocked_reason'] = None

        return users_list