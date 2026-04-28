from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import List, Optional
import json
import asyncio
from app.api.utils import decode_access_token

router = APIRouter(tags=["WebSockets"])

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[WebSocket, str] = {} # WebSocket -> Full Name

    async def connect(self, websocket: WebSocket, full_name: str):
        await websocket.accept()
        self.active_connections[websocket] = full_name

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            del self.active_connections[websocket]

    def get_online_users(self) -> List[str]:
        # Return unique names
        return list(set(self.active_connections.values()))

    async def broadcast(self, message: dict):
        for websocket in list(self.active_connections.keys()):
            try:
                await websocket.send_json(message)
            except Exception:
                self.disconnect(websocket)

manager = ConnectionManager()

@router.get("/online")
async def get_online_users():
    """Returns a list of unique names of users currently connected via WebSocket."""
    return manager.get_online_users()

@router.websocket("/ws/status")
async def websocket_endpoint(websocket: WebSocket, token: Optional[str] = Query(None)):
    payload = decode_access_token(token) if token else None
    if not payload:
        await websocket.close(code=1008)
        return

    full_name = payload.get("full_name", "Unknown")
    await manager.connect(websocket, full_name)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)

async def notify_new_report(report_data: dict):
    """Call this when a new report is added to notify all connected clients."""
    await manager.broadcast({
        "type": "new_report",
        "data": report_data
    })
