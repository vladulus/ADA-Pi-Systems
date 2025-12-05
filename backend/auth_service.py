from typing import Optional, Dict, Any

from ada_auth_client import ADAAuthClient, UserSession


class AuthService:
    """
    Serviciu central de autentificare pentru ADA-Pi.
    Folosește ADAAuthClient (care vorbește cu ADA Systems - Laravel).
    """

    _instance: Optional["AuthService"] = None

    @classmethod
    def instance(cls) -> "AuthService":
        if cls._instance is None:
            cls._instance = AuthService()
        return cls._instance

    def __init__(self):
        self.client = ADAAuthClient()
        self.session: Optional[UserSession] = None

    def is_authenticated(self) -> bool:
        return self.session is not None

    def login(self, email: str, password: str, device_id: str = "ada-pi-001") -> Dict[str, Any]:
        """
        Face login la ADA Systems și reține sesiunea.
        Returnează un dict cu info utile pentru UI (user + features).
        Aruncă Exception dacă login-ul eșuează.
        """
        session = self.client.login(email, password, device_id)
        self.session = session

        features = self.client.dashboard_features()

        return {
            "user": {
                "id": session.id,
                "name": session.name,
                "email": session.email,
                "role": session.role,
                "permissions": session.permissions,
            },
            "can_access_dashboard": session.can_access_dashboard(),
            "features": features,
            "token": session.token,
            "token_type": session.token_type,
            "expires_in": session.expires_in,
        }

    def logout(self):
        """
        Deocamdată doar șterge sesiunea locală.
        (Dacă vrei, mai târziu putem chema și /api/auth/logout.)
        """
        self.session = None

    def can_access_dashboard(self) -> bool:
        return self.session is not None and self.session.can_access_dashboard()

    def features(self) -> Dict[str, bool]:
        if not self.session:
            return {}
        return self.session.dashboard_features()

    def auth_header(self) -> Dict[str, str]:
        """
        Header Authorization pentru alte request-uri către ADA Systems.
        """
        return self.client.get_auth_header()
