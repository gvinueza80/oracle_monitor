"""WebSocket handlers for real-time metric updates"""

import json
import logging
from typing import Set, Dict
from datetime import datetime

from fastapi import WebSocket, WebSocketDisconnect, Query
from uuid import UUID

from security.jwt import decode_token
from cache.redis_cache import redis_cache

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for real-time updates"""

    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, instance_id: str):
        """Register a new WebSocket connection"""
        await websocket.accept()

        if instance_id not in self.active_connections:
            self.active_connections[instance_id] = set()

        self.active_connections[instance_id].add(websocket)
        logger.info(f"Client connected to {instance_id}, total: {len(self.active_connections[instance_id])}")

    def disconnect(self, instance_id: str, websocket: WebSocket):
        """Unregister a WebSocket connection"""
        if instance_id in self.active_connections:
            self.active_connections[instance_id].discard(websocket)
            if not self.active_connections[instance_id]:
                del self.active_connections[instance_id]
            logger.info(f"Client disconnected from {instance_id}")

    async def broadcast(self, instance_id: str, message: dict):
        """Broadcast a message to all clients for an instance"""
        if instance_id not in self.active_connections:
            return

        disconnected = set()
        for connection in self.active_connections[instance_id]:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error sending message: {e}")
                disconnected.add(connection)

        # Remove disconnected clients
        for connection in disconnected:
            self.disconnect(instance_id, connection)

    async def send_personal(self, websocket: WebSocket, message: dict):
        """Send a message to a specific client"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")

    def get_client_count(self, instance_id: str) -> int:
        """Get number of connected clients for an instance"""
        return len(self.active_connections.get(instance_id, set()))


# Global connection manager
manager = ConnectionManager()


async def validate_websocket_token(token: str) -> dict:
    """Validate JWT token from WebSocket query parameter"""
    payload = decode_token(token)
    if not payload:
        raise ValueError("Invalid token")
    return payload


async def handle_metric_update(instance_id: str, metric_data: dict):
    """Handle incoming metric update and broadcast to clients"""
    message = {
        "type": "metric_update",
        "instance_id": instance_id,
        "data": metric_data,
        "timestamp": datetime.utcnow().isoformat()
    }

    await manager.broadcast(instance_id, message)


async def handle_alert_notification(instance_id: str, alert_data: dict):
    """Handle alert notification and broadcast to clients"""
    message = {
        "type": "alert_triggered",
        "instance_id": instance_id,
        "alert": alert_data,
        "timestamp": datetime.utcnow().isoformat()
    }

    await manager.broadcast(instance_id, message)


async def handle_session_change(instance_id: str, session_data: dict):
    """Handle session change notification"""
    message = {
        "type": "session_update",
        "instance_id": instance_id,
        "session": session_data,
        "timestamp": datetime.utcnow().isoformat()
    }

    await manager.broadcast(instance_id, message)


async def websocket_endpoint(
    websocket: WebSocket,
    instance_id: UUID,
    token: str = Query(...)
):
    """
    WebSocket endpoint for real-time metric updates

    Connect: ws://localhost:8000/api/ws/metrics/{instance_id}?token={jwt_token}
    """
    try:
        # Validate token
        try:
            payload = await validate_websocket_token(token)
        except ValueError:
            await websocket.close(code=4001, reason="Invalid token")
            return

        # Connect client
        await manager.connect(websocket, str(instance_id))

        # Send initial connection message
        await manager.send_personal(
            websocket,
            {
                "type": "connected",
                "instance_id": str(instance_id),
                "message": "Connected to real-time updates",
                "timestamp": datetime.utcnow().isoformat()
            }
        )

        # Keep connection alive and handle incoming messages
        while True:
            # Receive any incoming messages from client
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                message_type = message.get("type")

                # Handle ping/pong for keep-alive
                if message_type == "ping":
                    await manager.send_personal(
                        websocket,
                        {"type": "pong", "timestamp": datetime.utcnow().isoformat()}
                    )

                # Handle subscription to specific metrics
                elif message_type == "subscribe":
                    metric_types = message.get("metric_types", [])
                    logger.info(f"Client subscribed to: {metric_types}")
                    await manager.send_personal(
                        websocket,
                        {
                            "type": "subscription_confirmed",
                            "metric_types": metric_types,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    )

            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON received: {data}")
                continue
            except Exception as e:
                logger.error(f"Error handling WebSocket message: {e}")

    except WebSocketDisconnect:
        manager.disconnect(str(instance_id), websocket)
        logger.info(f"Client disconnected from {instance_id}")

    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(str(instance_id), websocket)
