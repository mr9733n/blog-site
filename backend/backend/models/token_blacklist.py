# backend/models/token_blacklist.py
import sqlite3
from datetime import datetime, timezone, timedelta
from flask import current_app

from backend.models.base import get_db, query_db, commit_db


class TokenBlacklist:
    """
    TokenBlacklist handles JWT token revocation:
    - Adding tokens to the blacklist (logout, session invalidation)
    - Checking if tokens are blacklisted
    - Cleaning up expired blacklisted tokens
    - Blocking all tokens for a specific user
    """

    @staticmethod
    def blacklist_token(jti, user_id, expires_at):
        """
        Add a token to the blacklist during logout

        Args:
            jti (str): JWT token ID
            user_id (int): User ID associated with the token
            expires_at (str): ISO-format timestamp when the token expires

        Returns:
            bool: True if token was blacklisted successfully, False otherwise
        """
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
            current_app.logger.error(f"Error adding token to blacklist: {e}")
            return False

    @staticmethod
    def is_token_blacklisted(jti, user_id=None):
        """
        Check if a token is in the blacklist

        Args:
            jti (str): JWT token ID to check
            user_id (str, optional): User ID from the token

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
            current_app.logger.error(f"Error checking token blacklist: {e}")
            return False

    @staticmethod
    def clear_expired_tokens():
        """
        Clear expired tokens from the blacklist

        Returns:
            bool: True if cleanup was successful, False otherwise
        """
        now = datetime.now(timezone.utc).isoformat()
        db = get_db()

        try:
            db.execute('DELETE FROM token_blacklist WHERE expires_at < ?', [now])
            commit_db()
            return True
        except sqlite3.Error as e:
            current_app.logger.error(f"Error clearing expired tokens: {e}")
            return False

    @staticmethod
    def blacklist_user_tokens(user_id):
        """
        Block all tokens for a specific user (useful when changing password,
        detecting suspicious activity, or admin blocking a user)

        Args:
            user_id (int): User ID whose tokens should be blocked

        Returns:
            bool: True if operation was successful, False otherwise
        """
        try:
            db = get_db()
            now = datetime.now(timezone.utc).isoformat()

            # First delete any existing entries for this user
            db.execute('DELETE FROM token_blacklist WHERE user_id = ?', [user_id])

            # Create a special JTI for blocking all user tokens
            block_all_jti = f"user_all_tokens:{user_id}"

            # Add blacklist entry with a 1-year expiration
            future_date = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()

            db.execute(
                'INSERT INTO token_blacklist (jti, user_id, blacklisted_at, expires_at) VALUES (?, ?, ?, ?)',
                [block_all_jti, user_id, now, future_date]
            )
            commit_db()

            return True
        except sqlite3.Error as e:
            current_app.logger.error(f"Error blocking user tokens: {e}")
            return False