# backend/models/session.py
import json
import sqlite3
from datetime import datetime, timezone, timedelta
from flask import current_app, request

from backend.models.base import get_db, query_db, commit_db
from backend.models.security import SecurityMonitor


class SessionManager:
    """
    Session Manager handles all session-related operations including:
    - Creating and storing session keys
    - Validating session activity and state
    - Managing session fingerprints and security properties
    - Session expiration and cleanup
    """

    @staticmethod
    def ensure_column_exists(column_name, column_def="TEXT"):
        """
        Helper method to ensure a column exists in the user_sessions table

        Args:
            column_name (str): The name of the column to check/add
            column_def (str): The column definition (default: TEXT)

        Returns:
            bool: True if column exists or was added, False otherwise
        """
        db = get_db()
        try:
            # Check if column exists
            query_db(f'SELECT {column_name} FROM user_sessions LIMIT 1')
            return True
        except sqlite3.OperationalError:
            # Column doesn't exist, try to add it
            try:
                db.execute(f'ALTER TABLE user_sessions ADD COLUMN {column_name} {column_def}')
                commit_db()
                return True
            except sqlite3.OperationalError as e:
                current_app.logger.error(f"Couldn't add column {column_name}: {e}")
                return False

    @staticmethod
    def store_session(user_id, session_key, csrf_state, session_state, expires_at, device_fingerprint=None):
        """
        Create and store a new session

        Args:
            user_id (int): User ID associated with the session
            session_key (str): Unique session identifier
            csrf_state (str): CSRF token state
            session_state (str): Current session state (e.g., 'active')
            expires_at (str): ISO format timestamp when the session expires
            device_fingerprint (str, optional): Device fingerprint for security checks

        Returns:
            bool: True if session was stored successfully, False otherwise
        """
        db = get_db()
        try:
            # Check if device_fingerprint column exists
            has_fingerprint = SessionManager.ensure_column_exists('device_fingerprint')

            # Current timestamp for activity tracking
            now = datetime.now(timezone.utc).isoformat()

            # Insert session with appropriate columns
            if has_fingerprint and device_fingerprint:
                db.execute(
                    '''INSERT INTO user_sessions 
                       (user_id, session_key, csrf_state, state, expires_at, device_fingerprint, 
                        last_activity, request_counter, last_counter_update) 
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    [user_id, session_key, csrf_state, session_state, expires_at,
                     device_fingerprint, now, 0, now]
                )
            else:
                db.execute(
                    '''INSERT INTO user_sessions 
                       (user_id, session_key, csrf_state, state, expires_at, 
                        last_activity, request_counter, last_counter_update) 
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                    [user_id, session_key, csrf_state, session_state, expires_at,
                     now, 0, now]
                )
            commit_db()
            return True
        except sqlite3.Error as e:
            current_app.logger.error(f"Error storing session: {e}")
            return False

    @staticmethod
    def update_session(session_key, new_session_key=None, csrf_state=None,
                       session_state=None, device_fingerprint=None):
        """
        Update an existing session with new values

        Args:
            session_key (str): Current session key to update
            new_session_key (str, optional): New session key to set
            csrf_state (str, optional): New CSRF state
            session_state (str, optional): New session state
            device_fingerprint (str, optional): New device fingerprint

        Returns:
            bool: True if session was updated successfully, False otherwise
        """
        db = get_db()
        try:
            # Check which columns to update
            update_parts = []
            params = []

            if new_session_key:
                update_parts.append("session_key = ?")
                params.append(new_session_key)

            if csrf_state:
                update_parts.append("csrf_state = ?")
                params.append(csrf_state)

            if session_state:
                update_parts.append("state = ?")
                params.append(session_state)

            # Check if device_fingerprint column exists
            if device_fingerprint and SessionManager.ensure_column_exists('device_fingerprint'):
                update_parts.append("device_fingerprint = ?")
                params.append(device_fingerprint)

            if not update_parts:
                return True  # Nothing to update

            # Build and execute the query
            query = f"UPDATE user_sessions SET {', '.join(update_parts)} WHERE session_key = ?"
            params.append(session_key)

            db.execute(query, params)
            commit_db()
            return True
        except sqlite3.Error as e:
            current_app.logger.error(f"Error updating session: {e}")
            return False

    @staticmethod
    def update_activity(user_id):
        """
        Update the last activity timestamp for a user's sessions

        Args:
            user_id (int): The user ID to update

        Returns:
            bool: True if activity was updated, False otherwise
        """
        db = get_db()
        try:
            now = datetime.now(timezone.utc).isoformat()
            db.execute(
                'UPDATE user_sessions SET last_activity = ? WHERE user_id = ?',
                [now, user_id]
            )
            commit_db()
            return True
        except sqlite3.Error as e:
            current_app.logger.error(f"Error updating session activity: {e}")
            return False

    @staticmethod
    def check_activity(session_key):
        """
        Check if a session is still active based on last activity time

        Args:
            session_key (str): The session key to check

        Returns:
            bool: True if session is active, False if inactive/expired
        """
        db = get_db()
        try:
            session = query_db(
                'SELECT * FROM user_sessions WHERE session_key = ?',
                [session_key],
                one=True
            )

            if not session:
                return False

            last_activity = datetime.fromisoformat(session['last_activity']).replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            inactivity_seconds = (now - last_activity).total_seconds()

            if inactivity_seconds > current_app.config['MAX_INACTIVITY']:
                # Session inactive too long, mark as expired
                db.execute('UPDATE user_sessions SET state = "expired" WHERE session_key = ?', [session_key])
                commit_db()
                return False

            return True
        except Exception as e:
            current_app.logger.error(f"Error checking session activity: {e}")
            return False

    @staticmethod
    def validate_session(session_key, user_id):
        """
        Validate if a session belongs to a user and is active

        Args:
            session_key (str): The session key to validate
            user_id (int): The user ID to check against

        Returns:
            bool: True if session is valid for this user, False otherwise
        """
        session = query_db(
            'SELECT * FROM user_sessions WHERE session_key = ? AND user_id = ? AND state = "active"',
            [session_key, user_id],
            one=True
        )
        return session is not None

    @staticmethod
    def validate_fingerprint(session_key, device_fingerprint):
        """
        Улучшенная валидация fingerprint, исправляющая уязвимость подмены

        Args:
            session_key (str): The session key to check
            device_fingerprint (str): The fingerprint to validate

        Returns:
            bool: True if fingerprints match, False otherwise
        """
        try:
            # Проверка на наличие обязательных параметров
            if not session_key or not device_fingerprint:
                current_app.logger.warning("Missing session key or device fingerprint")
                return False  # Fail closed instead of open

            # Получаем сессию
            session = query_db(
                'SELECT * FROM user_sessions WHERE session_key = ?',
                [session_key],
                one=True
            )

            if not session:
                current_app.logger.warning(f"Session not found: {session_key[:8]}")
                return False

            # Проверяем состояние сессии
            if session['state'] != 'active':
                current_app.logger.warning(f"Session is not active: {session_key[:8]}, state: {session['state']}")
                return False

            # Проверяем срок действия
            now = datetime.now(timezone.utc).isoformat()
            if session['expires_at'] < now:
                current_app.logger.warning(f"Session expired: {session_key[:8]}")
                return False

            # Получаем сохраненный fingerprint
            stored_fingerprint = session['device_fingerprint'] if 'device_fingerprint' in session else None

            # Если stored_fingerprint равен None, это, вероятно, старая сессия
            if stored_fingerprint is None:
                current_app.logger.warning(f"No fingerprint stored for session: {session_key[:8]}")
                return False

            # Проверяем соответствие fingerprint
            fingerprint_matches = stored_fingerprint == device_fingerprint

            # Записываем результат проверки
            if not fingerprint_matches:
                current_app.logger.warning(f"Fingerprint mismatch for session {session_key[:8]}")

                # Записываем событие безопасности для дальнейшего анализа
                try:

                    SecurityMonitor.record_security_event(
                        user_id=session['user_id'],
                        session_key=session_key,
                        event_type="fingerprint_mismatch",
                        request_path=request.path if hasattr(request, 'path') else None,
                        details={
                            "stored_fingerprint": stored_fingerprint[:8] + "..." if stored_fingerprint else None,
                            "provided_fingerprint": device_fingerprint[:8] + "..." if device_fingerprint else None
                        }
                    )
                except Exception as e:
                    current_app.logger.error(f"Error recording security event: {e}")

            return fingerprint_matches
        except Exception as e:
            current_app.logger.error(f"Error validating fingerprint: {e}")
            # Fail closed for better security
            return False

    @staticmethod
    def check_session_valid(session_key, device_fingerprint=None):
        """
        Улучшенная комплексная валидация сессии, проверяющая срок действия, состояние и fingerprint

        Args:
            session_key (str): The session key to validate
            device_fingerprint (str, optional): Device fingerprint to check

        Returns:
            bool: True if session is valid, False otherwise
        """
        try:
            # Проверяем основные параметры
            if not session_key:
                return False

            now = datetime.now(timezone.utc).isoformat()

            # Получаем информацию о сессии
            session = query_db(
                'SELECT * FROM user_sessions WHERE session_key = ? AND expires_at > ? AND state = "active"',
                [session_key, now],
                one=True
            )

            if not session:
                current_app.logger.warning(f"Invalid session: {session_key[:8] if session_key else 'None'}")
                return False

            # Проверка fingerprint, если предоставлен
            if device_fingerprint:
                if not SessionManager.validate_fingerprint(session_key, device_fingerprint):
                    current_app.logger.warning(f"Session fingerprint validation failed for {session_key[:8]}")
                    return False
            elif 'device_fingerprint' in session and session['device_fingerprint']:
                # Если fingerprint требуется для сессии, но не предоставлен в запросе
                current_app.logger.warning(f"Fingerprint required but not provided for session {session_key[:8]}")

                # Для чувствительных маршрутов отклоняем запрос
                if hasattr(request, 'path'):
                    sensitive_paths = ['/api/admin', '/api/user/update', '/api/settings']
                    if any(request.path.startswith(path) for path in sensitive_paths):
                        return False

            # Проверка активности
            return SessionManager.check_activity(session_key)
        except Exception as e:
            current_app.logger.error(f"Error validating session: {e}")
            return False

    @staticmethod
    def delete_session(session_key):
        """
        Delete a session completely

        Args:
            session_key (str): Session key to delete

        Returns:
            bool: True if session was deleted, False otherwise
        """
        db = get_db()
        try:
            if session_key:
                db.execute('DELETE FROM user_sessions WHERE session_key = ?', [session_key])
                commit_db()
                return True
            return False
        except Exception as e:
            current_app.logger.error(f"Error deleting session: {e}")
            return False

    @staticmethod
    def clear_expired():
        """
        Clear all expired sessions from the database

        Returns:
            bool: True if cleanup was successful, False otherwise
        """
        now = datetime.now(timezone.utc).isoformat()
        db = get_db()
        try:
            db.execute('DELETE FROM user_sessions WHERE expires_at < ?', [now])
            commit_db()
            return True
        except sqlite3.Error as e:
            current_app.logger.error(f"Error clearing expired sessions: {e}")
            return False