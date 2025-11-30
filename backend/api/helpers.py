import time
import jwt
import requests
import os
from functools import wraps
from flask import request, jsonify

# ------------------------------------------------------------
# CONFIGURATION
# ------------------------------------------------------------

AUTH_API_URL = "https://www.adasystems.uk/api"
JWT_SECRET_FILE = "/opt/ada-pi/backend/JWT_SECRET"

token_cache = {}
TOKEN_CACHE_DURATION = 300  # 5 minutes

# ------------------------------------------------------------
# SECRET KEY HANDLING
# ------------------------------------------------------------

def load_secret():
    """
    Load local JWT secret (if present).
    If missing, backend will rely on adasystems.uk validation.
    """
    if os.path.exists(JWT_SECRET_FILE):
        with open(JWT_SECRET_FILE, "r") as f:
            return f.read().strip()
    return None


# ------------------------------------------------------------
# JWT LOCAL CREATION
# ------------------------------------------------------------

def create_jwt(payload, expires_in=3600):
    """
    Create a JWT locally using stored secret.
    Only works if JWT_SECRET is available.
    """
    secret = load_secret()
    if not secret:
        raise RuntimeError("JWT_SECRET not found. Cannot create JWT locally.")

    payload = dict(payload)
    payload["exp"] = int(time.time()) + expires_in

    return jwt.encode(payload, secret, algorithm="HS256")


# ------------------------------------------------------------
# JWT LOCAL VERIFICATION
# ------------------------------------------------------------

def verify_jwt(token):
    """
    Verify token locally if secret exists.
    If no secret available → fallback to API validation.
    Returns decoded payload or None.
    """
    secret = load_secret()

    if secret:
        try:
            return jwt.decode(token, secret, algorithms=["HS256"])
        except Exception:
            return None

    # No secret → use API
    return validate_jwt_with_api(token)


# ------------------------------------------------------------
# VALIDATION VIA API (REMOTE)
# ------------------------------------------------------------

def validate_jwt_with_api(token):
    cache_key = token[:50]

    if cache_key in token_cache:
        data, ts = token_cache[cache_key]
        if time.time() - ts < TOKEN_CACHE_DURATION:
            return data

    try:
        resp = requests.post(
            f"{AUTH_API_URL}/auth/validate",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5
        )

        if resp.status_code == 200:
            data = resp.json()
            if data.get("success"):
                user_data = data.get("data", {})
                token_cache[cache_key] = (user_data, time.time())
                return user_data

        return None
    except Exception:
        return None


# ------------------------------------------------------------
# LOCAL / REMOTE RULES
# ------------------------------------------------------------

def is_local_request():
    host = request.remote_addr
    return host in ["127.0.0.1", "::1", "localhost"]


# ------------------------------------------------------------
# AUTH DECORATOR
# ------------------------------------------------------------

def require_auth(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if is_local_request():
            return f(*args, **kwargs)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "missing_auth"}), 401

        token = auth_header.split(" ", 1)[1]

        user_data = verify_jwt(token)
        if not user_data:
            return jsonify({"error": "invalid_token"}), 401

        request.user = user_data
        return f(*args, **kwargs)
    return wrapper


# ------------------------------------------------------------
# PERMISSIONS & ROLES
# ------------------------------------------------------------

def has_permission(name):
    if is_local_request():
        return True
    if not hasattr(request, "user"):
        return False
    return name in request.user.get("permissions", [])


def has_role(name):
    if is_local_request():
        return True
    if not hasattr(request, "user"):
        return False
    return request.user.get("role") == name


# ------------------------------------------------------------
# HTTP UTILITIES
# ------------------------------------------------------------

def ok(data=None):
    return jsonify({"status": "ok", "data": data})


def fail(msg):
    return jsonify({"status": "error", "message": msg}), 400
