"""
ADA-Pi Settings Handler

Receives settings from cloud and applies them to local modules.
Tracks settings version to avoid reapplying unchanged settings.
"""

import os
import json
from logger import logger
from config_manager import load_config, save_config
from ipc.router import router

SETTINGS_VERSION_FILE = "/var/lib/ada_pi/settings_version"


class SettingsHandler:
    """
    Handles settings sync from cloud to local Pi.
    
    - Compares settings version to avoid unnecessary updates
    - Applies settings to config.json
    - Notifies modules of changes via IPC
    """

    def __init__(self):
        self._local_version = self._load_local_version()

    # ----------------------------------------------------------------
    # VERSION TRACKING
    # ----------------------------------------------------------------

    def _load_local_version(self) -> int:
        """Load the last applied settings version from disk."""
        try:
            if os.path.exists(SETTINGS_VERSION_FILE):
                with open(SETTINGS_VERSION_FILE, "r") as f:
                    return int(f.read().strip())
        except Exception as e:
            logger.log("WARN", f"SettingsHandler: could not read version file: {e}")
        return 0

    def _save_local_version(self, version: int):
        """Save the current settings version to disk."""
        try:
            os.makedirs(os.path.dirname(SETTINGS_VERSION_FILE), exist_ok=True)
            with open(SETTINGS_VERSION_FILE, "w") as f:
                f.write(str(version))
            self._local_version = version
        except Exception as e:
            logger.log("ERROR", f"SettingsHandler: could not save version: {e}")

    # ----------------------------------------------------------------
    # MAIN APPLY METHOD
    # ----------------------------------------------------------------

    def apply_settings(self, settings_payload: dict) -> bool:
        """
        Apply settings from server if version is newer.
        
        Args:
            settings_payload: {
                "version": <unix_timestamp>,
                "data": { ... settings dict ... }
            }
        
        Returns:
            True if settings were applied, False otherwise.
        """
        if not settings_payload:
            return False

        server_version = settings_payload.get("version", 0)
        settings_data = settings_payload.get("data", {})

        # Check if we need to update
        if server_version <= self._local_version:
            logger.log("DEBUG", f"SettingsHandler: settings up to date (local={self._local_version}, server={server_version})")
            return False

        logger.log("INFO", f"SettingsHandler: applying new settings (version {server_version})")

        try:
            # Load current config
            cfg = load_config()

            # Apply each section
            self._apply_cloud(cfg, settings_data.get("cloud", {}))
            self._apply_wifi(cfg, settings_data.get("wifi", {}))
            self._apply_bluetooth(cfg, settings_data.get("bluetooth", {}))
            self._apply_modem(cfg, settings_data.get("modem", {}))
            self._apply_gps(cfg, settings_data.get("gps", {}))
            self._apply_obd(cfg, settings_data.get("obd", {}))
            self._apply_ups(cfg, settings_data.get("ups", {}))
            self._apply_fan(cfg, settings_data.get("fan", {}))
            self._apply_system(cfg, settings_data.get("system", {}))

            # Save updated config
            save_config(cfg)

            # Save version
            self._save_local_version(server_version)

            # Notify all modules that config changed
            router.publish("config_changed", {"version": server_version})

            logger.log("INFO", "SettingsHandler: settings applied successfully")
            return True

        except Exception as e:
            logger.log("ERROR", f"SettingsHandler: failed to apply settings: {e}")
            return False

    # ----------------------------------------------------------------
    # SECTION APPLIERS
    # ----------------------------------------------------------------

    def _apply_cloud(self, cfg: dict, cloud: dict):
        """Apply cloud upload settings."""
        if not cloud:
            return
        
        if "cloud" not in cfg:
            cfg["cloud"] = {}
        
        if cloud.get("upload_url"):
            cfg["cloud"]["upload_url"] = cloud["upload_url"]
        if cloud.get("logs_url"):
            cfg["cloud"]["logs_url"] = cloud["logs_url"]

    def _apply_wifi(self, cfg: dict, wifi: dict):
        """Apply WiFi settings - actual connection handled by NetworkManager."""
        if not wifi:
            return
        
        if "wifi" not in cfg:
            cfg["wifi"] = {}
        
        cfg["wifi"]["enabled"] = wifi.get("enabled", True)
        cfg["wifi"]["ssid"] = wifi.get("ssid", "")
        cfg["wifi"]["password"] = wifi.get("password", "")
        cfg["wifi"]["dhcp"] = wifi.get("dhcp", True)
        cfg["wifi"]["ip"] = wifi.get("ip", "")
        cfg["wifi"]["gateway"] = wifi.get("gateway", "")
        cfg["wifi"]["dns"] = wifi.get("dns", "")

        # Notify network module to reconfigure WiFi
        if wifi.get("ssid"):
            router.publish("wifi_config_changed", wifi)

    def _apply_bluetooth(self, cfg: dict, bt: dict):
        """Apply Bluetooth settings."""
        if not bt:
            return
        
        if "bluetooth" not in cfg:
            cfg["bluetooth"] = {}
        
        cfg["bluetooth"]["enabled"] = bt.get("enabled", True)
        cfg["bluetooth"]["discoverable"] = bt.get("discoverable", False)
        cfg["bluetooth"]["name"] = bt.get("name", "")

        router.publish("bluetooth_config_changed", bt)

    def _apply_modem(self, cfg: dict, modem: dict):
        """Apply modem/cellular settings."""
        if not modem:
            return
        
        if "modem" not in cfg:
            cfg["modem"] = {}
        
        cfg["modem"]["apn"] = modem.get("apn", "")
        cfg["modem"]["username"] = modem.get("username", "")
        cfg["modem"]["password"] = modem.get("password", "")
        cfg["modem"]["network_mode"] = modem.get("network_mode", "auto")
        cfg["modem"]["roaming"] = modem.get("roaming", False)

        router.publish("modem_config_changed", modem)

    def _apply_gps(self, cfg: dict, gps: dict):
        """Apply GPS settings."""
        if not gps:
            return
        
        if "gps" not in cfg:
            cfg["gps"] = {}
        
        cfg["gps"]["enabled"] = gps.get("enabled", True)
        cfg["gps"]["update_rate"] = gps.get("update_rate", 1)

        router.publish("gps_config_changed", gps)

    def _apply_obd(self, cfg: dict, obd: dict):
        """Apply OBD settings."""
        if not obd:
            return
        
        if "obd" not in cfg:
            cfg["obd"] = {}
        
        cfg["obd"]["port"] = obd.get("port", "auto")
        cfg["obd"]["protocol"] = obd.get("protocol", "auto")
        cfg["obd"]["poll_interval"] = obd.get("poll_interval", 2)
        cfg["obd"]["excluded_ports"] = obd.get("excluded_ports", "")

        router.publish("obd_config_changed", obd)

    def _apply_ups(self, cfg: dict, ups: dict):
        """Apply UPS/battery settings."""
        if not ups:
            return
        
        if "ups" not in cfg:
            cfg["ups"] = {}
        
        cfg["ups"]["low_threshold"] = ups.get("low_threshold", 15)
        cfg["ups"]["auto_power_on"] = ups.get("auto_power_on", True)
        cfg["ups"]["shutdown_delay"] = ups.get("shutdown_delay", 30)

        router.publish("ups_config_changed", ups)

    def _apply_fan(self, cfg: dict, fan: dict):
        """Apply fan control settings."""
        if not fan:
            return
        
        if "fan" not in cfg:
            cfg["fan"] = {}
        
        cfg["fan"]["mode"] = fan.get("mode", "auto")
        cfg["fan"]["threshold"] = fan.get("threshold", 50)
        cfg["fan"]["speed"] = fan.get("speed", 100)

        router.publish("fan_config_changed", fan)

    def _apply_system(self, cfg: dict, system: dict):
        """Apply system-wide settings."""
        if not system:
            return
        
        if "system" not in cfg:
            cfg["system"] = {}
        
        cfg["system"]["timezone"] = system.get("timezone", "UTC")
        cfg["system"]["hostname"] = system.get("hostname", "")
        cfg["system"]["auto_update"] = system.get("auto_update", False)
        cfg["system"]["reboot_schedule"] = system.get("reboot_schedule", "disabled")

        # Apply timezone immediately if changed
        tz = system.get("timezone")
        if tz:
            try:
                os.system(f"timedatectl set-timezone {tz} 2>/dev/null || true")
            except:
                pass

        # Apply hostname if changed
        hostname = system.get("hostname")
        if hostname:
            try:
                os.system(f"hostnamectl set-hostname {hostname} 2>/dev/null || true")
            except:
                pass

        router.publish("system_config_changed", system)


# Singleton instance
settings_handler = SettingsHandler()
