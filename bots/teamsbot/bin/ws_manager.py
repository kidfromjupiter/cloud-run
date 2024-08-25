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
        self.conn.send(json.dumps({
            'event': "join-room",
            'room': "room1"
        }))

    def __ws_send(self, payload: dict):
        if self.conn is not None:
            print("conn isnt none. Sending")
            self.conn.send(json.dumps(payload))
            print("sent")

    def send_status(self, last_status, bot_name, meeting_id):
        payload = {
            "fromId": str(self.from_id),
            "toId": str(self.to_id),
            "status": last_status,
            "botName": bot_name,
            "meetingLink": meeting_id,
        }
        self.__ws_send(payload)


    def send_participants(self, participants: List[str]):
        payload = {
            "event": "participants",
            "data": participants
        }
        print("in send participants")
        self.__ws_send(payload)

    def send_subject(self, subject: str):
        payload = {
            "event": "subject",
            "data": subject
        }
        self.__ws_send(payload)
