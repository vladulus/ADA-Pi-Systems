#!/usr/bin/env python3
# ADA-Pi Network Worker
# Uses NetworkManager DBus engine for real WiFi/Ethernet status
# Includes modem failover when WiFi/Ethernet unavailable

import time
import subprocess
from logger import logger
from ipc.router import router
from engine.networkmanager_dbus import NMEngine
from config_manager import load_config


class NetworkWorker:
    """
    Provides:
      - WiFi status (SSID, signal, frequency, IP)
      - Ethernet status (link + IP)
      - Modem failover when primary connections fail
      - Combined "active interface" logic
      - Publishes IPC: 'network_update'
    """

    INTERVAL = 3  # seconds
    FAILOVER_CHECK_INTERVAL = 30  # check internet every 30s
    FAILOVER_RETRY_DELAY = 60  # wait 60s before retrying modem connect

    def __init__(self, network_module, modem_module=None):
        self.net = network_module
        self.modem = modem_module
        self.running = True
        self.engine = NMEngine()
        
        # Failover state
        self._failover_active = False
        self._last_failover_check = 0
        self._last_modem_attempt = 0
        self._consecutive_failures = 0
        
        # Load config for failover settings
        self._load_failover_config()
        
        # Subscribe to modem data connection events
        router.subscribe("modem_data_connected", self._on_modem_data_changed)
        router.subscribe("config_changed", self._reload_config)

        logger.log("INFO", "NetworkWorker initialized (DBus mode + failover)")

    def _load_failover_config(self):
        """Load failover configuration."""
        cfg = load_config()
        modem_cfg = cfg.get("modem", {})
        
        self.failover_enabled = modem_cfg.get("failover_enabled", True)
        self.failover_apn = modem_cfg.get("apn", "")
        
        logger.log("INFO", f"Failover enabled: {self.failover_enabled}, APN: {self.failover_apn or '(not set)'}")

    def _reload_config(self, data=None):
        """Reload config when changed."""
        self._load_failover_config()

    def _on_modem_data_changed(self, data):
        """Handle modem data connection state change."""
        connected = data.get("connected", False)
        if connected:
            self._failover_active = True
            logger.log("INFO", "NetworkWorker: modem failover now active")
        else:
            self._failover_active = False
            logger.log("INFO", "NetworkWorker: modem failover deactivated")

    # ------------------------------------------------------------
    def start(self):
        logger.log("INFO", "NetworkWorker started.")

        while self.running:
            try:
                self._update_status()
                self._check_failover()
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

        # Check modem data status
        modem_data = False
        modem_ip = None
        if self.modem:
            modem_status = self.modem.read_status()
            modem_data = modem_status.get("data_connected", False)
            modem_ip = modem_status.get("data_ip")

        active_iface = self._determine_active_interface(wifi, eth, modem_data)

        status = {
            "active": active_iface,
            "wifi": wifi,
            "ethernet": eth,
            "modem_data": modem_data,
            "ip": self._primary_ip(wifi, eth, modem_ip),
            "failover_active": self._failover_active,
        }

        self.net.update(status)
        router.publish("network_update", status)

    # ------------------------------------------------------------
    # FAILOVER LOGIC
    # ------------------------------------------------------------
    def _check_failover(self):
        """Check if we need to failover to modem or back to WiFi."""
        if not self.failover_enabled or not self.failover_apn:
            return

        now = time.time()
        
        # Only check every FAILOVER_CHECK_INTERVAL seconds
        if now - self._last_failover_check < self.FAILOVER_CHECK_INTERVAL:
            return
        
        self._last_failover_check = now

        wifi = self.engine.wifi_status()
        eth = self.engine.ethernet_status()
        
        wifi_ok = wifi.get("connected", False)
        eth_ok = eth.get("connected", False)
        
        # If WiFi or Ethernet is connected, check actual internet
        if wifi_ok or eth_ok:
            if self._has_internet():
                # Internet works, disable failover if active
                if self._failover_active:
                    logger.log("INFO", "NetworkWorker: primary connection restored, disabling modem failover")
                    router.publish("modem_disconnect_request", {})
                    self._failover_active = False
                self._consecutive_failures = 0
                return
            else:
                # WiFi/Eth connected but no internet
                self._consecutive_failures += 1
                logger.log("WARN", f"NetworkWorker: connected but no internet (failures: {self._consecutive_failures})")
        else:
            # No WiFi or Ethernet at all
            self._consecutive_failures += 1
            logger.log("WARN", f"NetworkWorker: no primary connection (failures: {self._consecutive_failures})")

        # Need failover after 2 consecutive failures
        if self._consecutive_failures >= 2 and not self._failover_active:
            # Don't spam modem connect attempts
            if now - self._last_modem_attempt < self.FAILOVER_RETRY_DELAY:
                return
            
            self._last_modem_attempt = now
            logger.log("INFO", "NetworkWorker: initiating modem failover")
            router.publish("modem_connect_request", {})

    def _has_internet(self):
        """Check if we have actual internet connectivity."""
        # Try multiple endpoints for reliability
        test_hosts = [
            ("8.8.8.8", 53),      # Google DNS
            ("1.1.1.1", 53),      # Cloudflare DNS
        ]
        
        for host, port in test_hosts:
            try:
                result = subprocess.run(
                    ["ping", "-c", "1", "-W", "2", host],
                    capture_output=True, timeout=5
                )
                if result.returncode == 0:
                    return True
            except:
                continue
        
        return False

    # ------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------

    def _determine_active_interface(self, wifi, eth, modem_data=False):
        """
        Priority:
            1) Ethernet (if connected with internet)
            2) WiFi (if connected with internet)
            3) Modem (if data connected)
            4) None
        """

        if eth.get("connected"):
            return "ethernet"

        if wifi.get("connected"):
            return "wifi"

        if modem_data:
            return "modem"

        return "none"

    # ------------------------------------------------------------

    def _primary_ip(self, wifi, eth, modem_ip=None):
        """
        Return IP address based on active interface.
        """
        if eth.get("connected") and eth.get("ip"):
            return eth["ip"]

        if wifi.get("connected") and wifi.get("ip"):
            return wifi["ip"]

        if modem_ip:
            return modem_ip

        return None
