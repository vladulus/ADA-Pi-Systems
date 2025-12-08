#!/usr/bin/env python3
# ADA-Pi OBD Worker
# Auto-detects ELM327 adapters, supports cars, vans (diesel), trucks (J1939)

import os
import time
import serial
from logger import logger
from ipc.router import router
from workers.obd_pid_decoder import PIDDecoder


class OBDWorker:
    BAUD_RATES = [115200, 38400, 9600, 230400]

    POLL_INTERVAL = 2  # seconds

    def __init__(self, module, config=None):
        self.obd = module
        self.config = config or {}
        self.running = True
        self.ser = None
        self.decoder = PIDDecoder()
        self.initialized = False
        self.port = None
        self.baud = None
        self.protocol = None

        # API flag: /api/obd/clear
        self.request_clear = False
        
        # Flag to force DTC read on next cycle
        self.request_read_dtc = False

        # Build port scan list from config
        self._build_port_list()
        
        # Subscribe to IPC commands from cloud uploader
        router.subscribe("obd_command", self._handle_command)

    # ------------------------------------------------------------
    def _handle_command(self, data):
        """Handle commands from cloud uploader via IPC."""
        if not isinstance(data, dict):
            return
            
        action = data.get("action")
        
        if action == "clear_dtc":
            logger.log("INFO", "OBDWorker: received clear_dtc command from server")
            self.request_clear = True
            
        elif action == "read_dtc":
            logger.log("INFO", "OBDWorker: received read_dtc command from server")
            self.request_read_dtc = True

    # ------------------------------------------------------------
    def _build_port_list(self):
        """Build list of ports to scan based on config."""
        obd_config = self.config.get("obd", {})
        
        # Check if OBD is disabled
        if not obd_config.get("enabled", True):
            self.PORT_SCAN = []
            logger.log("INFO", "OBD is disabled in config")
            return

        connection_type = obd_config.get("connection", "bluetooth")
        
        # USB connection - use specific port or scan
        if connection_type == "usb":
            usb_port = obd_config.get("usb_port", "")
            if usb_port:
                self.PORT_SCAN = [usb_port]
                logger.log("INFO", f"OBD configured for USB: {usb_port}")
            else:
                # Scan all USB ports except modem
                all_ports = [f"/dev/ttyUSB{i}" for i in range(0, 10)]
                excluded = ["/dev/ttyUSB2", "/dev/ttyUSB3"]  # Modem ports
                self.PORT_SCAN = [p for p in all_ports if p not in excluded]
                logger.log("INFO", f"OBD USB mode: scanning {len(self.PORT_SCAN)} ports")
            return
        
        # Bluetooth connection - bind rfcomm
        if connection_type == "bluetooth":
            bt_mac = obd_config.get("bluetooth_mac", "")
            if bt_mac:
                # Try to bind rfcomm0
                if self._bind_bluetooth(bt_mac):
                    self.PORT_SCAN = ["/dev/rfcomm0"]
                    logger.log("INFO", f"OBD Bluetooth bound to {bt_mac}")
                else:
                    self.PORT_SCAN = []
                    logger.log("WARN", f"OBD Bluetooth bind failed for {bt_mac}")
            else:
                # No MAC configured, try rfcomm0 anyway
                self.PORT_SCAN = ["/dev/rfcomm0"]
                logger.log("INFO", "OBD Bluetooth mode: using /dev/rfcomm0")
            return

        # Legacy: Check if specific port is configured
        config_port = obd_config.get("port")
        if config_port:
            self.PORT_SCAN = [config_port]
            logger.log("INFO", f"OBD configured to use only: {config_port}")
            return

        # Default: scan all USB/ACM ports
        all_ports = [
            *[f"/dev/ttyUSB{i}" for i in range(0, 10)],
            *[f"/dev/ttyACM{i}" for i in range(0, 10)]
        ]

        # Exclude modem ports by default
        excluded = obd_config.get("excluded_ports", [
            "/dev/ttyUSB2",  # Modem AT port
            "/dev/ttyUSB3",  # Modem GPS port
            "/dev/modem-at",
            "/dev/modem-gps"
        ])

        # Filter out excluded ports
        self.PORT_SCAN = [p for p in all_ports if p not in excluded]
        logger.log("INFO", f"OBD will scan {len(self.PORT_SCAN)} ports (excluding modem)")

    def _bind_bluetooth(self, mac_address):
        """Bind Bluetooth ELM327 to rfcomm0."""
        import subprocess
        try:
            # Release any existing binding
            subprocess.run(["rfcomm", "release", "0"], 
                          capture_output=True, timeout=5)
            time.sleep(0.5)
            
            # Bind to new MAC
            result = subprocess.run(
                ["rfcomm", "bind", "0", mac_address],
                capture_output=True, timeout=10
            )
            
            if result.returncode == 0:
                time.sleep(1)  # Wait for device to appear
                return os.path.exists("/dev/rfcomm0")
            
            logger.log("WARN", f"rfcomm bind failed: {result.stderr.decode()}")
            return False
            
        except Exception as e:
            logger.log("ERROR", f"Bluetooth bind error: {e}")
            return False

    # ------------------------------------------------------------
    def start(self):
        logger.log("INFO", "OBDWorker started")

        while self.running:
            try:
                if not self.initialized:
                    if not self._ensure_connection():
                        time.sleep(2)
                        continue

                # Clear DTC when requested
                if self.request_clear:
                    self.clear_dtc()
                    self.request_clear = False

                # Force DTC read when requested
                if self.request_read_dtc:
                    dtcs = self._read_dtcs()
                    self.obd.update_fault_codes(dtcs)
                    router.publish("obd_update", {"dtc": dtcs})
                    logger.log("INFO", f"OBDWorker: DTCs read on demand: {dtcs}")
                    self.request_read_dtc = False

                # Read PID values
                self._read_pids()

            except Exception as e:
                logger.log("ERROR", f"OBDWorker crash: {e}")
                self.initialized = False

            time.sleep(self.POLL_INTERVAL)

    # ------------------------------------------------------------
    def stop(self):
        self.running = False
        if self.ser:
            try:
                self.ser.close()
            except:
                pass

    # ------------------------------------------------------------
    # CONNECTION & INITIALIZATION
    # ------------------------------------------------------------

    def _ensure_connection(self):
        """Find ELM327 and initialize it."""
        for port in self.PORT_SCAN:
            if not os.path.exists(port):
                continue

            for baud in self.BAUD_RATES:
                try:
                    self.ser = serial.Serial(port, baud, timeout=1)
                    logger.log("INFO", f"Trying ELM327 on {port} @ {baud}")

                    if self._init_elm():
                        self.port = port
                        self.baud = baud
                        self.initialized = True
                        self.obd.update_connection(True, port, baud, self.protocol)
                        return True
                except:
                    pass

        self.obd.update_connection(False, error="ELM327 not found")
        return False

    # ------------------------------------------------------------
    def _send(self, text):
        """Low-level send to ELM327."""
        try:
            self.ser.write((text + "\r").encode())
        except:
            self.initialized = False

    def _read(self):
        """Low-level read until prompt."""
        try:
            out = self.ser.read_until(b">").decode(errors="ignore")
            return out.replace("\r", "").replace("\n", " ")
        except:
            self.initialized = False
            return ""

    # ------------------------------------------------------------
    def _init_elm(self):
        """Run ELM327 startup sequence + protocol detection."""
        cmds = [
            "ATZ",     # full reset
            "ATE0",    # echo off
            "ATL0",    # no linefeeds
            "ATS0",    # no spaces
            "ATH0",    # no headers
            "ATSP0"    # auto detect protocol
        ]

        for cmd in cmds:
            self._send(cmd)
            time.sleep(0.3)
            self._read()

        # Detect protocol
        self._send("ATDP")
        time.sleep(0.2)
        resp = self._read()

        if "CAN" in resp or "ISO" in resp or "J1850" in resp or "KWP" in resp:
            self.protocol = resp.strip()
            logger.log("INFO", f"Detected OBD protocol: {resp}")
            return True

        return False

    # ------------------------------------------------------------
    # PID + DTC READING
    # ------------------------------------------------------------

    def _request_pid(self, pid):
        """Send PID and clean response."""
        self._send(pid)
        time.sleep(0.15)
        raw = self._read()

        # Clean garbage responses
        junk = ["SEARCHING", "STOPPED", "NO DATA", "UNABLE TO CONNECT", "?"]
        for j in junk:
            raw = raw.replace(j, "")

        return raw.strip()

    # ------------------------------------------------------------
    def _read_pids(self):
        """Reads all relevant PIDs and updates OBDModule."""

        # STANDARD PIDs
        rpm = self.decoder.rpm(self._request_pid("010C"))
        speed = self.decoder.speed(self._request_pid("010D"))
        coolant = self.decoder.temp(self._request_pid("0105"))
        load = self.decoder.percent(self._request_pid("0104"))
        throttle = self.decoder.percent(self._request_pid("0111"))
        fuel_level = self.decoder.percent(self._request_pid("012F"))
        maf = self.decoder.maf(self._request_pid("0110"))
        map_val = self.decoder.map(self._request_pid("010B"))
        intake_temp = self.decoder.temp(self._request_pid("010F"))

        # Voltage (ELM proprietary)
        voltage = self.decoder.voltage(self._request_pid("ATRV"))

        # DIESEL PIDs (SAFE FALLBACK FOR GASOLINE CARS)
        boost = self.decoder.boost(self._request_pid("0170"))  # manifold absolute boost
        rail = self.decoder.rail_pressure(self._request_pid("019A"))
        egr = self.decoder.percent(self._request_pid("011C"))
        dpf_in = self.decoder.temp(self._request_pid("018B"))
        dpf_out = self.decoder.temp(self._request_pid("018C"))
        soot = self.decoder.percent(self._request_pid("018D"))

        # Update module
        self.obd.update_values(
            rpm=rpm,
            speed=speed,
            coolant=coolant,
            load=load,
            voltage=voltage,
            throttle=throttle,
            fuel_level=fuel_level,
            maf=maf,
            map=map_val,
            intake_temp=intake_temp,

            boost_pressure=boost,
            rail_pressure=rail,
            egr=egr,
            dpf_temp_in=dpf_in,
            dpf_temp_out=dpf_out,
            dpf_soot=soot
        )

        # DTC every 10 seconds
        if int(time.time()) % 10 == 0:
            dtcs = self._read_dtcs()
            self.obd.update_fault_codes(dtcs)

        # Notify frontend
        router.publish("obd_update", self.obd.read_status())

    # ------------------------------------------------------------
    # DTC HANDLING
    # ------------------------------------------------------------
    def _read_dtcs(self):
        raw = self._request_pid("03")
        return self.decoder.decode_dtcs(raw)

    def clear_dtc(self):
        logger.log("INFO", "Clearing DTC codes...")
        self._send("04")
        time.sleep(1)
        self._read()

        dtcs = self._read_dtcs()
        self.obd.update_fault_codes(dtcs)

        router.publish("obd_update", {"dtc": dtcs})
        logger.log("INFO", "DTC cleared.")
