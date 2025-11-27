# ADA-Pi Backend Module: Logger
# Simple centralized logger for backend systems

import time

class Logger:
    def __init__(self):
        self.entries = []
        self.max_entries = 500

    def log(self, level, message):
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        entry = f"[{timestamp}] [{level}] {message}"
        self.entries.append(entry)

        if len(self.entries) > self.max_entries:
            self.entries.pop(0)

        print(entry)

    def get_logs(self):
        return self.entries

# Global shared logger instance
logger = Logger()
