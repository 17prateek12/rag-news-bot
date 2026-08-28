import asyncio
import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import redis.asyncio as aioredis

from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["websocket"])


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("New WebSocket client connected. Total connections: %s", len(self.active_connections))

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info("WebSocket client disconnected. Remaining connections: %s", len(self.active_connections))

    async def broadcast(self, message: dict):
        logger.info("Broadcasting real-time message to %s clients: %s", len(self.active_connections), message)
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning("Failed to send message to connection, queueing for removal: %s", e)
                disconnected.append(connection)
        
        # Clean up any dead connections we failed to write to
        for conn in disconnected:
            self.disconnect(conn)


manager = ConnectionManager()


@router.websocket("/news")
async def websocket_news_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # We don't expect messages from clients, but we keep the read loop running
            # to detect client disconnects immediately (this raises WebSocketDisconnect)
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error("Error in websocket connection: %s", e)
        manager.disconnect(websocket)


async def redis_updates_listener():
    logger.info("Starting Redis Pub/Sub listener for 'news:updates' channel")
    while True:
        try:
            client = aioredis.from_url(settings.redis_url, decode_responses=True)
            pubsub = client.pubsub()
            await pubsub.subscribe("news:updates")
            logger.info("Subscribed to Redis 'news:updates' channel successfully")
            
            async for message in pubsub.listen():
                if message and message.get("type") == "message":
                    raw_data = message.get("data")
                    logger.info("Received update signal from Redis Pub/Sub: %s", raw_data)
                    try:
                        data = json.loads(raw_data)
                        await manager.broadcast(data)
                    except Exception as parse_err:
                        logger.error("Failed to parse pub/sub message payload: %s", parse_err)
        except asyncio.CancelledError:
            logger.info("Redis Pub/Sub listener task cancelled")
            break
        except Exception as e:
            logger.error("Redis Pub/Sub listener disconnected. Retrying in 5 seconds... Error: %s", e)
            await asyncio.sleep(5)
