# backend/models/token_blacklist.py
import sqlite3

from datetime import datetime, timezone, timedelta
from flask import current_app

from backend.models.base import get_db, query_db, commit_db


class TokenBlacklist:
    @staticmethod
    def blacklist_token(jti, user_id, expires_at):
        """Добавить токен в черный список при logout"""
        db = get_db()
        now = datetime.now(timezone.utc).isoformat()

        try:
            # Check if token is already blacklisted
            existing = query_db(
                'SELECT jti FROM token_blacklist WHERE jti = ?',
                [jti],
                one=True
            )

            if existing:
                # Token is already blacklisted, nothing to do
                current_app.logger.debug(f"Token {jti} already in blacklist, skipping insertion")
                return True

            # Insert the token into blacklist
            db.execute(
                'INSERT INTO token_blacklist (jti, user_id, blacklisted_at, expires_at) VALUES (?, ?, ?, ?)',
                [jti, user_id, now, expires_at]
            )
            commit_db()
            return True
        except sqlite3.Error as e:
            current_app.logger.error(f"Ошибка добавления токена в черный список: {e}")
            return False

    @staticmethod
    def is_token_blacklisted(jti, user_id=None):
        """Проверить, находится ли токен в черном списке

        Args:
            jti (str): The JWT ID to check
            user_id (str, optional): The user ID from the token

        Returns:
            bool: True if token is blacklisted, False otherwise
        """
        try:
            # Check if the specific token is in the blacklist
            token = query_db(
                'SELECT * FROM token_blacklist WHERE jti = ?',
                [jti],
                one=True
            )

            if token:
                return True

            # If user_id is provided, check if all tokens for this user are blocked
            if user_id:
                user_all_tokens_jti = f"user_all_tokens:{user_id}"
                all_tokens_blocked = query_db(
                    'SELECT * FROM token_blacklist WHERE jti = ?',
                    [user_all_tokens_jti],
                    one=True
                )
                return all_tokens_blocked is not None

            return False
        except Exception as e:
            current_app.logger.error(f"Ошибка проверки токена: {e}")
            return False

    @staticmethod
    def clear_expired_tokens():
        """Очистить просроченные токены из черного списка"""
        now = datetime.now(timezone.utc).isoformat()
        db = get_db()

        try:
            db.execute('DELETE FROM token_blacklist WHERE expires_at < ?', [now])
            commit_db()
        except sqlite3.Error as e:
            current_app.logger.error(f"Ошибка очистки просроченных токенов: {e}")

    @staticmethod
    def blacklist_user_tokens(user_id):
        """Заблокировать все токены пользователя"""
        try:
            db = get_db()
            now = datetime.now(timezone.utc).isoformat()

            # Создаем специальную запись в черном списке,
            # которая будет означать, что все токены пользователя заблокированы
            # Используем специальный идентификатор "user_all_tokens:{user_id}"

            # Сначала удаляем любые существующие записи для этого пользователя
            db.execute('DELETE FROM token_blacklist WHERE user_id = ?', [user_id])

            # Создаем уникальный jti для записи, блокирующей все токены пользователя
            block_all_jti = f"user_all_tokens:{user_id}"

            # Добавляем запись в черный список со сроком действия в 1 год
            # (или другим достаточно долгим периодом)
            future_date = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()

            db.execute(
                'INSERT INTO token_blacklist (jti, user_id, blacklisted_at, expires_at) VALUES (?, ?, ?, ?)',
                [block_all_jti, user_id, now, future_date]
            )
            commit_db()

            return True
        except sqlite3.Error as e:
            current_app.logger.error(f"Ошибка блокировки токенов пользователя: {e}")
            return False