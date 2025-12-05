#!/usr/bin/env python3
# ADA-Pi Unified Backend Engine
# Orchestrates all modules, workers, IPC, API, WebSocket, and OTA

import threading
import signal
import time
from logger import logger

# Config
from config_manager import load_config

# Modules
from modules.ups.module import UPSModule
from modules.network.module import NetworkModule
from modules.modem.module import ModemModule
from modules.gps.module import GPSModule
from modules.bluetooth.module import BluetoothModule
from modules.logs.module import LogsModule
from modules.tacho.module import TachoModule
from modules.fan.module import FanModule
from modules.obd.module import OBDModule
from modules.systeminfo.module import SystemInfoModule

# Workers
from workers.ups_worker import UPSWorker
from workers.network_worker import NetworkWorker
from workers.modem_worker import ModemWorker
from workers.gps_worker import GPSWorker
from workers.bluetooth_worker import BluetoothWorker
from workers.logs_worker import LogsWorker
from workers.tacho_worker import TachoWorker
from workers.tacho_uploader import TachoUploader
from workers.fan_worker import FanWorker
from workers.obd_worker import OBDWorker
from workers.systeminfo_worker import SystemInfoWorker
from workers.cloud_uploader import CloudUploader
from workers.rotation_worker import RotationWorker
from workers.ota_worker import OTAWorker
# Storage
from storage.storage_manager import StorageManager

# API + OTA
from api.server import start_api
from engine.ota_manager import OTAManager

# WebSocket
from api.websocket import WebSocketServer
from api.bridge import WebSocketBridge


class BackendEngine:
    def __init__(self):
        logger.log("INFO", "Initializing backend engine...")

        # --------------------------------------------------------
        # LOAD CONFIG
        # --------------------------------------------------------
        self.config = load_config()

        # --------------------------------------------------------
        # INIT MODULES
        # --------------------------------------------------------
        self.modules = {
            "ups": UPSModule(),
            "network": NetworkModule(),
            "modem": ModemModule(),
            "gps": GPSModule(),
            "bluetooth": BluetoothModule(),
            "logs": LogsModule(),
            "tacho": TachoModule(),
            "fan": FanModule(),
            "obd": OBDModule(),
            "system": SystemInfoModule()
        }

        # --------------------------------------------------------
        # INIT STORAGE
        # --------------------------------------------------------
        self.storage = StorageManager()

        # --------------------------------------------------------
        # INIT OTA MANAGER
        # --------------------------------------------------------
        self.ota = OTAManager(self.storage)

        # --------------------------------------------------------
        # INIT WORKERS
        # --------------------------------------------------------
        self.workers = [
            UPSWorker(self.modules["ups"]),
            NetworkWorker(self.modules["network"]),
            ModemWorker(self.modules["modem"], self.config),
            GPSWorker(self.modules["gps"]),
            BluetoothWorker(self.modules["bluetooth"]),
            LogsWorker(self.modules["logs"]),
            TachoWorker(self.modules["tacho"], self.modules["gps"]),
            FanWorker(self.modules["fan"]),
            OBDWorker(self.modules["obd"]),
            SystemInfoWorker(self.modules["system"]),
            TachoUploader(self.modules["tacho"], self.storage),
            CloudUploader(self.modules, self.storage),
            RotationWorker(self.storage),
            OTAWorker(self.ota, self.storage)
        ]

        self.threads = []

        logger.log("INFO", "Backend engine initialized.")

    # ------------------------------------------------------------
    def start(self):
        logger.log("INFO", "Starting backend workers...")

        # --------------------------------------------------------
        # START ALL WORKERS
        # --------------------------------------------------------
        for worker in self.workers:
            t = threading.Thread(target=worker.start, daemon=True)
            t.start()
            self.threads.append((worker, t))

        logger.log("INFO", "All workers started.")

        # --------------------------------------------------------
        # START REST API SERVER
        # --------------------------------------------------------
        api_thread = threading.Thread(
            target=start_api,
            args=(self.modules, self.storage, self.ota),
            daemon=True
        )
        api_thread.start()
        logger.log("INFO", "REST API running on port 8000")

        # --------------------------------------------------------
        # START WEBSOCKET SERVER
        # --------------------------------------------------------
        ws_server = WebSocketServer(host="0.0.0.0", port=9000)

        # Enable tagging of IPC events
        bridge = WebSocketBridge(ws_server)
        ws_thread = threading.Thread(target=ws_server.start, daemon=True)
        ws_thread.start()
        # Bridge IPC → WebSocket
        WebSocketBridge.enable_event_tracking()


        logger.log("INFO", "WebSocket server running on port 9000")

        # --------------------------------------------------------
        # SIGNAL HANDLING
        # --------------------------------------------------------
        signal.signal(signal.SIGINT, self._shutdown)
        signal.signal(signal.SIGTERM, self._shutdown)

        # Keep engine alive
        while True:
            time.sleep(1)

    # ------------------------------------------------------------
    def _shutdown(self, signum, frame):
        logger.log("WARN", f"Shutting down backend engine (signal={signum})")

        for worker, thread in self.threads:
            try:
                worker.stop()
            except:
                pass

        time.sleep(1)
        logger.log("INFO", "Backend stopped cleanly.")
        exit(0)


# ------------------------------------------------------------
# ENTRY POINT
# ------------------------------------------------------------
if __name__ == "__main__":
    engine = BackendEngine()
    engine.start()
