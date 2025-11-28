#!/usr/bin/env python3
# ADA-Pi WebSocket Server
# Broadcasts IPC events to all connected UI clients

import asyncio
import json
import websockets
from logger import logger


class WebSocketServer:
    def __init__(self, host="0.0.0.0", port=9000):
        self.host = host
        self.port = port
        self.clients = set()
        self.loop = None

    # ------------------------------------------------------------
    async def handler(self, websocket, path):
        # new client connected
        self.clients.add(websocket)
        logger.log("INFO", f"WebSocket client connected. {len(self.clients)} total")

        try:
            async for message in websocket:
                # client sent a message (for future commands)
                pass

        except Exception as e:
            logger.log("WARN", f"WebSocket client disconnected: {e}")

        finally:
            self.clients.remove(websocket)

    # ------------------------------------------------------------
    async def broadcast(self, event, payload):
        """
        Broadcast message to all connected clients.
        """
        if not self.clients:
            return

        msg = json.dumps({
            "event": event,
            "payload": payload
        })

        dead = []
        for ws in self.clients:
            try:
                await ws.send(msg)
            except:
                dead.append(ws)

        for ws in dead:
            self.clients.remove(ws)

    # ------------------------------------------------------------
    def start(self):
        """
        Run WebSocket server in its own thread using a new asyncio loop.
        """
        logger.log("INFO", f"Starting WebSocket server on ws://{self.host}:{self.port}")

        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        server = websockets.serve(self.handler, self.host, self.port)
        self.loop.run_until_complete(server)
        self.loop.run_forever()

    # ------------------------------------------------------------
    def stop(self):
        if self.loop:
            self.loop.stop()
