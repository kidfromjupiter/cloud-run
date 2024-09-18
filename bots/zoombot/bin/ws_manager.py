import json
from typing import List

import websockets.sync.client


class WebsocketConnection:
    def __init__(self, ws_link: str, from_id: str, to_id: str) -> None:
        self.conn = None
        self.ws_link: str = ws_link
        self.connected: bool = False
        self.from_id = from_id
        self.to_id = to_id

    def connect(self):
        self.conn = websockets.sync.client.connect(self.ws_link)
        self.connected = True

    def __ws_send(self, payload: dict):
        if self.conn is not None:
            print("conn isnt none. Sending")
            self.conn.send(json.dumps(payload))
            print("sent")

