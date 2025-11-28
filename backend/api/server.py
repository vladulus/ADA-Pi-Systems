#!/usr/bin/env python3
# ADA-Pi REST API Server
# Provides secure REST endpoints for all backend modules

import os
import time
import threading

from flask import Flask, request, jsonify
from logger import logger
from config_manager import load_config, save_config
from storage.storage_manager import StorageManager

# Authentication + helpers
from .helpers import (
    require_auth,
    create_jwt,
    ok,
    fail,
    is_local_request
)


# ------------------------------------------------------------
# API FACTORY (called from BackendEngine)
# ------------------------------------------------------------

def create_app(modules, storage, ota_manager):
    import os
    frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend"))
    app = Flask(__name__, static_folder=frontend_dir, static_url_path='/static')
    app.config["JSON_SORT_KEYS"] = False

    # Attach backend objects
    app.modules = modules
    app.storage = storage
    app.ota = ota_manager

    # Load config on startup
    cfg = load_config()
    gps_cfg = cfg.get("gps", {})
    modules["gps"].set_unit_mode(gps_cfg.get("unit_mode", "auto"))

    # ============================================================
    # AUTHENTICATION
    # ============================================================
    @app.post("/api/auth/login")
    def login():
        """
        Remote requests require username/password — local requests do not.
        """
        if is_local_request():
            return ok({"token": None})

        data = request.json or {}
        username = data.get("username", "")
        password = data.get("password", "")

        auth_cfg = load_config().get("auth", {})
        if username != auth_cfg.get("username") or password != auth_cfg.get("password"):
            return fail("invalid_credentials")

        token = create_jwt({"user": username}, expire_hours=24)
        return ok({"token": token})

    # ============================================================
    # SETTINGS — GLOBAL
    # ============================================================
    @app.get("/api/settings")
    @require_auth
    def settings_all():
        return ok(load_config())

    @app.post("/api/settings")
    @require_auth
    def settings_update_all():
        cfg = load_config()
        data = request.json or {}

        for key, value in data.items():
            cfg[key] = value

        save_config(cfg)
        return ok(cfg)

    # ============================================================
    # SETTINGS — SPLIT (API URL, WS URL, Device ID, Cloud, UPS)
    # ============================================================
    @app.post("/api/settings/api_url")
    @require_auth
    def settings_api_url():
        data = request.json or {}
        url = data.get("api_url")
        if not url:
            return fail("missing api_url")

        cfg = load_config()
        cfg["api_url"] = url
        save_config(cfg)
        return ok({"api_url": url})

    @app.post("/api/settings/ws_url")
    @require_auth
    def settings_ws_url():
        data = request.json or {}
        url = data.get("ws_url")
        if not url:
            return fail("missing ws_url")

        cfg = load_config()
        cfg["ws_url"] = url
        save_config(cfg)
        return ok({"ws_url": url})

    @app.post("/api/settings/cloud")
    @require_auth
    def settings_cloud():
        data = request.json or {}
        cfg = load_config()
        cloud = cfg.get("cloud", {})

        cloud["upload_url"] = data.get("upload_url", cloud.get("upload_url", ""))
        cloud["logs_url"] = data.get("logs_url", cloud.get("logs_url", ""))

        cfg["cloud"] = cloud
        save_config(cfg)
        return ok(cloud)

    @app.post("/api/settings/device")
    @require_auth
    def settings_device():
        data = request.json or {}
        dev_id = data.get("device_id")
        if not dev_id:
            return fail("missing device_id")

        cfg = load_config()
        cfg["device_id"] = dev_id
        save_config(cfg)
        return ok({"device_id": dev_id})

    @app.post("/api/settings/ups")
    @require_auth
    def settings_ups():
        data = request.json or {}
        pct = int(data.get("shutdown_pct", -1))
        if pct < 1 or pct > 100:
            return fail("invalid shutdown_pct")

        cfg = load_config()
        cfg.setdefault("ups", {})
        cfg["ups"]["shutdown_pct"] = pct
        save_config(cfg)
        return ok({"shutdown_pct": pct})

    # ============================================================
    # SYSTEM
    # ============================================================
    @app.get("/api/system/info")
    @require_auth
    def system_info():
        return ok(app.modules["system"].read_status())

    @app.post("/api/system/reboot")
    @require_auth
    def system_reboot():
        os.system("sudo reboot")
        return ok({"reboot": True})

    @app.post("/api/system/shutdown")
    @require_auth
    def system_shutdown():
        os.system("sudo shutdown -h now")
        return ok({"shutdown": True})

    # ============================================================
    # UPS
    # ============================================================
    @app.get("/api/ups")
    @require_auth
    def ups_status():
        return ok(app.modules["ups"].read_status())

    # ============================================================
    # FAN
    # ============================================================
    @app.get("/api/fan")
    @require_auth
    def fan_info():
        return ok(app.modules["fan"].read_status())

    @app.post("/api/fan/mode")
    @require_auth
    def fan_mode():
        data = request.json or {}
        mode = data.get("mode")
        if mode not in ["auto", "manual"]:
            return fail("invalid mode")

        if mode == "auto":
            app.modules["fan"].set_auto()

        return ok({"mode": mode})

    @app.post("/api/fan/speed")
    @require_auth
    def fan_speed():
        data = request.json or {}
        speed = int(data.get("speed", -1))
        if speed < 0 or speed > 100:
            return fail("invalid speed")

        app.modules["fan"].set_speed(speed)
        return ok({"speed": speed})

    # ============================================================
    # GPS + NEW UNIT MODE ENDPOINT
    # ============================================================
    @app.get("/api/gps")
    @require_auth
    def gps_status():
        return ok(app.modules["gps"].read_status())

    @app.post("/api/gps/unit")
    @require_auth
    def gps_unit():
        """
        mode = auto / kmh / mph
        """
        data = request.json or {}
        mode = data.get("mode")

        if mode not in ["auto", "kmh", "mph"]:
            return fail("invalid_mode")

        app.modules["gps"].set_unit_mode(mode)

        cfg = load_config()
        cfg.setdefault("gps", {})
        cfg["gps"]["unit_mode"] = mode
        save_config(cfg)

        return ok({"unit_mode": mode})

    # ============================================================
    # OBD
    # ============================================================
    @app.get("/api/obd")
    @require_auth
    def obd_status():
        return ok(app.modules["obd"].read_status())

    @app.post("/api/obd/clear")
    @require_auth
    def obd_clear():
        app.modules["obd"].request_clear = True
        return ok({"clearing": True})

    # ============================================================
    # BLUETOOTH
    # ============================================================
    @app.get("/api/bluetooth")
    @require_auth
    def bt_status():
        return ok(app.modules["bluetooth"].read_status())

    @app.get("/api/bluetooth/paired")
    @require_auth
    def bt_paired():
        return ok(app.modules["bluetooth"].list_paired())

    @app.get("/api/bluetooth/available")
    @require_auth
    def bt_available():
        return ok(app.modules["bluetooth"].list_available())

    @app.post("/api/bluetooth/scan")
    @require_auth
    def bt_scan():
        app.modules["bluetooth"].scan_requested = True
        return ok({"scan": "started"})

    @app.post("/api/bluetooth/pair")
    @require_auth
    def bt_pair():
        mac = (request.json or {}).get("mac")
        if not mac:
            return fail("missing mac")
        app.modules["bluetooth"].pair_request = mac
        return ok({"pairing": mac})

    @app.post("/api/bluetooth/unpair")
    @require_auth
    def bt_unpair():
        mac = (request.json or {}).get("mac")
        if not mac:
            return fail("missing mac")
        app.modules["bluetooth"].unpair_request = mac
        return ok({"unpair": mac})

    # ============================================================
    # NETWORK (WIFI + ETHERNET)
    # ============================================================
    @app.get("/api/network")
    @require_auth
    def net_status():
        return ok(app.modules["network"].read_status())

    @app.get("/api/network/wifi")
    @require_auth
    def net_wifi():
        return ok(app.modules["network"].read_status().get("wifi", {}))

    @app.get("/api/network/ethernet")
    @require_auth
    def net_eth():
        return ok(app.modules["network"].read_status().get("ethernet", {}))

    # ============================================================
    # MODEM
    # ============================================================
    @app.get("/api/modem")
    @require_auth
    def modem_status():
        return ok(app.modules["modem"].read_status())

    @app.post("/api/modem/at")
    @require_auth
    def modem_at():
        cmd = (request.json or {}).get("cmd")
        if not cmd:
            return fail("missing cmd")
        app.modules["modem"].at_request = cmd
        return ok({"sent": cmd})

    @app.post("/api/modem/reset")
    @require_auth
    def modem_reset():
        app.modules["modem"].reset_requested = True
        return ok({"reset": True})

    # ============================================================
    # TACHO
    # ============================================================
    @app.get("/api/tacho")
    @require_auth
    def tacho_status():
        return ok(app.modules["tacho"].read_status())

    @app.get("/api/tacho/logs/daily")
    @require_auth
    def tacho_daily():
        return ok(app.storage.get_daily_logs())

    @app.get("/api/tacho/logs/weekly")
    @require_auth
    def tacho_weekly():
        return ok(app.storage.get_weekly_logs())

    @app.get("/api/tacho/logs/monthly")
    @require_auth
    def tacho_monthly():
        return ok(app.storage.get_monthly_logs())

    @app.get("/api/tacho/logs/yearly")
    @require_auth
    def tacho_yearly():
        return ok(app.storage.get_yearly_logs())

    # ============================================================
    # LOGS
    # ============================================================
    @app.get("/api/logs/live")
    @require_auth
    def logs_live():
        return ok(app.modules["logs"].read_status())

    @app.get("/api/logs/files/daily")
    @require_auth
    def logs_daily():
        files = [
            f for f in os.listdir(app.storage.LOGS_DIR)
            if f.endswith(".txt")
        ]
        return ok(sorted(files))

    # ============================================================
    # OTA
    # ============================================================
    @app.post("/api/ota/update")
    @require_auth
    def ota_update():
        data = request.json or {}
        url = data.get("url")
        sha256 = data.get("sha256")

        if not url:
            return fail("missing url")

        app.ota.queue_update(url, sha256)

        return ok({"queued": True, "url": url, "sha256": sha256})

    @app.get("/api/ota/status")
    @require_auth
    def ota_status():
        return ok({"status": "use_websocket"})

    # ============================================================
    # FRONTEND ROUTES - Serve Web Dashboard
    # ============================================================
    
    @app.route("/")
    def index():
        """Serve the main web dashboard"""
        from flask import send_from_directory
        import os
        frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "frontend")
        if os.path.exists(os.path.join(frontend_dir, "index.html")):
            return send_from_directory(frontend_dir, "index.html")
        else:
            return jsonify({"error": "Frontend not found", "path": frontend_dir}), 404
    

    return app


# ------------------------------------------------------------
# API RUNNER
# ------------------------------------------------------------

def start_api(modules, storage, ota_manager):
    """
    Starts Flask API server in a background thread.
    """
    app = create_app(modules, storage, ota_manager)

    def run():
        logger.log("INFO", "REST API running on port 8000")
        app.run(
            host="0.0.0.0",
            port=8000,
            debug=False,
            threaded=True,
            use_reloader=False
        )

    threading.Thread(target=run, daemon=True).start()
