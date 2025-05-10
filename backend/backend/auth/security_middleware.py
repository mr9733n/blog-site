# backend/auth/security_middleware.py

import time
import hashlib
from flask import request, jsonify, current_app, g
from flask_jwt_extended import verify_jwt_in_request, get_jwt

from backend.models.session import SessionManager
from backend.models.security import SecurityMonitor


def apply_security_middleware(app):
    """
    Apply global security middleware to the Flask application

    Args:
        app: Flask application instance
    """

    @app.before_request
    def global_security_check():
        """Global security middleware for all routes"""
        try:
            # Skip for non-API routes and OPTIONS requests
            if not request.path.startswith('/api/') or request.method == 'OPTIONS':
                return None

            # Skip for login and register routes
            if request.path.endswith('/login') or request.path.endswith('/register'):
                return None

            # Skip for public API endpoints
            public_endpoints = [
                '/api/posts',
                '/api/images/data/'
            ]

            if any(request.path.startswith(endpoint) for endpoint in public_endpoints) and request.method == 'GET':
                return None

            # Verify JWT is present and valid
            try:
                verify_jwt_in_request()
                jwt_data = get_jwt()
            except Exception as e:
                # Let the standard JWT handling take care of this
                return None

            # Get session information
            session_key = jwt_data.get('session_key')
            user_id = jwt_data.get('sub')

            # Skip detailed checks if we don't have session data
            if not session_key or not user_id:
                return None

            # Basic security checks for all routes

            # 1. Track access patterns for security monitoring
            SecurityMonitor.track_request_counter(session_key)
            SecurityMonitor.track_activity_pattern(session_key)

            # 2. Record request timestamp and path for activity monitoring
            g.request_start_time = time.time()
            g.user_id = user_id
            g.session_key = session_key

            # 3. Check for extremely rapid access (potential automated attacks)
            _, suspicious_counter = SecurityMonitor.track_request_counter(session_key)
            if suspicious_counter:
                g.suspicious_activity = True
                g.suspicious_reason = "rapid_requests"

            # 4. Log sensitive operation access attempts for auditing
            sensitive_paths = ['/api/admin', '/api/user/update', '/api/settings']
            if any(request.path.startswith(path) for path in sensitive_paths):
                # Get client info for logging
                client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
                if client_ip and ',' in client_ip:
                    client_ip = client_ip.split(',')[0].strip()

                user_agent = request.headers.get('User-Agent', 'Unknown')

                # Log access attempt to sensitive resource
                current_app.logger.info(
                    f"Sensitive resource access: {request.path} by user {user_id} " +
                    f"from {client_ip} using {user_agent[:40]}..."
                )

            # Continue with the request - security validation will be handled by
            # specific route decorators
            return None
        except Exception as e:
            current_app.logger.error(f"Error in global security middleware: {e}")
            # Let the request continue to be handled by normal error handlers
            return None

    @app.after_request
    def log_suspicious_activity(response):
        """Log suspicious activity and update security records"""
        try:
            # Skip for non-API routes
            if not request.path.startswith('/api/'):
                return response

            # Check if suspicious activity was detected
            suspicious = getattr(g, 'suspicious_activity', False)

            if suspicious and hasattr(g, 'user_id') and hasattr(g, 'session_key'):
                reason = getattr(g, 'suspicious_reason', 'unknown')

                # Log suspicious activity
                current_app.logger.warning(
                    f"Suspicious activity detected: {reason} for user {g.user_id} " +
                    f"on {request.path} (session: {g.session_key[:8]})"
                )

                # Record security event
                SecurityMonitor.record_security_event(
                    user_id=g.user_id,
                    session_key=g.session_key,
                    event_type=f"suspicious_{reason}",
                    request_path=request.path,
                    response_code=response.status_code
                )

            # Calculate and log request processing time for unusually slow requests
            if hasattr(g, 'request_start_time'):
                processing_time = time.time() - g.request_start_time
                if processing_time > 1.0:  # Log slow requests (> 1 second)
                    current_app.logger.warning(
                        f"Slow request: {request.path} took {processing_time:.2f}s " +
                        f"(status: {response.status_code})"
                    )
        except Exception as e:
            current_app.logger.error(f"Error in response middleware: {e}")

        return response