# backend/models/security.py
import json
import hashlib
import sqlite3
from datetime import datetime, timezone
from flask import current_app, request

from backend.models.base import get_db, query_db, commit_db


class SecurityMonitor:
    """
    Security Monitor handles advanced security features:
    - Request pattern analysis
    - IP network change detection
    - Session counter for parallel access detection
    - Anomaly detection in session usage
    """

    @staticmethod
    def ensure_column_exists(table, column_name, column_def="TEXT"):
        """
        Helper method to ensure a column exists in a table

        Args:
            table (str): Table name
            column_name (str): Column name to check/add
            column_def (str): Column definition (default: TEXT)

        Returns:
            bool: True if column exists or was added, False otherwise
        """
        db = get_db()
        try:
            # Check if column exists
            query_db(f'SELECT {column_name} FROM {table} LIMIT 1')
            return True
        except sqlite3.OperationalError:
            # Column doesn't exist, try to add it
            try:
                db.execute(f'ALTER TABLE {table} ADD COLUMN {column_name} {column_def}')
                commit_db()
                return True
            except sqlite3.OperationalError as e:
                current_app.logger.error(f"Couldn't add {column_name} to {table}: {e}")
                return False

    @staticmethod
    def track_request_counter(session_key):
        """
        Increment the request counter for a session and check for suspicious activity

        Args:
            session_key (str): The session key to track

        Returns:
            tuple: (success, suspicious) - indicates success and if suspicious activity detected
        """
        db = get_db()
        try:
            # Ensure counter columns exist
            counter_exists = SecurityMonitor.ensure_column_exists('user_sessions', 'request_counter',
                                                                  'INTEGER DEFAULT 0')
            timestamp_exists = SecurityMonitor.ensure_column_exists('user_sessions', 'last_counter_update')

            if not counter_exists or not timestamp_exists:
                return False, None

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

                # If counter increased too rapidly, flag as suspicious
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
            current_app.logger.error(f"Error tracking request counter: {e}")
            return False, None

    @staticmethod
    def get_ip_network_hash(ip_address):
        """
        Generate a hash of the IP network (not the full IP) for change detection
        This preserves privacy while still allowing network-level change detection

        Args:
            ip_address (str): Full IP address

        Returns:
            str or None: Hash of the network portion or None if invalid
        """
        try:
            if '.' in ip_address:  # IPv4
                parts = ip_address.split('.')
                if len(parts) >= 3:
                    # Para redes privadas (10.x.x.x, 172.16-31.x.x, 192.168.x.x) incluir más octetos
                    first_octet = int(parts[0])
                    if (first_octet == 10 or
                            (first_octet == 172 and 16 <= int(parts[1]) <= 31) or
                            (first_octet == 192 and int(parts[1]) == 168)):
                        # Para redes privadas, usamos 3 octetos para mejor precisión
                        network_class = f"{parts[0]}.{parts[1]}.{parts[2]}"
                    else:
                        # Para IPs públicas, mantenemos 2 octetos
                        network_class = f"{parts[0]}.{parts[1]}"

                    # Añadimos el User-Agent al hash para mejorar la singularidad
                    user_agent = request.headers.get('User-Agent', '')
                    hash_input = f"{network_class}|{user_agent}"
                    return hashlib.sha256(hash_input.encode()).hexdigest()

            elif ':' in ip_address:  # IPv6
                parts = ip_address.split(':')
                if len(parts) >= 4:
                    network_class = ':'.join(parts[:4])
                    # También añadimos User-Agent aquí
                    user_agent = request.headers.get('User-Agent', '')
                    hash_input = f"{network_class}|{user_agent}"
                    return hashlib.sha256(hash_input.encode()).hexdigest()
            return None
        except Exception as e:
            current_app.logger.error(f"Error generating IP network hash: {e}")
            return None

    @staticmethod
    def check_network_change(session_key, ip_address, strict_mode=False):
        """
        Check if the network has changed significantly from previous requests
        With fix for empty/null values and different levels of strictness

        Args:
            session_key (str): The session key to check
            ip_address (str): Current IP address
            strict_mode (bool): If True, even minor network changes trigger protection

        Returns:
            tuple: (success, changed) - indicates success and if network changed
        """
        try:
            # Generate network hash
            ip_class_hash = SecurityMonitor.get_ip_network_hash(ip_address)
            if not ip_class_hash:
                return False, None

            # Ensure column exists
            has_ip_hash = SecurityMonitor.ensure_column_exists('user_sessions', 'ip_network_hash')
            if not has_ip_hash:
                return False, None

            # Get current stored hash
            session = query_db(
                'SELECT ip_network_hash FROM user_sessions WHERE session_key = ?',
                [session_key],
                one=True
            )

            if not session:
                return False, None

            db = get_db()

            # Fix: Check if the column exists in the result and if value is not None
            stored_hash = None
            if 'ip_network_hash' in session:
                stored_hash = session['ip_network_hash']

            # If we don't have a stored hash yet, store it
            if not stored_hash:
                db.execute(
                    'UPDATE user_sessions SET ip_network_hash = ? WHERE session_key = ?',
                    [ip_class_hash, session_key]
                )
                commit_db()
                return True, False

            # Check if hash has changed
            if stored_hash != ip_class_hash:
                current_app.logger.warning(f"Network change detected for session {session_key[:8]}")
                return True, True

            return True, False
        except Exception as e:
            current_app.logger.error(f"Error checking network change: {e}")
            return False, None

    @staticmethod
    def track_activity_pattern(session_key):
        """
        Track and analyze activity patterns for anomaly detection
        With fix for empty/null activity_times

        Args:
            session_key (str): The session key to track

        Returns:
            tuple: (success, suspicious) - indicates if operation succeeded and if pattern is suspicious
        """
        db = get_db()
        try:
            # Ensure activity_times column exists
            has_column = SecurityMonitor.ensure_column_exists('user_sessions', 'activity_times')
            if not has_column:
                return False, None

            # Get current activity times
            session = query_db(
                'SELECT activity_times FROM user_sessions WHERE session_key = ?',
                [session_key],
                one=True
            )

            if not session:
                return False, None

            # Update activity times (keep last 20)
            now = datetime.now(timezone.utc).timestamp()
            activity_times = []

            # Fix: Check if the column exists in the result and if value is not None/empty
            activity_times_data = None
            if 'activity_times' in session:
                activity_times_data = session['activity_times']

            if activity_times_data:
                try:
                    activity_times = json.loads(activity_times_data)
                    # Ensure we got a list back
                    if not isinstance(activity_times, list):
                        activity_times = []
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
                    suspicious = True

            # Save updated activity times
            db.execute(
                'UPDATE user_sessions SET activity_times = ? WHERE session_key = ?',
                [json.dumps(activity_times), session_key]
            )
            commit_db()

            return True, suspicious
        except Exception as e:
            current_app.logger.error(f"Error tracking activity pattern: {e}")
            return False, None

    @staticmethod
    def perform_comprehensive_checks(session_key, ip_address=None, request_path=None):
        """
        Perform all security checks and return a comprehensive security status

        Args:
            session_key (str): The session key to check
            ip_address (str, optional): Current IP address
            request_path (str, optional): Current request path for context

        Returns:
            dict: Security status with individual check results
        """
        result = {
            'success': True,
            'session_valid': True,
            'suspicious_activity': False,
            'network_changed': False,
            'rapid_requests': False,
            'risk_level': 'low'
        }

        # Track request counter
        counter_success, suspicious_counter = SecurityMonitor.track_request_counter(session_key)
        if not counter_success:
            result['success'] = False
        if suspicious_counter:
            result['suspicious_activity'] = True
            result['rapid_requests'] = True
            result['risk_level'] = 'medium'

        # Check network changes if IP provided
        if ip_address:
            network_success, network_changed = SecurityMonitor.check_network_change(session_key, ip_address)
            if not network_success:
                result['success'] = False
            if network_changed:
                result['network_changed'] = True
                result['risk_level'] = 'high'

        # Track activity patterns
        pattern_success, suspicious_pattern = SecurityMonitor.track_activity_pattern(session_key)
        if not pattern_success:
            result['success'] = False
        if suspicious_pattern:
            result['suspicious_activity'] = True
            # Increase risk level if already suspicious
            if result['risk_level'] != 'low':
                result['risk_level'] = 'high'
            else:
                result['risk_level'] = 'medium'

        # If we're on a sensitive path, increase risk assessment
        if request_path:
            sensitive_paths = ['/api/user/update', '/api/settings', '/api/admin']
            if any(request_path.startswith(path) for path in sensitive_paths) and result['risk_level'] != 'low':
                result['risk_level'] = 'high'

        return result