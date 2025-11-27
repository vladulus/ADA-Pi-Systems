# ADA-Pi Backend Module: Tacho Module
# Handles GPS-based speed logging, trip logging, daily logs,
# monthly logs, and upload scheduling.

import time

class TachoModule:
    def __init__(self):
        self.enabled = False
        self.upload_interval = 5  # minutes
        self.last_upload = 0

        # live data
        self.speed = 0.0
        self.latitude = 0.0
        self.longitude = 0.0

        # logs
        self.speed_history = []      # last N values
        self.daily_log = []          # full day list of points
        self.monthly_log = []        # monthly summaries

    def update_position(self, speed, lat, lon):
        """Called by GPS service every refresh."""
        self.speed = speed
        self.latitude = lat
        self.longitude = lon

        timestamp = time.time()

        # Append to history (graph)
        self.speed_history.append({"t": timestamp, "speed": speed})
        if len(self.speed_history) > 200:
            self.speed_history.pop(0)

        # Append to daily log
        self.daily_log.append({
            "t": timestamp,
            "speed": speed,
            "lat": lat,
            "lon": lon
        })

    def set_enabled(self, state: bool):
        self.enabled = state

    def set_upload_interval(self, minutes: int):
        self.upload_interval = minutes

    def should_upload(self):
        """Returns True if time since last upload > interval."""
        return (time.time() - self.last_upload) > (self.upload_interval * 60)

    def mark_uploaded(self):
        self.last_upload = time.time()

    def get_speed_history(self):
        return self.speed_history

    def get_daily_log(self):
        return self.daily_log

    def get_monthly_log(self):
        return self.monthly_log

    def read_status(self):
        """Return JSON-friendly dictionary for API + UI."""
        return {
            "enabled": self.enabled,
            "upload_interval": self.upload_interval,
            "last_upload": self.last_upload,
            "speed": self.speed,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "speed_history": self.speed_history
        }