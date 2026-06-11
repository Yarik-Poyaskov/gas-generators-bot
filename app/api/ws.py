from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import List, Optional, Dict
import json
import asyncio
from pydantic import BaseModel
from app.api.utils import decode_access_token

router = APIRouter(tags=["WebSockets"])

class ConnectionManager:
    def __init__(self):
        # Храним WebSocket -> {"user_id": int, "full_name": str}
        self.active_connections: dict[WebSocket, dict] = {} 

    async def connect(self, websocket: WebSocket, user_id: int, full_name: str):
        await websocket.accept()
        self.active_connections[websocket] = {
            "user_id": user_id,
            "full_name": full_name
        }

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            del self.active_connections[websocket]

    def get_online_users(self) -> List[dict]:
        # Возвращает список уникальных пользователей онлайн
        seen = set()
        online = []
        for info in self.active_connections.values():
            u_id = info["user_id"]
            if u_id not in seen:
                seen.add(u_id)
                online.append({
                    "user_id": u_id,
                    "full_name": info["full_name"]
                })
        return online

    async def send_personal_message(self, user_id: int, message: dict) -> bool:
        """Отправляет JSON-сообщение всем открытым вкладкам конкретного пользователя."""
        sent = False
        for websocket, info in list(self.active_connections.items()):
            if info["user_id"] == user_id:
                try:
                    await websocket.send_json(message)
                    sent = True
                except Exception:
                    self.disconnect(websocket)
        return sent

    async def broadcast(self, message: dict):
        for websocket in list(self.active_connections.keys()):
            try:
                await websocket.send_json(message)
            except Exception:
                self.disconnect(websocket)

manager = ConnectionManager()

class ForceActionRequest(BaseModel):
    user_id: int
    action: str # "logout", "reload", "clear_cache"

@router.get("/online")
async def get_online_users():
    """Returns a list of unique names of users currently connected via WebSocket (for compatibility with Header.tsx)."""
    return [u["full_name"] for u in manager.get_online_users()]

@router.get("/online-details")
async def get_online_details():
    """Returns a detailed list of unique users connected with their user_ids and full_names."""
    return manager.get_online_users()

@router.post("/force-action")
async def force_user_action(payload: ForceActionRequest):
    """
    Sends a remote control command (logout, reload, clear_cache) to a specific user's sessions.
    """
    valid_actions = ["logout", "reload", "clear_cache"]
    if payload.action not in valid_actions:
        return {"status": "error", "message": f"Некоректна дія. Дозволені: {', '.join(valid_actions)}"}
        
    action_type = f"force_{payload.action}"
    
    success = await manager.send_personal_message(
        user_id=payload.user_id,
        message={"type": action_type}
    )
    
    # Для логаута или сброса кэша принудительно закроем соединение через секунду
    if payload.action in ["logout", "clear_cache"]:
        async def close_connections():
            await asyncio.sleep(1.0)
            for websocket, info in list(manager.active_connections.items()):
                if info["user_id"] == payload.user_id:
                    try:
                        await websocket.close(code=1000)
                    except:
                        pass
                    manager.disconnect(websocket)
        asyncio.create_task(close_connections())

    if not success:
        return {"status": "error", "message": "Користувач не в мережі"}
        
    return {"status": "ok", "message": f"Команду {payload.action} надіслано"}

@router.websocket("/ws/status")
async def websocket_endpoint(websocket: WebSocket, token: Optional[str] = Query(None)):
    payload = decode_access_token(token) if token else None
    if not payload:
        await websocket.close(code=1008)
        return

    try:
        user_id = int(payload.get("sub", 0))
    except:
        await websocket.close(code=1008)
        return

    full_name = payload.get("full_name", "Unknown")
    await manager.connect(websocket, user_id, full_name)
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
