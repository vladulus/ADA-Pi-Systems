# IPC → WebSocket Bridge

import asyncio
from ipc.router import router
from logger import logger

class WebSocketBridge:
    def __init__(self, ws_server):
        self.ws = ws_server

        # Subscribe to all backend events here
        router.subscribe("*", self.forward_any_event)

    # ------------------------------------------------------------
    def forward_any_event(self, data):
        """
        Called whenever ANY router.publish(event, data) is used.
        """
        event_name = data.get("__event__")

        if not event_name:
            return

        asyncio.run_coroutine_threadsafe(
            self.ws.broadcast(event_name, data),
            self.ws.loop
        )

    # ------------------------------------------------------------
    @staticmethod
    def enable_event_tracking():
        """
        Modifies router.publish so that every event gets "__event__" key.
        """
        original_publish = router.publish

        def wrapped(event, payload=None):
            if payload is None:
                payload = {}
            payload["__event__"] = event
            original_publish(event, payload)

        router.publish = wrapped
