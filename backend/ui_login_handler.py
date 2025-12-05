from typing import Any, Dict

from login_bridge import login_with_ada_systems


def handle_ui_login(email: str, password: str, device_id: str = "ada-pi-001") -> Dict[str, Any]:
    """
    Funcție pe care o poate apela UI-ul (QML / WebSocket / REST)
    ca să facă login în ADA Systems.

    Returnează mereu un dict simplu, de genul:

    - succes:
      {
        "ok": True,
        "user": {...},
        "can_access_dashboard": True/False,
        "features": {...}
      }

    - eroare:
      {
        "ok": False,
        "error": "mesaj pentru UI"
      }
    """

    result = login_with_ada_systems(email=email, password=password, device_id=device_id)

    if not result.get("ok"):
        # credențiale greșite, API down, etc.
        return {
            "ok": False,
            "error": result.get("error", "Autentificare eșuată"),
        }

    # dacă nu are acces la dashboard, întoarcem un mesaj clar pentru UI
    if not result["can_access_dashboard"]:
        return {
            "ok": False,
            "error": "Nu ai acces la acest dashboard.",
        }

    # totul ok: user + permisiuni + feature flags
    return {
        "ok": True,
        "user": result["user"],
        "can_access_dashboard": result["can_access_dashboard"],
        "features": result["features"],
        # dacă vrei să le folosești mai târziu:
        "token": result["token"],
        "token_type": result["token_type"],
        "expires_in": result["expires_in"],
    }
