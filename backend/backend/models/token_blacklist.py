# backend/models/token_blacklist.py
import json
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

    @staticmethod
    def store_session_key(user_id, session_key, csrf_state, session_state, expires_at, device_fingerprint=None):
        """Сохранение ключа сессии с поддержкой fingerprint устройства"""
        db = get_db()
        try:
            # Check if user_sessions table has device_fingerprint column
            has_fingerprint = False
            try:
                query_db('SELECT device_fingerprint FROM user_sessions LIMIT 1')
                has_fingerprint = True
            except sqlite3.OperationalError:
                # Column doesn't exist, add it
                try:
                    db.execute('ALTER TABLE user_sessions ADD COLUMN device_fingerprint TEXT')
                    commit_db()
                    has_fingerprint = True
                except sqlite3.OperationalError as e:
                    current_app.logger.error(f"Couldn't add device_fingerprint column: {e}")

            if has_fingerprint and device_fingerprint:
                db.execute(
                    'INSERT INTO user_sessions (user_id, session_key, csrf_state, state, expires_at, device_fingerprint) VALUES (?, ?, ?, ?, ?, ?)',
                    [user_id, session_key, csrf_state, session_state, expires_at, device_fingerprint]
                )
            else:
                db.execute(
                    'INSERT INTO user_sessions (user_id, session_key, csrf_state, state, expires_at) VALUES (?, ?, ?, ?, ?)',
                    [user_id, session_key, csrf_state, session_state, expires_at]
                )
            commit_db()
            return True
        except sqlite3.Error as e:
            current_app.logger.error(f"Ошибка сохранения сессионного ключа: {e}")
            return False

    @staticmethod
    def increment_session_counter(session_key):
        """Increment the request counter for this session and check for suspicious activity"""
        db = get_db()
        try:
            # Make sure counter column exists (add if needed)
            has_counter = False
            try:
                query_db('SELECT request_counter FROM user_sessions LIMIT 1')
                has_counter = True
            except sqlite3.OperationalError:
                try:
                    db.execute('ALTER TABLE user_sessions ADD COLUMN request_counter INTEGER DEFAULT 0')
                    db.execute('ALTER TABLE user_sessions ADD COLUMN last_counter_update TEXT')
                    commit_db()
                    has_counter = True
                except sqlite3.OperationalError as e:
                    current_app.logger.error(f"Couldn't add request_counter column: {e}")
                    return False, None

            if has_counter:
                # Get current counter value
                session = query_db(
                    'SELECT request_counter, last_counter_update FROM user_sessions WHERE session_key = ?',
                    [session_key],
                    one=True
                )

                if not session:
                    return False, None

                current_counter = session['request_counter'] or 0
                last_update = session['last_counter_update']
                new_counter = current_counter + 1
                now = datetime.now(timezone.utc).isoformat()

                # Check for suspiciously rapid counter increments (potential parallel sessions)
                suspicious = False
                if last_update:
                    last_update_time = datetime.fromisoformat(last_update).replace(tzinfo=timezone.utc)
                    time_diff = (datetime.now(timezone.utc) - last_update_time).total_seconds()

                    # If counter increased multiple times in less than 2 seconds, flag as suspicious
                    if time_diff < 2 and new_counter - current_counter > 1:
                        suspicious = True
                        current_app.logger.warning(f"Suspicious rapid counter increments for session {session_key}")

                # Update the counter
                db.execute(
                    'UPDATE user_sessions SET request_counter = ?, last_counter_update = ? WHERE session_key = ?',
                    [new_counter, now, session_key]
                )
                commit_db()

                return True, suspicious

        except Exception as e:
            current_app.logger.error(f"Error updating session counter: {e}")
            return False, None

    @staticmethod
    def update_session_keys(session_key, new_session_key=None, csrf_state=None, session_state=None,
                            device_fingerprint=None):
        """Обновить ключи сессии, включая fingerprint устройства"""
        db = get_db()
        try:
            # Check if client_fingerprint column exists
            has_fingerprint = False
            try:
                query_db('SELECT device_fingerprint FROM user_sessions LIMIT 1')
                has_fingerprint = True
            except sqlite3.OperationalError:
                pass

            if has_fingerprint and device_fingerprint:
                db.execute(
                    'UPDATE user_sessions SET session_key = ?, csrf_state = ?, state = ?, device_fingerprint = ? WHERE session_key = ?',
                    [new_session_key, csrf_state, session_state, device_fingerprint, session_key]
                )
            else:
                db.execute(
                    'UPDATE user_sessions SET session_key = ?, csrf_state = ?, state = ? WHERE session_key = ?',
                    [new_session_key, csrf_state, session_state, session_key]
                )
            commit_db()
            return True
        except sqlite3.Error as e:
            current_app.logger.error(f"Ошибка обновления сессионных данных: {e}")
            return False

    @staticmethod
    def update_session_activity(user_id):
        db = get_db()
        try:
            db.execute(
                'UPDATE user_sessions SET last_activity = ? WHERE user_id = ?',
                [datetime.now(timezone.utc).isoformat(), user_id]
            )
        except sqlite3.Error as e:
            current_app.logger.error(f"Ошибка обновления сессионной активности : {e}")
            return False

    @staticmethod
    def validate_session_fingerprint(session_key, device_fingerprint):
        """Проверка соответствия fingerprint устройства для сессии"""
        try:
            # Check if device_fingerprint column exists
            has_fingerprint = False
            try:
                query_db('SELECT device_fingerprint FROM user_sessions LIMIT 1')
                has_fingerprint = True
            except sqlite3.OperationalError:
                # If column doesn't exist, skip fingerprint validation
                return True

            if not has_fingerprint:
                return True

            session = query_db(
                'SELECT device_fingerprint FROM user_sessions WHERE session_key = ?',
                [session_key],
                one=True
            )

            if not session:
                return False

            stored_fingerprint = session.get('device_fingerprint')

            # If either fingerprint is None, allow the session (backward compatibility)
            if stored_fingerprint is None or device_fingerprint is None:
                return True

            # Compare fingerprints
            return stored_fingerprint == device_fingerprint

        except Exception as e:
            current_app.logger.error(f"Ошибка проверки fingerprint: {e}")
            # Fail open for this security feature (better UX with some security reduction)
            return True

    @staticmethod
    def validate_ip_anomalies(session_key,ip_class_hash):
        # Check if our table has ip_network_hash column
        db = get_db()
        has_ip_hash = False
        try:
            query_db('SELECT ip_network_hash FROM user_sessions LIMIT 1')
            has_ip_hash = True
        except sqlite3.OperationalError:
            try:
                db.execute('ALTER TABLE user_sessions ADD COLUMN ip_network_hash TEXT')
                commit_db()
                has_ip_hash = True
            except:
                return

        if has_ip_hash:
            # Get current stored hash
            session = query_db(
                'SELECT ip_network_hash FROM user_sessions WHERE session_key = ?',
                [session_key],
                one=True
            )

            if not session:
                return

            stored_hash = session['ip_network_hash']

            # If we don't have a stored hash yet, store it
            if not stored_hash:
                db.execute(
                    'UPDATE user_sessions SET ip_network_hash = ? WHERE session_key = ?',
                    [ip_class_hash, session_key]
                )
                commit_db()
                return

        return stored_hash

    @staticmethod
    def validate_token_usage_patterns(session_key):
        db = get_db()
        has_columns = False
        try:
            query_db('SELECT activity_times FROM user_sessions LIMIT 1')
            has_columns = True
        except sqlite3.OperationalError:
            try:
                # Add JSON column for storing recent activity times
                db.execute('ALTER TABLE user_sessions ADD COLUMN activity_times TEXT')
                commit_db()
                has_columns = True
            except:
                return

        if has_columns:
            # Get current activity times
            session = query_db(
                'SELECT activity_times FROM user_sessions WHERE session_key = ?',
                [session_key],
                one=True
            )

            if not session:
                return

            # Update activity times (keep last 20)
            now = datetime.now(timezone.utc).timestamp()
            activity_times = []

            if session['activity_times']:
                try:
                    activity_times = json.loads(session['activity_times'])
                except:
                    activity_times = []

            # Add current time
            activity_times.append(now)

            # Keep only last 20
            if len(activity_times) > 20:
                activity_times = activity_times[-20:]

            # Check for anomalies in access patterns
            suspicious = False
            suspicious_count = 0
            if len(activity_times) >= 5:
                # Check for unusually rapid access
                sorted_times = sorted(activity_times)
                for i in range(1, len(sorted_times)):
                    time_diff = sorted_times[i] - sorted_times[i - 1]
                    if time_diff < 0.5:  # Unusually rapid requests (less than 0.5 sec apart)
                        suspicious_count += 1

                if suspicious_count >= 3:  # Multiple suspiciously rapid requests
                    current_app.logger.warning(f"Unusual request timing pattern for session {session_key[:8]}")
                    return suspicious == True

            # Save updated activity times
            db.execute(
                'UPDATE user_sessions SET activity_times = ? WHERE session_key = ?',
                [json.dumps(activity_times), session_key]
            )
            commit_db()

    @staticmethod
    def validate_session_activity(session_key):
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
                # Сессия слишком долго неактивна
                db.execute('UPDATE user_sessions SET state = "expired" WHERE session_key = ?', [session_key])
                commit_db()
                return False

            return True

        except Exception as e:
            current_app.logger.error(f"Ошибка валидации активности: {e}")
            return False

    @staticmethod
    def validate_session(session_key, user_id):
        session = query_db(
            'SELECT * FROM user_sessions WHERE session_key = ? AND user_id = ? AND state = "active"',
            [session_key, user_id],
            one=True
        )
        return session is not None

    @staticmethod
    def validate_session_key(session_key, device_fingerprint=None):
        """Расширенная проверка сессионного ключа с поддержкой fingerprint устройства"""
        try:
            now = datetime.now(timezone.utc).isoformat()
            session = query_db(
                'SELECT * FROM user_sessions WHERE session_key = ? AND expires_at > ? AND state = "active"',
                [session_key, now],
                one=True
            )

            if not session:
                return False

            # Check fingerprint if provided
            if device_fingerprint:
                try:
                    # Check if device_fingerprint column exists before validation
                    has_fingerprint_column = False
                    try:
                        query_db('SELECT device_fingerprint FROM user_sessions LIMIT 1')
                        has_fingerprint_column = True
                    except sqlite3.OperationalError:
                        # If column doesn't exist, skip fingerprint check
                        pass

                    if has_fingerprint_column:
                        stored_fingerprint = session.get('device_fingerprint')

                        # If stored fingerprint exists, validate match
                        if stored_fingerprint is not None:
                            if stored_fingerprint != device_fingerprint:
                                current_app.logger.warning(f"Session fingerprint mismatch for session {session_key}")
                                return False
                except Exception as fingerprint_error:
                    current_app.logger.error(f"Error checking fingerprint: {fingerprint_error}")
                    # Continue with other validations - don't fail just for fingerprint

            # Также проверяем активность
            return TokenBlacklist.validate_session_activity(session_key)
        except Exception as e:
            current_app.logger.error(f"Ошибка проверки сессионного ключа: {e}")
            return False

    @staticmethod
    def delete_session_key(session_key):
        db = get_db()
        try:
            if session_key:
                db.execute('DELETE FROM user_sessions WHERE session_key = ?', [session_key])
                commit_db()
        except Exception as e:
            current_app.logger.error(f"Ошибка удаления сессионного ключа: {e}")
            return False

    @staticmethod
    def clear_expired_sessions():
        """Очистить просроченные сессии"""
        now = datetime.now(timezone.utc).isoformat()
        db = get_db()
        try:
            db.execute('DELETE FROM user_sessions WHERE expires_at < ?', [now])
            commit_db()
        except sqlite3.Error as e:
            current_app.logger.error(f"Ошибка очистки просроченных сессий: {e}")