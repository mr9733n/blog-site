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

        Args:
            session_key (str): The session key to check
            ip_address (str): Current IP address
            strict_mode (bool): If True, even minor network changes trigger protection

        Returns:
            tuple: (success, changed) - indicates success and if network changed
        """

        def _check_network():
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

            # Get stored hash value safely
            stored_hash = None
            if 'ip_network_hash' in session:
                stored_hash = session['ip_network_hash']

            # If we don't have a stored hash yet, store it and continue
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

        # Use the secure handler to ensure proper error handling
        success, changed = SecurityMonitor.secure_handler(
            _check_network,
            default_value=(False, True),  # Default to (failed, changed=True) for fail-closed
            operation_name="network change detection"
        )

        # If operation failed but we're in strict mode, treat as changed
        if not success and strict_mode:
            return False, True

        return success, changed

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

    @staticmethod
    def secure_handler(func, *args, default_value=False, operation_name="security operation", **kwargs):
        """
        A wrapper for security-critical functions to ensure proper error handling and logging

        Args:
            func: The function to execute
            *args: Arguments to pass to the function
            default_value: The default value to return on error (usually False for fail-closed)
            operation_name: Name of the operation for logging
            **kwargs: Keyword arguments to pass to the function

        Returns:
            The result of the function call, or default_value on error
        """
        try:
            return func(*args, **kwargs)
        except Exception as e:
            current_app.logger.error(f"Security error in {operation_name}: {e}")
            # Return the default value (typically False for fail-closed)
            return default_value


    @staticmethod
    def analyze_user_sessions(user_id):
        """
        Analyze all active sessions for a user to detect potential session hijacking

        Args:
            user_id (int): The user ID to analyze

        Returns:
            dict: Analysis results with anomalies and risk assessment
        """
        try:
            # Get all active sessions for the user
            sessions = query_db(
                '''SELECT session_key, last_activity, ip_network_hash, 
                      device_fingerprint, activity_times, created_at, state
                   FROM user_sessions 
                   WHERE user_id = ? AND state = "active"''',
                [user_id]
            )

            if not sessions:
                return {"success": True, "active_sessions": 0, "anomalies": []}

            # Convert sqlite3.Row objects to dictionaries
            sessions = [dict(session) for session in sessions]

            # Initialize results
            result = {
                "success": True,
                "active_sessions": len(sessions),
                "anomalies": [],
                "suspicious_sessions": [],
                "risk_level": "low"
            }

            # Check for multiple simultaneous active sessions
            if len(sessions) > 1:
                result["anomalies"].append({
                    "type": "multiple_sessions",
                    "description": f"User has {len(sessions)} active sessions"
                })

                # If more than 3 sessions, consider it suspicious
                if len(sessions) > 3:
                    result["risk_level"] = "medium"

            # Analyze network diversity
            ip_hashes = set()
            fingerprints = set()

            for session in sessions:
                if session.get('ip_network_hash'):
                    ip_hashes.add(session['ip_network_hash'])
                if session.get('device_fingerprint'):
                    fingerprints.add(session['device_fingerprint'])

            # If too many different networks or devices, flag as suspicious
            if len(ip_hashes) > 2:
                result["anomalies"].append({
                    "type": "network_diversity",
                    "description": f"User has sessions from {len(ip_hashes)} different networks"
                })
                result["risk_level"] = "high"

            if len(fingerprints) > 2:
                result["anomalies"].append({
                    "type": "device_diversity",
                    "description": f"User has sessions from {len(fingerprints)} different devices"
                })
                result["risk_level"] = "high"

            # Analyze activity patterns for each session
            for i, session in enumerate(sessions):
                session_anomalies = []

                # Check if session has activity times
                if session.get('activity_times'):
                    try:
                        # Parse activity times JSON
                        import json
                        activity_times = json.loads(session['activity_times'])

                        # Skip if not enough data points
                        if isinstance(activity_times, list) and len(activity_times) >= 5:
                            # Check for unusual activity patterns
                            sorted_times = sorted(activity_times)
                            suspicious_count = 0

                            for j in range(1, len(sorted_times)):
                                time_diff = sorted_times[j] - sorted_times[j - 1]
                                if time_diff < 0.2:  # Unusually rapid requests
                                    suspicious_count += 1

                            if suspicious_count >= 3:
                                session_anomalies.append("unusual_request_timing")
                                result["risk_level"] = "high"
                    except Exception as e:
                        current_app.logger.error(f"Error analyzing activity times: {e}")

                # Check for other anomalies in this session
                if session_anomalies:
                    result["suspicious_sessions"].append({
                        "session_key": session['session_key'][:8] + "...",  # Truncate for display
                        "anomalies": session_anomalies
                    })

            return result
        except Exception as e:
            current_app.logger.error(f"Error analyzing user sessions: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def detect_session_hijacking(user_id=None, session_key=None):
        """
        Real-time detection of potential session hijacking attempts

        Args:
            user_id (int, optional): User ID to check
            session_key (str, optional): Specific session key to check

        Returns:
            dict: Detection results with confidence score and evidence
        """
        result = {
            "detected": False,
            "confidence": 0,
            "evidence": [],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        try:
            # Determine which sessions to analyze
            if session_key:
                # Analyze specific session
                session = query_db(
                    '''SELECT user_id, session_key, last_activity, ip_network_hash, 
                          device_fingerprint, activity_times, created_at, state, request_counter
                       FROM user_sessions 
                       WHERE session_key = ?''',
                    [session_key],
                    one=True
                )

                if not session:
                    return result

                user_id = session['user_id']
                sessions = [session]
            elif user_id:
                # Get all active sessions for this user
                sessions = query_db(
                    '''SELECT user_id, session_key, last_activity, ip_network_hash, 
                          device_fingerprint, activity_times, created_at, state, request_counter
                       FROM user_sessions 
                       WHERE user_id = ? AND state = "active"''',
                    [user_id]
                )
            else:
                return result

            # Check for hijacking signals

            # 1. Check for rapid IP network changes within the same session
            for session in sessions:
                # Get recent IP changes for this session
                ip_changes = query_db(
                    '''SELECT * FROM security_events 
                       WHERE session_key = ? AND event_type = 'ip_change' 
                       ORDER BY timestamp DESC LIMIT 10''',
                    [session['session_key']]
                )

                if len(ip_changes) >= 3:
                    result["detected"] = True
                    result["confidence"] += 40
                    result["evidence"].append({
                        "type": "rapid_ip_changes",
                        "session_key": session['session_key'][:8] + "...",
                        "changes_count": len(ip_changes)
                    })

            # 2. Check for simultaneous activity from different locations
            # This is a strong indicator of session hijacking
            if user_id and len(sessions) > 1:
                # Get unique network hashes
                network_hashes = set()
                for session in sessions:
                    if session.get('ip_network_hash'):
                        network_hashes.add(session['ip_network_hash'])

                # If activity from multiple networks in short timeframe
                if len(network_hashes) > 1:
                    # Check if activities overlap in time
                    recent_activities = []
                    for session in sessions:
                        if session.get('last_activity'):
                            last_activity = datetime.fromisoformat(session['last_activity'].replace('Z', '+00:00'))
                            recent_activities.append({
                                "session_key": session['session_key'],
                                "network": session.get('ip_network_hash'),
                                "timestamp": last_activity
                            })

                    # Sort by timestamp
                    recent_activities.sort(key=lambda x: x['timestamp'])

                    # Check for overlapping activity
                    for i in range(1, len(recent_activities)):
                        prev_activity = recent_activities[i - 1]
                        curr_activity = recent_activities[i]

                        # If different networks and activities close in time (< 5 min)
                        time_diff = (curr_activity['timestamp'] - prev_activity['timestamp']).total_seconds()
                        if prev_activity['network'] != curr_activity['network'] and time_diff < 300:
                            result["detected"] = True
                            result["confidence"] += 70
                            result["evidence"].append({
                                "type": "simultaneous_activity",
                                "locations": len(network_hashes),
                                "time_window_seconds": time_diff
                            })

            # 3. Check for unusual activity patterns within a session
            for session in sessions:
                if session.get('activity_times'):
                    try:
                        import json
                        activity_times = json.loads(session['activity_times'])

                        if isinstance(activity_times, list) and len(activity_times) >= 5:
                            # Detect unusual patterns like precise timing intervals
                            intervals = []
                            sorted_times = sorted(activity_times)

                            for i in range(1, len(sorted_times)):
                                intervals.append(sorted_times[i] - sorted_times[i - 1])

                            # Check if intervals are suspiciously consistent (bot-like)
                            if len(intervals) >= 3:
                                import statistics
                                # Calculate variance of intervals
                                variance = statistics.variance(intervals) if len(intervals) > 1 else 0

                                # Extremely low variance suggests automated requests
                                if 0 < variance < 0.01:
                                    result["detected"] = True
                                    result["confidence"] += 50
                                    result["evidence"].append({
                                        "type": "automated_requests",
                                        "session_key": session['session_key'][:8] + "...",
                                        "variance": variance
                                    })
                    except Exception as e:
                        current_app.logger.error(f"Error analyzing activity patterns: {e}")

            # Adjust final confidence based on admin status
            if User.is_admin(user_id) and result["confidence"] > 0:
                # Increase confidence for admin accounts
                result["confidence"] = min(95, result["confidence"] * 1.5)
                result["evidence"].append({
                    "type": "admin_account",
                    "description": "Target is an admin account (higher risk)"
                })

            return result
        except Exception as e:
            current_app.logger.error(f"Error detecting session hijacking: {e}")
            return {
                "detected": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }


    @staticmethod
    def record_security_event(user_id, session_key, event_type, request_path=None, response_code=None, details=None):
        """
        Record a security-related event for audit and monitoring

        Args:
            user_id (int): User ID associated with the event
            session_key (str): Session key associated with the event
            event_type (str): Type of security event (e.g., 'ip_change', 'suspicious_activity')
            request_path (str, optional): API path being accessed
            response_code (int, optional): HTTP response code
            details (dict, optional): Additional event details as JSON-serializable dict

        Returns:
            bool: True if event was recorded successfully, False otherwise
        """
        try:
            db = get_db()

            # Ensure security_events table exists
            db.execute('''
                CREATE TABLE IF NOT EXISTS security_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    session_key TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    request_path TEXT,
                    response_code INTEGER,
                    details TEXT,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            ''')

            # Current timestamp
            now = datetime.now(timezone.utc).isoformat()

            # Convert details to JSON if provided
            details_json = None
            if details:
                try:
                    import json
                    details_json = json.dumps(details)
                except:
                    details_json = str(details)

            # Record the event
            db.execute(
                '''INSERT INTO security_events 
                   (user_id, session_key, event_type, request_path, response_code, details, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?, ?)''',
                [
                    user_id,
                    session_key,
                    event_type,
                    request_path,
                    response_code,
                    details_json,
                    now
                ]
            )
            commit_db()

            # Log to application log as well
            current_app.logger.info(f"Security event recorded: {event_type} for user {user_id}")

            return True
        except Exception as e:
            current_app.logger.error(f"Error recording security event: {e}")
            return False


    @staticmethod
    def get_security_events(user_id=None, session_key=None, event_type=None, limit=100):
        """
        Get security events for analysis

        Args:
            user_id (int, optional): Filter by User ID
            session_key (str, optional): Filter by session key
            event_type (str, optional): Filter by event type
            limit (int, optional): Maximum number of events to return

        Returns:
            list: List of security events as dictionaries
        """
        try:
            # Build query conditions
            conditions = []
            params = []

            if user_id:
                conditions.append("user_id = ?")
                params.append(user_id)

            if session_key:
                conditions.append("session_key = ?")
                params.append(session_key)

            if event_type:
                conditions.append("event_type = ?")
                params.append(event_type)

            # Build the query
            query = "SELECT * FROM security_events"

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            query += " ORDER BY timestamp DESC"

            if limit:
                query += f" LIMIT {limit}"

            # Execute the query
            events = query_db(query, params)

            # Convert to dictionaries
            return [dict(event) for event in events] if events else []
        except Exception as e:
            current_app.logger.error(f"Error getting security events: {e}")
            return []