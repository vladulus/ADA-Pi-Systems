import time
import jwt
import socket
from functools import wraps
from flask import request, jsonify
from config_manager import load_config, save_config

# Default JWT secret (can be overridden in config)
SECRET_KEY = "ADA_PI_DEFAULT_SECRET"


def load_secret():
    cfg = load_config()
    return cfg.get("jwt_secret", SECRET_KEY)


# ------------------------------------------------------------
# JWT CREATE
# ------------------------------------------------------------

def create_jwt(payload, expire_hours=24):
    payload = dict(payload)
    payload["exp"] = int(time.time() + expire_hours * 3600)
    token = jwt.encode(payload, load_secret(), algorithm="HS256")
    return token


# ------------------------------------------------------------
# JWT VERIFY
# ------------------------------------------------------------

def verify_jwt(token):
    try:
        data = jwt.decode(token, load_secret(), algorithms=["HS256"])
        return data
    except:
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
    @wraps(f)
    def wrapper(*args, **kwargs):
        if is_local_request():
            # local UI → no auth needed
            return f(*args, **kwargs)

        # remote → JWT required
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "missing_auth"}), 401

        token = auth_header.split(" ", 1)[1]
        data = verify_jwt(token)
        if not data:
            return jsonify({"error": "invalid_token"}), 401

        return f(*args, **kwargs)

    return wrapper


# ------------------------------------------------------------
# HTTP RESPONSE HELPERS
# ------------------------------------------------------------

def ok(data=None):
    return jsonify({"status": "ok", "data": data})


def fail(msg):
    return jsonify({"status": "error", "message": msg}), 400
