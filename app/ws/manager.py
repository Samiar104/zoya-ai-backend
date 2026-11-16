"""WebSocket connection manager.

Two channels:
- /ws/device/{device_id} — one connection per Android device, used to push
  commands and receive results.
- /ws/chat — browser/dashboard chat channel, used for live conversation.

The manager is process-local. For multi-worker production use Redis
pub/sub — see README.
"""
import json
from typing import Any

from fastapi import WebSocket

from app.core.logging import get_logger

log = get_logger("zoya.ws")


class ConnectionManager:
    def __init__(self) -> None:
        self.devices: dict[str, WebSocket] = {}
        self.chat_clients: set[WebSocket] = set()

    # --- devices -------------------------------------------------------
    async def connect_device(self, device_id: str, ws: WebSocket) -> None:
        await ws.accept()
        self.devices[device_id] = ws
        log.info("Device connected via WebSocket: %s", device_id)

    def disconnect_device(self, device_id: str) -> None:
        self.devices.pop(device_id, None)
        log.info("Device disconnected: %s", device_id)

    def is_device_connected(self, device_id: str) -> bool:
        return device_id in self.devices

    async def send_to_device(self, device_id: str, payload: dict[str, Any]) -> bool:
        ws = self.devices.get(device_id)
        if ws is None:
            return False
        try:
            await ws.send_text(json.dumps(payload))
            return True
        except Exception as exc:  # noqa: BLE001 - a dead socket must not crash the API
            log.warning("Failed to send to device %s: %s", device_id, exc)
            self.devices.pop(device_id, None)
            return False

    # --- chat ----------------------------------------------------------
    async def connect_chat(self, ws: WebSocket) -> None:
        await ws.accept()
        self.chat_clients.add(ws)

    def disconnect_chat(self, ws: WebSocket) -> None:
        self.chat_clients.discard(ws)

    async def broadcast_chat(self, payload: dict[str, Any]) -> None:
        dead = set()
        for ws in self.chat_clients:
            try:
                await ws.send_text(json.dumps(payload))
            except Exception:  # noqa: BLE001
                dead.add(ws)
        self.chat_clients -= dead


manager = ConnectionManager()
