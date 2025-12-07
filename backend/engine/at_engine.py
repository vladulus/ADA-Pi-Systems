#!/usr/bin/env python3
# AT Command Engine for ADA-Pi
# Provides a robust, reusable serial-based AT command interface

import serial
import time
import threading
from logger import logger

class ATCommandEngine:
    """
    Handles:
      - Serial port open/close
      - Auto-reconnect
      - Send AT commands safely
      - Read multi-line responses
      - Detect timeouts
      - Strip modem noise
    """

    def __init__(self):
        self.port = None
        self.ser = None
        self.lock = threading.Lock()

    # ------------------------------------------------------------
    def connect(self, port, baud=115200):
        """Open serial port."""
        try:
            self.ser = serial.Serial(
                port=port,
                baudrate=baud,
                timeout=1,
                write_timeout=1
            )
            self.port = port
            logger.log("INFO", f"AT engine connected to {port}")
            return True
        except Exception as e:
            logger.log("ERROR", f"AT connect failed on {port}: {e}")
            return False

    # ------------------------------------------------------------
    def disconnect(self):
        """Close serial port."""
        try:
            if self.ser:
                self.ser.close()
                self.ser = None
                logger.log("INFO", "AT engine disconnected")
        except:
            pass

    # ------------------------------------------------------------
    def send(self, command, timeout=2, strip_ok=True):
        """
        Send AT command and return a list of response lines.
        """

        if self.ser is None:
            logger.log("WARN", "AT send called but no modem connected")
            return []

        with self.lock:
            try:
                # Flush I/O
                self.ser.reset_input_buffer()
                self.ser.reset_output_buffer()

                # Send command
                cmd = (command + "\r").encode()
                self.ser.write(cmd)

                lines = []
                t_end = time.time() + timeout

                # Read response lines until timeout
                while time.time() < t_end:
                    line = self.ser.readline().decode(errors="ignore").strip()
                    if not line:
                        continue

                    # Skip echo
                    if line == command:
                        continue

                    # Stop on OK or ERROR
                    if line == "OK" and strip_ok:
                        break

                    lines.append(line)

                    if "ERROR" in line:
                        break

                return lines

            except Exception as e:
                logger.log("ERROR", f"AT send failed: {e}")
                self.disconnect()
                return []

    # ------------------------------------------------------------
    def test(self):
        """Send 'AT' to confirm modem is responsive."""
        resp = self.send("AT", strip_ok=False)
        return len(resp) > 0
