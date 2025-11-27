import time

class LogsModule:
    """
    Stores a rolling buffer of recent live logs for UI display.
    """

    def __init__(self):
        self.buffer = []
        self.max_size = 200  # last 200 log lines

    def push(self, line):
        """Add a new log line to buffer."""
        timestamped = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {line}"
        self.buffer.append(timestamped)
        if len(self.buffer) > self.max_size:
            self.buffer.pop(0)

    def read_status(self):
        """Return last N logs."""
        return {"recent": list(self.buffer)}
