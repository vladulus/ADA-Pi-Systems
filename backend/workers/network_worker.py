#!/usr/bin/env python3
# ADA-Pi Network Worker
# Uses NetworkManager DBus engine for real WiFi/Ethernet status

import time
from logger import logger
from ipc.router import router
from engine.networkmanager_dbus import NMEngine


class NetworkWorker:
    """
    Provides:
      - WiFi status (SSID, signal, frequency, IP)
      - Ethernet status (link + IP)
      - Combined "active interface" logic
      - Publishes IPC: 'network_update'
    """

    INTERVAL = 3  # seconds

    def __init__(self, network_module):
        self.net = network_module
        self.running = True
        self.engine = NMEngine()

        logger.log("INFO", "NetworkWorker initialized (DBus mode)")

    # ------------------------------------------------------------
    def start(self):
        logger.log("INFO", "NetworkWorker started.")

        while self.running:
            try:
                self._update_status()
                time.sleep(self.INTERVAL)

            except Exception as e:
                logger.log("ERROR", f"NetworkWorker crash: {e}")
                time.sleep(2)

    # ------------------------------------------------------------
    def stop(self):
        self.running = False

    # ------------------------------------------------------------
    # MAIN UPDATE LOOP
    # ------------------------------------------------------------
    def _update_status(self):
        wifi = self.engine.wifi_status()
        eth = self.engine.ethernet_status()

        active_iface = self._determine_active_interface(wifi, eth)

        status = {
            "active": active_iface,
            "wifi": wifi,
            "ethernet": eth,
            "ip": self._primary_ip(wifi, eth),
        }

        self.net.update(status)
        router.publish("network_update", status)

    # ------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------

    def _determine_active_interface(self, wifi, eth):
        """
        Priority:
            1) Ethernet
            2) WiFi
            3) Modem (in future)
            4) None
        """

        if eth.get("connected"):
            return "ethernet"

        if wifi.get("connected"):
            return "wifi"

        # In the future we will add:
        # if modem.get("connected"): return "modem"

        return "none"

    # ------------------------------------------------------------

    def _primary_ip(self, wifi, eth):
        """
        Return IP address based on active interface.
        """
        if eth.get("connected") and eth.get("ip"):
            return eth["ip"]

        if wifi.get("connected") and wifi.get("ip"):
            return wifi["ip"]

        return None
