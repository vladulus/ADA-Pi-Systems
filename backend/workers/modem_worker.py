import os
import time
import re
from datetime import datetime, timezone
from logger import logger
from engine.at_engine import ATCommandEngine
from ipc.router import router


class ModemWorker:
    REFRESH = 5

    def __init__(self, module, config=None, gps_module=None):
        self.module = module
        self.config = config or {}
        self.running = True
        self.engine = ATCommandEngine()
        self.gps_module = gps_module
        self._gps_enabled = False

    def start(self):
        logger.log("INFO", "ModemWorker started")

        while self.running:
            try:
                if not self._ensure_modem_connected():
                    time.sleep(self.REFRESH)
                    continue

                data = {}
                id_info = self._get_modem_identity()
                data.update(id_info)
                sim_info = self._get_sim_info()
                data.update(sim_info)
                op_info = self._get_operator()
                data.update(op_info)
                mode_info = self._get_network_mode()
                data.update(mode_info)
                sig_info = self._get_signal()
                data.update(sig_info)
                reg_info = self._get_registration()
                data.update(reg_info)

                if self.gps_module:
                    self._read_gps()

                data["connected"] = True
                data["error"] = None
                data["at_port"] = self.module.at_port
                self.module.update(data)
                router.publish("modem_update", data)

            except Exception as e:
                logger.log("ERROR", f"ModemWorker crash: {e}")
                self.module.update({"error": str(e), "connected": False})

            time.sleep(self.REFRESH)

    def stop(self):
        self.running = False

    def _read_gps(self):
        """Read GPS via AT+CGNSSINFO"""
        try:
            if not self._gps_enabled:
                self.engine.send("AT+CGPS=1")
                self._gps_enabled = True
                logger.log("INFO", "GPS enabled via ModemWorker")

            resp = self.engine.send("AT+CGNSSINFO")
            if not resp:
                self.gps_module.update_fix(False)
                return

            resp_text = "\n".join(resp)
            match = re.search(r'\+CGNSSINFO:\s*(.+)', resp_text)
            if not match:
                self.gps_module.update_fix(False)
                return

            data = match.group(1).strip()
            parts = data.split(',')

            if len(parts) < 10 or not parts[4]:
                self.gps_module.update_fix(False)
                return

            gps_sats = int(parts[1]) if parts[1] else 0
            glonass_sats = int(parts[2]) if parts[2] else 0
            satellites = gps_sats + glonass_sats

            lat = self._nmea_to_decimal(parts[4], parts[5])
            lon = self._nmea_to_decimal(parts[6], parts[7])

            if lat is None or lon is None:
                self.gps_module.update_fix(False)
                return

            alt = float(parts[10]) if len(parts) > 10 and parts[10] else 0.0
            speed_knots = float(parts[11]) if len(parts) > 11 and parts[11] else 0.0
            heading = float(parts[12]) if len(parts) > 12 and parts[12] else 0.0
            hdop = float(parts[13]) if len(parts) > 13 and parts[13] else None
            speed_kmh = speed_knots * 1.852

            date_str = parts[8] if len(parts) > 8 else ""
            time_str = parts[9] if len(parts) > 9 else ""
            timestamp = datetime.now(timezone.utc).isoformat()
            if date_str and time_str:
                try:
                    time_clean = time_str.split(".")[0].ljust(6, "0")
                    timestamp = datetime.strptime(date_str + time_clean, "%d%m%y%H%M%S").replace(tzinfo=timezone.utc).isoformat()
                except:
                    pass

            self.gps_module.update_position(lat, lon, alt, hdop=hdop, heading=heading, timestamp=timestamp)
            self.gps_module.update_speed(speed_kmh)
            self.gps_module.update_fix(True)
            self.gps_module.satellites = satellites

            if 49 <= lat <= 61 and -8 <= lon <= 2:
                self.gps_module.set_auto_unit("mph")
            else:
                self.gps_module.set_auto_unit("kmh")

            logger.log("INFO", f"GPS fix: {lat:.6f}, {lon:.6f}, {satellites} sats, alt={alt}m")

            router.publish("gps_update", {
                "latitude": lat,
                "longitude": lon,
                "altitude": alt,
                "speed": self.gps_module.get_speed(),
                "unit": self.gps_module.get_unit(),
                "satellites": satellites,
                "hdop": hdop,
                "fix": True,
                "heading": heading,
                "timestamp": timestamp
            })

        except Exception as e:
            logger.log("ERROR", f"GPS read error: {e}")
            self.gps_module.update_fix(False)

    def _nmea_to_decimal(self, value, direction):
        if not value:
            return None
        try:
            deg_len = 2 if direction in ["N", "S"] else 3
            deg = float(value[:deg_len])
            minutes = float(value[deg_len:])
            dec = deg + (minutes / 60.0)
            if direction in ["S", "W"]:
                dec = -dec
            return dec
        except:
            return None

    def _ensure_modem_connected(self):
        if self.engine.ser and self.engine.test():
            return True

        modem_config = self.config.get("modem", {})
        config_port = modem_config.get("port")

        if config_port and os.path.exists(config_port):
            logger.log("INFO", f"Using configured modem port: {config_port}")
            if self.engine.connect(config_port):
                if self.engine.test():
                    self.module.at_port = config_port
                    logger.log("INFO", f"Modem detected on {config_port}")
                    return True
                self.engine.disconnect()
            logger.log("ERROR", f"Failed to connect to configured port {config_port}")
            self.module.update({"connected": False, "error": f"Modem not detected on {config_port}"})
            return False

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

        self.module.update({"connected": False, "error": "Modem not detected"})
        return False

    def _get_modem_identity(self):
        resp = self.engine.send("ATI")
        brand = model = None
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
        self.brand = brand
        return {"brand": brand, "model": model}

    def _get_sim_info(self):
        iccid = imsi = imei = None
        resp = self.engine.send("AT+ICCID")
        for line in resp:
            if "+ICCID:" in line:
                iccid = line.split(":")[1].strip()
        resp = self.engine.send("AT+CIMI")
        for line in resp:
            if line.isdigit():
                imsi = line.strip()
        resp = self.engine.send("AT+GSN")
        for line in resp:
            if line.isdigit():
                imei = line.strip()
        return {"iccid": iccid, "imsi": imsi, "imei": imei}

    def _get_operator(self):
        resp = self.engine.send("AT+COPS?")
        operator = None
        for line in resp:
            if "+COPS:" in line:
                # +COPS: 0,0,"LycaMobile LycaMobile",7
                match = re.search(r'"([^"]+)"', line)
                if match:
                    operator = match.group(1)
                    # Remove duplicate name if present
                    parts = operator.split()
                    if len(parts) == 2 and parts[0] == parts[1]:
                        operator = parts[0]
        return {"operator": operator}

    def _get_registration(self):
        resp = self.engine.send("AT+CREG?")
        state_map = {"0": "not registered", "1": "home", "2": "searching", "3": "denied", "5": "roaming"}
        status = None
        for line in resp:
            if "+CREG:" in line:
                parts = line.split(",")
                if len(parts) >= 2:
                    status = state_map.get(parts[1], "unknown")
        return {"registration": status}

    def _get_network_mode(self):
        resp = self.engine.send('AT+CPSI?')
        mode = band = None
        for line in resp:
            if "+CPSI:" in line:
                parts = line.split(",")
                if len(parts) >= 1:
                    mode = parts[0].split(":")[1].strip()
                if len(parts) >= 7:
                    band = parts[6]
        if mode:
            if "LTE" in mode:
                mode = "4G"
            elif "NR" in mode or "5G" in mode:
                mode = "5G"
            elif "WCDMA" in mode:
                mode = "3G"
            elif "GSM" in mode:
                mode = "2G"
        return {"network_mode": mode, "band": band}

    def _get_signal(self):
        rssi = rsrp = rsrq = sinr = None
        if hasattr(self, 'brand') and self.brand == "SIMCom":
            resp = self.engine.send("AT+CSQ")
            for line in resp:
                if "+CSQ:" in line:
                    parts = line.split(":")
                    if len(parts) >= 2:
                        values = parts[1].strip().split(",")
                        if len(values) >= 1:
                            try:
                                csq = int(values[0])
                                if csq != 99:
                                    rssi = -113 + (csq * 2)
                            except:
                                pass
            # Get detailed signal from CPSI
            resp = self.engine.send("AT+CPSI?")
            for line in resp:
                if "+CPSI:" in line:
                    parts = line.split(",")
                    # +CPSI: LTE,Online,234-30,0x67F2,2871821,432,EUTRAN-BAND20,6225,2,-200,-1400,-709,12
                    if len(parts) >= 13:
                        try:
                            rsrq = int(parts[9]) // 10 if parts[9] else None  # -200 -> -20
                            rsrp = int(parts[10]) // 10 if parts[10] else None  # -1400 -> -140
                            sinr = int(parts[12]) if parts[12] else None  # 12
                        except:
                            pass
        else:
            resp = self.engine.send("AT+QCSQ")
            for line in resp:
                if "+QCSQ:" in line:
                    parts = line.split(",")
                    if len(parts) >= 5:
                        try:
                            rssi = int(parts[1])
                            rsrp = int(parts[2])
                            rsrq = int(parts[3])
                            sinr = int(parts[4])
                        except:
                            pass
        return {"rssi": rssi, "rsrp": rsrp, "rsrq": rsrq, "sinr": sinr}
