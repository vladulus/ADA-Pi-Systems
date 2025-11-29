import time
import jwt
import requests
from functools import wraps
from flask import request, jsonify

# ------------------------------------------------------------
# CONFIGURATION
# ------------------------------------------------------------

# JWT Secret from adasystems.uk (you'll need to sync this)
# For now, we'll validate by calling adasystems.uk API
AUTH_API_URL = "https://www.adasystems.uk/api"

# Cache validated tokens to reduce API calls (5 minute cache)
token_cache = {}
TOKEN_CACHE_DURATION = 300  # 5 minutes

# ------------------------------------------------------------
# JWT VALIDATION VIA ADASYSTEMS.UK API
# ------------------------------------------------------------

def validate_jwt_with_api(token):
    """
    Validate JWT token by calling adasystems.uk API.
    Returns user data if valid, None if invalid.
    """
    # Check cache first
    cache_key = token[:50]  # Use first 50 chars as cache key
    if cache_key in token_cache:
        cached_data, cached_time = token_cache[cache_key]
        if time.time() - cached_time < TOKEN_CACHE_DURATION:
            return cached_data
    
    try:
        response = requests.post(
            f"{AUTH_API_URL}/auth/validate",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                # Cache the result
                user_data = result.get('data', {})
                token_cache[cache_key] = (user_data, time.time())
                return user_data
        
        return None
    except Exception as e:
        print(f"Token validation error: {e}")
        return None


def decode_jwt_locally(token, secret_key):
    """
    Decode JWT token locally if you have the secret key.
    This is faster but requires syncing the JWT_SECRET from adasystems.uk.
    """
    try:
        payload = jwt.decode(token, secret_key, algorithms=["HS256"])
        return payload
    except Exception as e:
        print(f"JWT decode error: {e}")
        return None


# ------------------------------------------------------------
# LOCAL/REMOTE AUTH DECISION
# ------------------------------------------------------------

def is_local_request():
    """
    Returns True if the request comes from:
      - 127.0.0.1
      - ::1
      - localhost
    """
    host = request.remote_addr
    return host in ["127.0.0.1", "::1", "localhost"]


# ------------------------------------------------------------
# DECORATOR FOR ENDPOINT PROTECTION
# ------------------------------------------------------------

def require_auth(f):
    """
    Protect API endpoints with JWT authentication from adasystems.uk.
    Local requests (127.0.0.1) bypass authentication.
    Remote requests must provide valid JWT token.
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        if is_local_request():
            # Local UI → no auth needed
            return f(*args, **kwargs)

        # Remote → JWT required
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "missing_auth", "message": "Authorization header required"}), 401

        token = auth_header.split(" ", 1)[1]
        
        # Validate token via adasystems.uk API
        user_data = validate_jwt_with_api(token)
        
        if not user_data:
            return jsonify({"error": "invalid_token", "message": "Invalid or expired token"}), 401

        # Attach user data to request for use in endpoint
        request.user = user_data
        
        return f(*args, **kwargs)

    return wrapper


# ------------------------------------------------------------
# PERMISSION CHECKING
# ------------------------------------------------------------

def has_permission(permission_name):
    """
    Check if authenticated user has a specific permission.
    Usage in endpoint:
        if not has_permission('edit_settings'):
            return jsonify({"error": "forbidden"}), 403
    """
    if is_local_request():
        return True  # Local requests have all permissions
    
    if not hasattr(request, 'user'):
        return False
    
    user = request.user
    permissions = user.get('permissions', [])
    return permission_name in permissions


def has_role(role_name):
    """
    Check if authenticated user has a specific role.
    Usage:
        if not has_role('super-admin'):
            return jsonify({"error": "forbidden"}), 403
    """
    if is_local_request():
        return True  # Local requests have all roles
    
    if not hasattr(request, 'user'):
        return False
    
    user = request.user
    return user.get('role') == role_name


# ------------------------------------------------------------
# HTTP RESPONSE HELPERS
# ------------------------------------------------------------

def ok(data=None):
    return jsonify({"status": "ok", "data": data})


def fail(msg):
    return jsonify({"status": "error", "message": msg}), 400
