# backend/auth/middlewares.py
import secrets
import hashlib
import time
from flask import request, jsonify, make_response, g, current_app
from flask_jwt_extended import get_jwt

from backend.models.user import User
from backend.models.token_blacklist import TokenBlacklist
from backend.models.session import SessionManager
from backend.models.security import SecurityMonitor

from backend.routes.admin import admin_security_check


# ============================================================================
# Basic Authentication Middlewares
# ============================================================================

def register_auth_middlewares(app):
    """
    Register all authentication-related middlewares with the Flask app

    Args:
        app: Flask application instance
    """

    # don't apply admin security check globally
    # app.before_request(admin_security_check)
    # Register all middleware functions with the app
    app.before_request(log_request_info)
    app.before_request(check_user_blocked)
    app.before_request(check_csrf)
    app.before_request(rotate_csrf_tokens)
    app.before_request(update_session_activity)

    # Security enhancement middlewares
    app.before_request(detect_network_changes)
    app.before_request(analyze_request_patterns)
    app.before_request(validate_sensitive_operations)

    # Response middlewares
    app.after_request(add_csrf_token_to_response)

    # Register JWT token blocklist loader
    jwt = app.extensions.get('flask-jwt-extended')
    if jwt:
        jwt.token_in_blocklist_loader(check_if_token_revoked)

    return app


def log_request_info():
    """Log basic request information for debugging"""
    if 'Cookie' in request.headers:
        current_app.logger.debug(f"DEBUG: Auth header received: {request.headers['Cookie']}...")
    else:
        current_app.logger.warning("DEBUG: No Authorization header in request")
        current_app.logger.debug(f"DEBUG: Available headers: {list(request.headers.keys())}")


def check_user_blocked():
    """Check if the user account is blocked"""
    # Check only API requests that aren't authentication
    if not request.path.startswith('/api/') or request.path in ['/api/login', '/api/register']:
        return

    try:
        # Extract and validate user ID from JWT
        jwt_data = get_jwt()
        user_id = jwt_data.get('sub')

        if user_id and User.is_user_blocked(user_id):
            return jsonify({"msg": "Ваш аккаунт заблокирован администратором"}), 403
    except Exception:
        # Silently continue if we can't get JWT data - other auth checks will handle this
        pass


def check_csrf():
    """Validate CSRF state matches between cookie and header"""
    # Skip for OPTIONS requests (CORS preflight)
    if request.method == 'OPTIONS':
        return

    # Only check for non-GET, non-OPTIONS requests
    if request.method not in ['POST', 'PUT', 'DELETE', 'PATCH']:
        return

    # Allow login without CSRF (first request)
    if request.path.endswith('/login') or request.path.endswith('/register'):
        return

    # Get CSRF tokens from different locations
    csrf_from_cookie = request.cookies.get('csrf_state')
    csrf_from_header = request.headers.get('X-CSRF-STATE')

    # Detailed logging for debugging
    if not csrf_from_cookie and not csrf_from_header:
        current_app.logger.warning(f"CSRF validation failed: No CSRF token in cookie or header")
        return jsonify({"msg": "CSRF-защита: отсутствует токен"}), 403

    if not csrf_from_cookie:
        current_app.logger.warning(f"CSRF validation failed: No CSRF token in cookie")
        return jsonify({"msg": "CSRF-защита: отсутствует токен в cookie"}), 403

    if not csrf_from_header:
        current_app.logger.warning(f"CSRF validation failed: No CSRF token in header")
        return jsonify({"msg": "CSRF-защита: отсутствует токен в заголовке"}), 403

    # Validate tokens match
    if csrf_from_cookie != csrf_from_header:
        current_app.logger.warning(f"CSRF validation failed: Token mismatch")
        return jsonify({"msg": "CSRF-защита: несоответствие токенов"}), 403

    # Check if token is expired (if using timestamp format)
    if ':' in csrf_from_cookie:
        try:
            token_parts = csrf_from_cookie.split(':')
            if len(token_parts) == 2:
                timestamp = int(token_parts[1])
                # Check if token is extremely old (1 day+) - potential stolen token
                if time.time() - timestamp > 86400:  # 24 hours
                    current_app.logger.warning(f"CSRF validation failed: Token too old")
                    return jsonify({"msg": "CSRF-защита: устаревший токен"}), 403
        except Exception as e:
            current_app.logger.error(f"Error parsing CSRF timestamp: {e}")
            # Continue if we can't parse timestamp


def rotate_csrf_tokens():
    """Rotate CSRF tokens periodically for enhanced security"""
    # Only check for GET requests to API endpoints
    if not request.path.startswith('/api/') or request.method != 'GET':
        return

    csrf_state = request.cookies.get('csrf_state')
    if not csrf_state:
        return

    # Check if we need to rotate based on timestamp in token
    rotate = False
    try:
        # If the csrf_state follows format "token:timestamp"
        if ':' in csrf_state:
            token_parts = csrf_state.split(':')
            if len(token_parts) == 2:
                timestamp = int(token_parts[1])
                # Rotate every 5 minutes
                if time.time() - timestamp > 300:
                    rotate = True
    except:
        # If we can't parse, default to not rotating
        pass

    if rotate:
        # Get current user and session if available
        try:
            jwt_data = get_jwt()
            session_key = jwt_data.get('session_key')

            if session_key:
                # Generate new CSRF state with timestamp
                new_csrf_state = f"{secrets.token_hex(16)}:{int(time.time())}"

                # Update session with new CSRF state
                SessionManager.update_session(session_key, csrf_state=new_csrf_state)

                # Set the new cookie (will be in response)
                token_lifetime = current_app.config.get('JWT_ACCESS_TOKEN_EXPIRES', 1800)
                resp = make_response()
                resp.set_cookie(
                    'csrf_state',
                    new_csrf_state,
                    max_age=token_lifetime,
                    secure=current_app.config.get('JWT_COOKIE_SECURE', False),
                    httponly=False,
                    samesite=current_app.config.get('JWT_COOKIE_SAMESITE', 'Lax')
                )
                return resp
        except:
            # Continue with the request if rotation fails
            pass


def update_session_activity():
    """Update last activity timestamp for the current session"""
    if not request.path.startswith('/api/'):
        return

    try:
        jwt_data = get_jwt()
        user_id = jwt_data.get('sub')

        if user_id:
            SessionManager.update_activity(user_id)
    except:
        # Continue if we can't update activity
        pass


# ============================================================================
# Security Enhancement Middlewares
# ============================================================================

def detect_network_changes():
    """Detect significant network changes that might indicate session hijacking"""
    # Only check for modifying operations
    if not request.path.startswith('/api/') or request.method not in ['POST', 'PUT', 'DELETE', 'PATCH']:
        return

    try:
        # Get JWT data
        jwt_data = get_jwt()
        session_key = jwt_data.get('session_key')

        if not session_key:
            return

        # Get real client IP (taking into account proxies)
        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if client_ip and ',' in client_ip:
            # If multiple IPs in X-Forwarded-For, take the first one (client IP)
            client_ip = client_ip.split(',')[0].strip()

        _, network_changed = SecurityMonitor.check_network_change(session_key, client_ip)

        # Store result in flask g object for other middlewares to use
        g.network_changed = network_changed

        # For sensitive operations, apply stricter security
        if network_changed:
            sensitive_paths = ['/api/user/update', '/api/settings/token-settings', '/api/admin']
            if any(request.path.startswith(path) for path in sensitive_paths):
                return jsonify({
                    "msg": "Обнаружено изменение сети. Для этой операции требуется повторная аутентификация.",
                    "code": "REVERIFY_REQUIRED"
                }), 428  # Precondition Required
    except:
        # Continue if we can't check network changes
        pass

def analyze_request_patterns():
    """Analyze request patterns for unusual activity"""
    if not request.path.startswith('/api/') or request.method == 'OPTIONS':
        return

    try:
        # Get JWT data
        jwt_data = get_jwt()
        session_key = jwt_data.get('session_key')

        if not session_key:
            return

        # Track request counter and check for parallel access
        _, suspicious_counter = SecurityMonitor.track_request_counter(session_key)

        # Track and analyze request timing patterns
        _, suspicious_pattern = SecurityMonitor.track_activity_pattern(session_key)

        # Store results in flask g object
        g.suspicious_activity = suspicious_counter or suspicious_pattern

        # For sensitive operations, apply stricter security
        if g.suspicious_activity:
            sensitive_paths = ['/api/user/update', '/api/admin']
            if any(request.path.startswith(path) for path in sensitive_paths):
                return jsonify({
                    "msg": "Обнаружена подозрительная активность. Для продолжения требуется повторная аутентификация.",
                    "code": "SUSPICIOUS_ACTIVITY"
                }), 428  # Precondition Required
    except:
        # Continue if analysis fails
        pass


def validate_sensitive_operations():
    """Apply extra security validations for sensitive operations"""
    # Only check for modifying operations
    if request.method not in ['POST', 'PUT', 'DELETE', 'PATCH']:
        return

    # Define paths that modify sensitive user data
    sensitive_paths = [
        '/api/user/update',
        '/api/settings/token-settings',
        '/api/admin/users',
    ]

    # Check if the current path is sensitive
    is_sensitive = False
    for path in sensitive_paths:
        if request.path.startswith(path):
            is_sensitive = True
            break

    # For sensitive paths, enforce fingerprint validation
    if is_sensitive:
        try:
            jwt_data = get_jwt()
            session_key = jwt_data.get('session_key')

            # Get device fingerprint
            device_fingerprint = request.headers.get('X-Device-Fingerprint')

            # If both are present, validate fingerprint match
            if session_key and device_fingerprint:
                fingerprint_match = SessionManager.validate_fingerprint(session_key, device_fingerprint)

                if not fingerprint_match:
                    current_app.logger.warning(f"Sensitive operation blocked: fingerprint mismatch on {request.path}")
                    return jsonify({
                        "msg": "Операция заблокирована из соображений безопасности. Пожалуйста, повторите вход в систему."
                    }), 403
        except:
            # If we can't get JWT data, continue to regular auth checks
            pass


# ============================================================================
# Response Middleware
# ============================================================================

def add_csrf_token_to_response(response):
    """Add CSRF token to response headers"""
    try:
        # Find CSRF token in cookies
        csrf_token = None
        for cookie_name in ['csrf_access_token', 'csrf_refresh_token']:
            if cookie_name in request.cookies:
                csrf_token = request.cookies.get(cookie_name)
                break

        # Add token to response header if found
        if csrf_token:
            response.headers['X-CSRF-TOKEN'] = csrf_token
        else:
            # If not found in cookies, try to get from JWT
            try:
                jwt_data = get_jwt()
                if 'csrf' in jwt_data:
                    response.headers['X-CSRF-TOKEN'] = jwt_data['csrf']
            except:
                # If we can't get JWT data, just continue
                pass
    except Exception as e:
        # Log error but don't interrupt response
        current_app.logger.debug(f"Could not add CSRF token to response: {str(e)}")

    return response


# ============================================================================
# JWT Handlers
# ============================================================================

def check_if_token_revoked(jwt_header, jwt_payload):
    """Check if a token is revoked or otherwise invalid"""
    jti = jwt_payload.get('jti')
    session_key = jwt_payload.get('session_key')
    user_id = jwt_payload.get('sub')

    # Extract token binding claims
    token_fp_hash = jwt_payload.get('fp_hash')
    token_ip_net = jwt_payload.get('ip_net')
    token_ua_hash = jwt_payload.get('ua_hash')

    # Get real client IP (taking into account proxies)
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if client_ip and ',' in client_ip:
        # If multiple IPs in X-Forwarded-For, take the first one (client IP)
        client_ip = client_ip.split(',')[0].strip()

    # Get device fingerprint from request
    device_fingerprint = request.headers.get('X-Device-Fingerprint')

    # Calculate current request fingerprint hash
    current_fp_hash = None
    if device_fingerprint:
        current_fp_hash = hashlib.sha256(device_fingerprint.encode()).hexdigest()

    # Calculate current IP network hash
    current_ip_net = None
    if client_ip:
        current_ip_net = SecurityMonitor.get_ip_network_hash(client_ip)

    # Calculate current User-Agent hash
    current_ua_hash = hashlib.sha256(request.headers.get('User-Agent', '').encode()).hexdigest()[:16]

    try:
        # Basic token validation
        is_blacklisted = TokenBlacklist.is_token_blacklisted(jti, user_id)

        # Session validations
        session_invalid = session_key and not SessionManager.check_session_valid(session_key)
        session_user_mismatch = session_key and not SessionManager.validate_session(session_key, user_id)

        # КРИТИЧЕСКИ ВАЖНОЕ ИЗМЕНЕНИЕ: Всегда проверять fingerprint, если он есть в токене
        device_mismatch = False
        if token_fp_hash and current_fp_hash:
            # Строгое сравнение отпечатков устройств
            if token_fp_hash != current_fp_hash:
                device_mismatch = True
                current_app.logger.warning(f"🔍 Device fingerprint hash mismatch for user {user_id}")
                # Немедленно добавляем событие безопасности
                SecurityMonitor.record_security_event(
                    user_id=user_id,
                    session_key=session_key,
                    event_type="fingerprint_mismatch",
                    request_path=request.path,
                    details={"token_hash": token_fp_hash, "request_hash": current_fp_hash[:8] + "..."}
                )
                # Для критических операций или админ-маршрутов всегда отклоняем запрос при несовпадении
                admin_paths = ['/api/admin']
                sensitive_paths = ['/api/user/update', '/api/settings/token-settings']
                if any(request.path.startswith(path) for path in admin_paths + sensitive_paths):
                    return True  # Блокируем токен для чувствительных маршрутов

        # IP network validation - более строгая проверка
        network_mismatch = False
        if token_ip_net and current_ip_net and token_ip_net != current_ip_net:
            # Для админ-путей всегда проверяем сеть
            admin_paths = ['/api/admin']
            sensitive_paths = ['/api/user/update', '/api/settings/token-settings']

            is_sensitive_path = any(request.path.startswith(path) for path in admin_paths + sensitive_paths)
            if is_sensitive_path:
                network_mismatch = True
                current_app.logger.warning(f"🚨 IP network binding mismatch for user {user_id}")
                # Записываем событие безопасности
                SecurityMonitor.record_security_event(
                    user_id=user_id,
                    session_key=session_key,
                    event_type="network_mismatch",
                    request_path=request.path,
                    details={"token_network": token_ip_net[:8] + "...", "request_network": current_ip_net[:8] + "..."}
                )

        # User-Agent validation - более строгая проверка
        ua_mismatch = False
        if token_ua_hash and token_ua_hash != current_ua_hash:
            # Для админ-маршрутов проверяем User-Agent
            if any(request.path.startswith('/api/admin') for path in ['/api/admin']):
                ua_mismatch = True
                current_app.logger.warning(f"🌐 User-Agent mismatch for user {user_id}")
                # Записываем событие безопасности
                SecurityMonitor.record_security_event(
                    user_id=user_id,
                    session_key=session_key,
                    event_type="user_agent_mismatch",
                    request_path=request.path
                )

        # Log security issues
        if is_blacklisted:
            current_app.logger.warning(f"🔒 Blocked token with jti={jti} attempted use")
        if session_invalid:
            current_app.logger.warning(f"🔑 Invalid session key: {session_key}")
        if session_user_mismatch:
            current_app.logger.warning(f"👤 Session-user mismatch: {session_key} for user {user_id}")
        if device_mismatch:
            current_app.logger.warning(f"🔍 Device mismatch for user {user_id}")

        # Для админ-маршрутов применяем более строгую валидацию
        is_admin_route = request.path.startswith('/api/admin')
        if is_admin_route:
            admin_validation_failed = device_mismatch or network_mismatch or ua_mismatch
            if admin_validation_failed:
                current_app.logger.warning(f"🛡️ ADMIN ACCESS BLOCKED: Device binding validation failed")
                return True  # Блокируем токен

        # Отклоняем токен, если не прошла любая проверка
        return (is_blacklisted or session_invalid or session_user_mismatch or
                device_mismatch or network_mismatch or ua_mismatch)
    except Exception as e:
        current_app.logger.error(f"Error checking token validity: {e}")
        # В случае ошибки отклоняем токен для безопасности
        return True