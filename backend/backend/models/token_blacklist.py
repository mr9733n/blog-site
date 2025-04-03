# backend/models/token_blacklist.py
import sqlite3

from datetime import datetime
from flask import current_app

from backend.models.base import get_db, query_db, commit_db


class TokenBlacklist:
    @staticmethod
    def blacklist_token(jti, user_id, expires_at):
        """Добавить токен в черный список при logout"""
        db = get_db()
        now = datetime.now().isoformat()

        try:
            db.execute(
                'INSERT INTO token_blacklist (jti, user_id, blacklisted_at, expires_at) VALUES (?, ?, ?, ?)',
                [jti, user_id, now, expires_at]
            )
            commit_db()
        except sqlite3.Error as e:
            current_app.logger.error(f"Ошибка добавления токена в черный список: {e}")
            return False
        return True

    @staticmethod
    def is_token_blacklisted(jti):
        """Проверить, находится ли токен в черном списке"""
        try:
            token = query_db(
                'SELECT * FROM token_blacklist WHERE jti = ?',
                [jti],
                one=True
            )
            return token is not None
        except sqlite3.Error:
            return False

    @staticmethod
    def clear_expired_tokens():
        """Очистить просроченные токены из черного списка"""
        now = datetime.now().isoformat()
        db = get_db()

        try:
            db.execute('DELETE FROM token_blacklist WHERE expires_at < ?', [now])
            commit_db()
        except sqlite3.Error as e:
            current_app.logger.error(f"Ошибка очистки просроченных токенов: {e}")

    @staticmethod
    def blacklist_user_tokens(user_id):
        """Заблокировать все активные токены пользователя"""
        try:
            db = get_db()
            now = datetime.now().isoformat()

            db.execute(
                'DELETE FROM token_blacklist WHERE user_id = ?',
                [user_id]
            )
            commit_db()
        except sqlite3.Error as e:
            current_app.logger.error(f"Ошибка блокировки токенов пользователя: {e}")
            return False
        return True