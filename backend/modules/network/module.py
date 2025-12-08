#!/usr/bin/env python3

import time

class NetworkModule:
    """
    Stores all network-related runtime data.

    Structure:
    {
        "active": "wifi" | "ethernet" | "modem" | "none",
        "wifi": {...},
        "ethernet": {...},
        "modem_data": bool,
        "ip": "x.x.x.x",
        "failover_active": bool,
        "updated": <timestamp>
    }
    """

    def __init__(self):
        self.state = {
            "active": "none",
            "wifi": {
                "connected": False,
                "ssid": None,
                "bssid": None,
                "strength": None,
                "frequency": None,
                "ip": None,
            },
            "ethernet": {
                "connected": False,
                "ip": None,
            },
            "modem_data": False,
            "ip": None,
            "failover_active": False,
            "updated": time.time(),
        }

    # ------------------------------------------------------------
    def update(self, new_data: dict):
        """
        Merge worker-provided data into module state.
        """
        # wifi info
        if "wifi" in new_data:
            self.state["wifi"].update(new_data["wifi"])

        # ethernet info
        if "ethernet" in new_data:
            self.state["ethernet"].update(new_data["ethernet"])

        # active interface
        if "active" in new_data:
            self.state["active"] = new_data["active"]

        # primary IP
        if "ip" in new_data:
            self.state["ip"] = new_data["ip"]

        # modem data connection
        if "modem_data" in new_data:
            self.state["modem_data"] = new_data["modem_data"]

        # failover status
        if "failover_active" in new_data:
            self.state["failover_active"] = new_data["failover_active"]

        # timestamp
        self.state["updated"] = time.time()

    # ------------------------------------------------------------
    def read_status(self):
        """
        Returns full network state for API, QML, cloud upload.
        """
        return self.state.copy()
