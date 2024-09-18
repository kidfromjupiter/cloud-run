from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
        self.active_connections_groups: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, id: str):
        await websocket.accept()
        self.active_connections[id] = websocket

    async def connect_group(self, websocket: WebSocket, group_id: str):
        self.active_connections_groups[group_id].append(websocket)

    def disconnect(self, id: str):
        self.active_connections.pop(id)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def kill(self, id: str):
        await self.active_connections[id].send_json({
            "kill": True
        })

    async def kill_group(self, group_id: str):
        for websocket in self.active_connections_groups[group_id]:
            await websocket.send_json({
                "kill": True
            })

    async def broadcast(self, message: str):
        for connection in self.active_connections.values():
            await connection.send_text(message)
