import json
from typing import Union

import websocket

from schema.app import ModStatusSchema
from smods_manager.app import WEBSOCKET_PORT
from smods_websocket.model import WebsocketMessage, ModStatus
from utils.logger import get_logger

logger = get_logger(__name__)


def create_status_message(channel: str, payload: Union[dict, str]) -> WebsocketMessage:
    return WebsocketMessage(type="status", channel=channel, payload=payload)


def send_status(websock: websocket.WebSocket, channel: str, status: ModStatus):
    logger.debug("Sending message to the WebSocket...")
    logger.debug(f"Websocket status: status={websock.status}, timeout={websock.timeout}, connected={websock.connected}")
    status_object = create_status_message(channel, ModStatusSchema().dump(status))
    if websock.connected:
        try:
            websock.send(json.dumps(dict(status_object)))
        except Exception:
            websock.connect(f"ws://localhost:{WEBSOCKET_PORT}")
