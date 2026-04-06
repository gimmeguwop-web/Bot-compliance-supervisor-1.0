"""
WebSocket router for real-time task updates.
Provides live progress tracking for document validation tasks.
"""
import json
from typing import Dict, List, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from app.core.logger import logger

router = APIRouter()

# Хранилище активных подключений: task_id -> list[WebSocket]
active_connections: Dict[str, List[WebSocket]] = {}


@router.websocket("/ws/tasks")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for subscribing to task updates."""
    await websocket.accept()
    task_id = None
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "subscribe":
                task_id = message.get("task_id")
                if not task_id:
                    await websocket.send_json({
                        "type": "error", 
                        "message": "Task ID required"
                    })
                    continue
                
                if task_id not in active_connections:
                    active_connections[task_id] = []
                active_connections[task_id].append(websocket)
                
                logger.info(f"Client subscribed to task {task_id}")
                await websocket.send_json({
                    "type": "subscribed",
                    "task_id": task_id,
                    "message": "Successfully subscribed to updates"
                })
            
            elif message.get("type") == "unsubscribe":
                if task_id and task_id in active_connections:
                    if websocket in active_connections[task_id]:
                        active_connections[task_id].remove(websocket)
                    if not active_connections[task_id]:
                        del active_connections[task_id]
                task_id = None
                
    except WebSocketDisconnect:
        if task_id and task_id in active_connections:
            if websocket in active_connections[task_id]:
                active_connections[task_id].remove(websocket)
            if not active_connections[task_id]:
                del active_connections[task_id]
        logger.info(f"Client disconnected from task {task_id}")


async def broadcast_task_update(task_id: str, data: Dict[str, Any]):
    """Broadcast task status updates to all subscribed clients."""
    if task_id in active_connections:
        disconnected = []
        for connection in active_connections[task_id]:
            try:
                await connection.send_json({
                    "type": "update",
                    "data": data
                })
            except Exception as e:
                logger.warning(f"Failed to send update to client: {e}")
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for conn in disconnected:
            if conn in active_connections.get(task_id, []):
                active_connections[task_id].remove(conn)
        if task_id in active_connections and not active_connections[task_id]:
            del active_connections[task_id]


__all__ = ["broadcast_task_update"]
