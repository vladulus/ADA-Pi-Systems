#!/usr/bin/env python3
# ADA-Pi Modem Worker
# Auto-detects and manages SIMCom + Quectel LTE/5G modems

import os
import time
from logger import logger
from engine.at_engine import ATCommandEngine


class ModemWorker:
    REFRESH = 5   # seconds

    def __init__(self, module):
        self.module = module
        self.running = True
        self.engine = ATCommandEngine()

    # ------------------------------------------------------------
    def start(self):
        logger.log("INFO", "ModemWorker started")

        while self.running:
            try:
                if not self._ensure_modem_connected():
                    time.sleep(self.REFRESH)
                    continue

                data = {}

                # Identify modem brand & model
                id_info = self._get_modem_identity()
                data.update(id_info)

                # SIM status, IMEI, ICCID
                sim_info = self._get_sim_info()
                data.update(sim_info)

                # Operator
                op_info = self._get_operator()
                data.update(op_info)

                # Network mode (2G/3G/4G/5G)
                mode_info = self._get_network_mode()
                data.update(mode_info)

                # Signal metrics (RSSI/RSRP/RSRQ/SINR)
                sig_info = self._get_signal()
                data.update(sig_info)

                # Registration state
                reg_info = self._get_registration()
                data.update(reg_info)

                # Update module
                data["connected"] = True
                data["error"] = None
                data["at_port"] = self.module.at_port
                self.module.update(data)

            except Exception as e:
                logger.log("ERROR", f"ModemWorker crash: {e}")
                self.module.update({
                    "error": str(e),
                    "connected": False
                })

            time.sleep(self.REFRESH)

    # ------------------------------------------------------------
    def stop(self):
        self.running = False

    # ------------------------------------------------------------
    # Auto-detect modem & AT port
    # ------------------------------------------------------------
    def _ensure_modem_connected(self):
        """Find and connect to correct /dev/ttyUSB* AT port."""

        if self.engine.ser and self.engine.test():
            return True

        logger.log("INFO", "Searching for modem AT port...")

        for i in range(0, 10):
            port = f"/dev/ttyUSB{i}"
            if not os.path.exists(port):
                continue

            if self.engine.connect(port):
                if self.engine.test():
                    self.module.at_port = port
                    logger.log("INFO", f"Modem detected on {port}")
                    return True

                self.engine.disconnect()

        self.module.update({
            "connected": False,
            "error": "Modem not detected"
        })
        return False

    # ------------------------------------------------------------
    # MODEM IDENTITY
    # ------------------------------------------------------------
    def _get_modem_identity(self):
        """Detect modem brand & model using ATI."""
        resp = self.engine.send("ATI")

        brand = None
        model = None

        for line in resp:
            if "SIMCOM" in line.upper():
                brand = "SIMCom"
            if "Quectel" in line:
                brand = "Quectel"

            if "SIM7600" in line:
                model = "SIM7600"
            if "EC25" in line:
                model = "EC25"
            if "EG25" in line:
                model = "EG25"
            if "RG" in line:
                model = "RG Series (5G)"
            if "RM" in line:
                model = "RM Series (5G)"

        return {
            "brand": brand,
            "model": model
        }

    # ------------------------------------------------------------
    # SIM INFO
    # ------------------------------------------------------------
    def _get_sim_info(self):
        iccid = None
        imsi = None
        imei = None

        # ICCID
        resp = self.engine.send("AT+ICCID")
        for line in resp:
            if "+ICCID:" in line:
                iccid = line.split(":")[1].strip()

        # IMSI
        resp = self.engine.send("AT+CIMI")
        for line in resp:
            if line.isdigit():
                imsi = line.strip()

        # IMEI
        resp = self.engine.send("AT+GSN")
        for line in resp:
            if line.isdigit():
                imei = line.strip()

        return {
            "iccid": iccid,
            "imsi": imsi,
            "imei": imei
        }

    # ------------------------------------------------------------
    # OPERATOR
    # ------------------------------------------------------------
    def _get_operator(self):
        resp = self.engine.send("AT+COPS?")
        operator = None

        for line in resp:
            if "+COPS:" in line:
                parts = line.split(",")
                if len(parts) >= 3:
                    operator = parts[2].replace('"', "")

        return {"operator": operator}

    # ------------------------------------------------------------
    # REGISTRATION
    # ------------------------------------------------------------
    def _get_registration(self):
        resp = self.engine.send("AT+CREG?")

        state_map = {
            "0": "not registered",
            "1": "home",
            "2": "searching",
            "3": "denied",
            "5": "roaming"
        }

        status = None

        for line in resp:
            if "+CREG:" in line:
                parts = line.split(",")
                if len(parts) >= 2:
                    status = state_map.get(parts[1], "unknown")

        return {"registration": status}

    # ------------------------------------------------------------
    # NETWORK MODE (2G/3G/4G/5G)
    # ------------------------------------------------------------
    def _get_network_mode(self):
        resp = self.engine.send('AT+QNWINFO')
        mode = None
        band = None

        for line in resp:
            if "+QNWINFO:" in line:
                parts = line.split(",")
                if len(parts) >= 2:
                    mode = parts[1].replace('"', "")
                if len(parts) >= 3:
                    band = parts[2].replace('"', "")

        # Normalize mode string
        if mode:
            mode = mode.upper()
            if "LTE" in mode:
                mode = "4G"
            elif "NR5G" in mode:
                mode = "5G"
            elif "WCDMA" in mode:
                mode = "3G"
            elif "GSM" in mode:
                mode = "2G"

        return {
            "network_mode": mode,
            "band": band
        }

    # ------------------------------------------------------------
    # SIGNAL STRENGTH
    # ------------------------------------------------------------
    def _get_signal(self):
        """Uses QCSQ for detailed LTE/5G signal."""
        resp = self.engine.send("AT+QCSQ")
        rssi = rsrp = rsrq = sinr = None

        for line in resp:
            if "+QCSQ:" in line:
                parts = line.split(",")
                # Example: +QCSQ: "LTE",-65,-95,-7,21
                if len(parts) >= 5:
                    try:
                        rssi = int(parts[1])
                        rsrp = int(parts[2])
                        rsrq = int(parts[3])
                        sinr = int(parts[4])
                    except:
                        pass

        return {
            "rssi": rssi,
            "rsrp": rsrp,
            "rsrq": rsrq,
            "sinr": sinr
        }
