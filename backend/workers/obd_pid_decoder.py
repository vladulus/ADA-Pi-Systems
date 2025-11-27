#!/usr/bin/env python3
# PID Decoder for ADA-Pi OBD Worker
# Handles decoding for gasoline + diesel + extended PIDs

class PIDDecoder:
    def __init__(self):
        pass

    # ------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------
    def _hexbytes(self, raw):
        """Return cleaned hex byte list from raw ELM327 output."""
        try:
            parts = raw.replace(">", "").strip().split()
            return [int(x, 16) for x in parts if len(x) <= 2]
        except:
            return []

    # ------------------------------------------------------------
    # Standard PIDs
    # ------------------------------------------------------------
    def rpm(self, raw):
        b = self._hexbytes(raw)
        if len(b) >= 4:
            return ((b[-2] * 256) + b[-1]) / 4
        return 0

    def speed(self, raw):
        b = self._hexbytes(raw)
        if len(b) >= 3:
            return b[-1]
        return 0

    def temp(self, raw):
        b = self._hexbytes(raw)
        if len(b) >= 3:
            return b[-1] - 40
        return 0

    def percent(self, raw):
        b = self._hexbytes(raw)
        if len(b) >= 3:
            return round((b[-1] / 255) * 100, 1)
        return 0

    def voltage(self, raw):
        """ATRV returns something like '12.4V'."""
        try:
            txt = raw.replace("V", "").strip()
            return float(txt)
        except:
            return 0.0

    def maf(self, raw):
        b = self._hexbytes(raw)
        if len(b) >= 4:
            return ((b[-2] * 256) + b[-1]) / 100
        return 0

    def map(self, raw):
        b = self._hexbytes(raw)
        if len(b) >= 3:
            return b[-1]  # kPa
        return 0

    # ------------------------------------------------------------
    # Diesel PIDs
    # ------------------------------------------------------------
    def boost(self, raw):
        """Manifold boost pressure (PID 0x70 or similar)"""
        b = self._hexbytes(raw)
        if len(b) >= 3:
            return b[-1]  # kPa or psi depending on ECU
        return 0

    def rail_pressure(self, raw):
        b = self._hexbytes(raw)
        if len(b) >= 4:
            return ((b[-2] * 256) + b[-1])  # raw units
        return 0

    # ------------------------------------------------------------
    # DTC decoding
    # ------------------------------------------------------------
    def decode_dtcs(self, raw):
        """
        Convert bytes to OBD-II DTC codes.
        Example:
          43 01 33 00 00  -> P0133
        """

        b = self._hexbytes(raw)
        if len(b) < 3:
            return []

        dtcs = []

        # Skip first byte (0x43 = response to 03)
        # Then process A/B pairs
        for i in range(1, len(b), 2):
            if i + 1 >= len(b):
                break

            A = b[i]
            B = b[i + 1]

            if A == 0 and B == 0:
                continue

            dtcs.append(self._decode_dtc_pair(A, B))

        return dtcs

    def _decode_dtc_pair(self, A, B):
        """Convert two bytes into DTC string."""
        # First two bits determine system:
        # 00 = P (Powertrain)
        # 01 = C (Chassis)
        # 10 = B (Body)
        # 11 = U (Network)
        sys = ["P", "C", "B", "U"][(A & 0xC0) >> 6]

        code = (
            sys +
            format((A & 0x3F), "02X") +
            format(B, "02X")
        )
        return code
