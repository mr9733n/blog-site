# Create a new file: backend/services/security_validator.py

import hashlib
import time
from flask import request, jsonify, current_app, g
from flask_jwt_extended import get_jwt, verify_jwt_in_request

from backend.models.session import SessionManager
from backend.models.security import SecurityMonitor
from backend.models.user import User


class SecurityValidator:
    """
    Centralized security validation for consistent enforcement of security policies
    across different routes and controllers.
    """

    @staticmethod
    def validate_request(required_level="standard", admin_required=False):
        """
        Comprehensive security validation for incoming requests

        Args:
            required_level (str): Security level required - "standard", "elevated", or "high"
            admin_required (bool): Whether admin privileges are required

        Returns:
            tuple: (is_valid, response) - Boolean indicating if request is valid and
                  error response if not valid (None if valid)
        """
        try:
            public_endpoints = ['/api/posts', '/api/images/data']
            if any(request.path.startswith(endpoint) for endpoint in public_endpoints) and request.method == 'GET':
                return True, None

            # Skip for OPTIONS requests (CORS preflight)
            if request.method == 'OPTIONS':
                return True, None

            # Get JWT data
            try:
                # This will verify the JWT exists and is valid
                verify_jwt_in_request()
                # After verification, we can safely get the JWT data
                jwt_data = get_jwt()
            except Exception as e:
                current_app.logger.warning(f"JWT validation failed: {e}")
                return False, (jsonify({"msg": "Требуется авторизация"}), 401)

            user_id = jwt_data.get('sub')
            session_key = jwt_data.get('session_key')

            # Check required parameters
            if not user_id or not session_key:
                current_app.logger.warning(f"Missing required JWT claims")
                return False, (jsonify({"msg": "Недостаточно данных для авторизации"}), 401)

            # If admin required, check admin rights
            if admin_required:
                if not User.is_admin(int(user_id)):
                    current_app.logger.warning(f"Admin access attempt by non-admin user: {user_id}")
                    return False, (jsonify({"msg": "Требуются права администратора"}), 403)

            # Security validations based on required level
            # 1. Basic session validation - all levels
            if not SessionManager.check_session_valid(session_key):
                current_app.logger.warning(f"Invalid session: {session_key[:8]} for user {user_id}")
                return False, (jsonify({"msg": "Недействительная сессия"}), 401)

            # 2. User-session match validation - all levels
            if not SessionManager.validate_session(session_key, int(user_id)):
                current_app.logger.warning(f"Session-user mismatch: {session_key[:8]} for user {user_id}")
                return False, (jsonify({"msg": "Несоответствие сессии и пользователя"}), 401)

            # 3. Device fingerprint validation - all levels except basic with fallback
            device_fingerprint = request.headers.get('X-Device-Fingerprint')

            # Validate fingerprint if we have one or if elevated security required
            if device_fingerprint or required_level in ("elevated", "high"):
                if not device_fingerprint:
                    current_app.logger.warning(f"Missing fingerprint for {required_level} security request")
                    return False, (jsonify({"msg": "Требуется идентификатор устройства"}), 401)

                if not SessionManager.validate_fingerprint(session_key, device_fingerprint):
                    current_app.logger.warning(f"Fingerprint mismatch for user {user_id}")
                    return False, (jsonify({"msg": "Несоответствие устройства"}), 403)

            # 4. CSRF token validation for non-GET methods - all levels
            if request.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
                csrf_from_cookie = request.cookies.get('csrf_state')
                csrf_from_header = request.headers.get('X-CSRF-STATE')

                if not csrf_from_cookie or not csrf_from_header:
                    current_app.logger.warning(f"Missing CSRF token for user {user_id}")
                    return False, (jsonify({"msg": "Отсутствует CSRF-токен"}), 403)

                if csrf_from_cookie != csrf_from_header:
                    current_app.logger.warning(f"CSRF token mismatch for user {user_id}")
                    return False, (jsonify({"msg": "Несоответствие CSRF-токенов"}), 403)

            # 5. Token binding validation (device-specific claims) - elevated and high levels
            if required_level in ("elevated", "high"):
                # Get device-binding claims from token
                token_fp_hash = jwt_data.get('fp_hash')
                token_ip_net = jwt_data.get('ip_net')
                token_ua_hash = jwt_data.get('ua_hash')

                # Get current request info for comparison
                client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
                if client_ip and ',' in client_ip:
                    client_ip = client_ip.split(',')[0].strip()

                # Only validate the claims that exist in the token
                if token_fp_hash and device_fingerprint:
                    current_fp_hash = hashlib.sha256(device_fingerprint.encode()).hexdigest()
                    if token_fp_hash != current_fp_hash:
                        current_app.logger.warning(f"Token fingerprint mismatch for user {user_id}")
                        return False, (jsonify({"msg": "Несоответствие токена устройству"}), 403)

                # For high security, also validate network hash
                if required_level == "high" and token_ip_net and client_ip:
                    current_ip_net = SecurityMonitor.get_ip_network_hash(client_ip)
                    if token_ip_net != current_ip_net:
                        current_app.logger.warning(f"Token network mismatch for user {user_id}")
                        return False, (jsonify({"msg": "Несоответствие сети"}), 403)

                # For high security, validate User-Agent hash
                if required_level == "high" and token_ua_hash:
                    current_ua_hash = hashlib.sha256(request.headers.get('User-Agent', '').encode()).hexdigest()[:16]
                    if token_ua_hash != current_ua_hash:
                        current_app.logger.warning(f"Token User-Agent mismatch for user {user_id}")
                        return False, (jsonify({"msg": "Несоответствие браузера"}), 403)

            # 6. Rate limiting and activity pattern analysis - elevated and high levels
            if required_level in ("elevated", "high"):
                # Check for suspicious activity patterns
                _, suspicious_pattern = SecurityMonitor.track_activity_pattern(session_key)
                _, suspicious_counter = SecurityMonitor.track_request_counter(session_key)

                if suspicious_pattern or suspicious_counter:
                    current_app.logger.warning(f"Suspicious activity detected for user {user_id}")

                    # For high security, block immediately
                    if required_level == "high":
                        return False, (jsonify({
                            "msg": "Обнаружена подозрительная активность",
                            "code": "SUSPICIOUS_ACTIVITY"
                        }), 403)

                    # For elevated security, mark in context but allow request
                    g.suspicious_activity = True

            # 7. Session hijacking detection - high security only
            if required_level == "high" and admin_required:
                # Real-time detection of potential session hijacking
                detection_result = SecurityMonitor.detect_session_hijacking(session_key=session_key)

                if detection_result["detected"] and detection_result["confidence"] >= 50:
                    current_app.logger.warning(
                        f"Possible session hijacking detected for admin {user_id} " +
                        f"(confidence: {detection_result['confidence']}%)"
                    )

                    # Log evidence for investigation
                    for evidence in detection_result["evidence"]:
                        current_app.logger.warning(f"Hijacking evidence: {evidence}")

                    # Block access and require re-authentication
                    return False, (jsonify({
                        "msg": "Обнаружена подозрительная активность. Требуется повторная аутентификация.",
                        "code": "SECURITY_THREAT"
                    }), 403)

            # All validations passed
            return True, None
        except Exception as e:
            current_app.logger.error(f"Error in security validation: {e}")
            # Fail closed on any errors
            return False, (jsonify({"msg": "Ошибка проверки безопасности"}), 500)

    @staticmethod
    def validate_admin_access():
        """Validate admin access with high security requirements"""
        return SecurityValidator.validate_request(required_level="high", admin_required=True)

    @staticmethod
    def validate_sensitive_operation():
        """Validate sensitive operations with elevated security requirements"""
        return SecurityValidator.validate_request(required_level="elevated")