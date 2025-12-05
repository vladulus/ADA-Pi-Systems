from typing import Any, Dict

from auth_service import AuthService


def login_with_ada_systems(email: str, password: str, device_id: str = "ada-pi-001") -> Dict[str, Any]:
    """
    Funcție simplă pe care o poate apela UI-ul (QML / alt layer)
    ca să facă login și să primească tot ce are nevoie într-un dict.

    Returnează:
    {
      "ok": True/False,
      "error": "mesaj" (doar dacă ok=False),
      "user": {...},
      "can_access_dashboard": bool,
      "features": {
          "gps": bool,
          "obd": bool,
          ...
      }
    }
    """
    svc = AuthService.instance()

    try:
        result = svc.login(email=email, password=password, device_id=device_id)
    except Exception as e:
        # Aici poți loga eroarea, dacă vrei
        return {
            "ok": False,
            "error": str(e),
        }

    return {
        "ok": True,
        "user": result["user"],
        "can_access_dashboard": result["can_access_dashboard"],
        "features": result["features"],
        "token": result["token"],
        "token_type": result["token_type"],
        "expires_in": result["expires_in"],
    }


def get_dashboard_guard() -> Dict[str, Any]:
    """
    Helper pe care îl poți apela din orice loc din backend
    ca să știi rapid:
      - dacă are voie în dashboard
      - ce features sunt active
    """
    svc = AuthService.instance()

    return {
        "is_authenticated": svc.is_authenticated(),
        "can_access_dashboard": svc.can_access_dashboard(),
        "features": svc.features(),
    }
