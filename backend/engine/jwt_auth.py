import time
import jwt
from logger import logger
from config_manager import load_config

# --------------------------------------------------------------------
# IMPORTANT:
# A production device should rotate keys periodically and use
# asymmetric signing (RS256). For now, HS256 is sufficient.
# --------------------------------------------------------------------

DEFAULT_SECRET = "ada-pi-default-secret"


def get_secret_key():
    """
    Load or generate the JWT secret from config.
    """

    config = load_config()

    if "jwt_secret" not in config:
        logger.log("WARN", "No JWT secret found in config. Using default temporary key.")
        return DEFAULT_SECRET

    return config["jwt_secret"]


# --------------------------------------------------------------------

def create_jwt(payload, expire_minutes=60):
    """
    Create a JWT token signed with HS256.
    """

    secret = get_secret_key()

    payload = {
        **payload,
        "exp": int(time.time()) + expire_minutes * 60
    }

    return jwt.encode(payload, secret, algorithm="HS256")


# --------------------------------------------------------------------

def validate_jwt(auth_header):
    """
    Validate incoming JWT Authorization header.
    Format expected:
        Authorization: Bearer <token>
    Returns True if valid, False otherwise.
    """

    if not auth_header:
        return False

    if not auth_header.startswith("Bearer "):
        return False

    token = auth_header.replace("Bearer ", "").strip()
    secret = get_secret_key()

    try:
        jwt.decode(token, secret, algorithms=["HS256"])
        return True
    except Exception as e:
        logger.log("WARN", f"JWT validation failed: {e}")
        return False
