from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import List, Optional
import json
import asyncio
from app.api.utils import decode_access_token

router = APIRouter(tags=["WebSockets"])

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        # We use a copy to avoid modification during iteration
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection)

manager = ConnectionManager()

@router.websocket("/ws/status")
async def websocket_endpoint(websocket: WebSocket, token: Optional[str] = Query(None)):
    if not token or not decode_access_token(token):
        # Reject unauthorized connections
        await websocket.close(code=1008) # 1008 is Policy Violation
        return

    await manager.connect(websocket)
    try:
        while True:
            # We don't expect messages from client, but must read to detect disconnects
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
