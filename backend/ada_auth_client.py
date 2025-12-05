import os
import requests
from dataclasses import dataclass
from typing import List, Optional

# BASE_URL se ia din env: ADA_API_BASE_URL
# Dacă nu e setată variabila, folosește implicit localhost (dev).
BASE_URL = os.getenv("ADA_API_BASE_URL", "http://127.0.0.1:8000")


@dataclass
class UserSession:
    id: int
    name: str
    email: str
    role: str
    permissions: List[str]
    token: str
    token_type: str
    expires_in: int

    def has_permission(self, perm: str) -> bool:
        return perm in self.permissions

    def can_access_dashboard(self) -> bool:
        return "dashboard.access" in self.permissions

    def dashboard_features(self) -> dict:
        perms = set(self.permissions)
        return {
            "gps": "dashboard.gps" in perms,
            "obd": "dashboard.obd" in perms,
            "system": "dashboard.system" in perms,
            "ups": "dashboard.ups" in perms,
            "network": "dashboard.network" in perms,
            "modem": "dashboard.modem" in perms,
            "bluetooth": "dashboard.bluetooth" in perms,
            "tachograph": "dashboard.tachograph" in perms,
            "logs": "dashboard.logs" in perms,
        }


class ADAAuthClient:
    def __init__(self, base_url: str = BASE_URL, timeout: int = 5):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session: Optional[UserSession] = None

    def login(self, username: str, password: str, device_id: str) -> UserSession:
        """
        POST /api/auth/login și construiește un UserSession.
        Acceptă răspunsuri de formă:
        - {"status": "ok", "data": {...}}
        - sau {"success": true, "data": {...}}
        """
        url = f"{self.base_url}/api/auth/login"
        payload = {
            "username": username,
            "password": password,
            "device_id": device_id,
        }

        resp = requests.post(url, json=payload, timeout=self.timeout)
        resp.raise_for_status()

        try:
            data = resp.json()
        except ValueError:
            print("[ADAAuthClient] Invalid JSON from API:")
            print(resp.text)
            raise Exception("Invalid JSON response from API")

        print("[ADAAuthClient] DEBUG JSON from API:", data)

        status = data.get("status")
        success = data.get("success")

        if not ((status == "ok") or (success is True)):
            msg = data.get("message") or "Login failed"
            raise Exception(msg)

        payload = data.get("data") or {}
        token = payload.get("token")
        user = payload.get("user")

        if not token:
            raise Exception("Login failed: no token in response")
        if not user:
            raise Exception("Login failed: no user in response")

        permissions = list(user.get("permissions", []))

        self.session = UserSession(
            id=user["id"],
            name=user["name"],
            email=user["email"],
            role=user.get("role", "user"),
            permissions=permissions,
            token=token,
            token_type=payload.get("token_type", "bearer"),
            expires_in=payload.get("expires_in", 0),
        )

        return self.session

    def get_auth_header(self) -> dict:
        if not self.session:
            return {}
        return {
            "Authorization": f"{self.session.token_type} {self.session.token}"
        }

    def has_permission(self, perm: str) -> bool:
        return self.session is not None and self.session.has_permission(perm)

    def can_access_dashboard(self) -> bool:
        return self.session is not None and self.session.can_access_dashboard()

    def dashboard_features(self) -> dict:
        if not self.session:
            return {}
        return self.session.dashboard_features()
