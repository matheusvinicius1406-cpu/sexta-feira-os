"""
WebSocket Streaming - Real-time response streaming
"""
from typing import Optional, Dict, Any, Set
import logging
import json
import asyncio
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for real-time streaming"""
    
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}  # user_id -> set of connections
    
    async def connect(self, websocket: WebSocket, user_id: str) -> None:
        """Register WebSocket connection"""
        await websocket.accept()
        
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        
        self.active_connections[user_id].add(websocket)
        logger.info(f"WebSocket connected for user {user_id}")
    
    def disconnect(self, websocket: WebSocket, user_id: str) -> None:
        """Unregister WebSocket connection"""
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        
        logger.info(f"WebSocket disconnected for user {user_id}")
    
    async def broadcast_to_user(self, user_id: str, data: Dict[str, Any]) -> None:
        """Broadcast message to all connections of a user"""
        if user_id not in self.active_connections:
            return
        
        message = json.dumps(data)
        disconnected = set()
        
        for connection in self.active_connections[user_id]:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error sending to WebSocket: {e}")
                disconnected.add(connection)
        
        # Clean up disconnected
        for conn in disconnected:
            self.disconnect(conn, user_id)
    
    async def broadcast_stream(
        self,
        user_id: str,
        stream_id: str,
        response_stream,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Stream response to user connections"""
        try:
            # Send start event
            await self.broadcast_to_user(user_id, {
                "type": "stream_start",
                "stream_id": stream_id,
                "metadata": metadata or {}
            })
            
            # Stream tokens
            async for chunk in response_stream:
                if isinstance(chunk, dict):
                    # Already formatted
                    chunk["stream_id"] = stream_id
                    await self.broadcast_to_user(user_id, chunk)
                else:
                    # Text chunk
                    await self.broadcast_to_user(user_id, {
                        "type": "token",
                        "stream_id": stream_id,
                        "content": chunk
                    })
                
                # Allow other tasks to run
                await asyncio.sleep(0)
            
            # Send complete event
            await self.broadcast_to_user(user_id, {
                "type": "stream_complete",
                "stream_id": stream_id
            })
        except Exception as e:
            logger.error(f"Error in stream broadcast: {e}")
            await self.broadcast_to_user(user_id, {
                "type": "stream_error",
                "stream_id": stream_id,
                "error": str(e)
            })


class WebSocketHandler:
    """Handles WebSocket communication protocol"""
    
    def __init__(self, connection_manager: ConnectionManager, pipeline):
        self.manager = connection_manager
        self.pipeline = pipeline
    
    async def handle_connection(
        self,
        websocket: WebSocket,
        user_id: str
    ) -> None:
        """Handle WebSocket connection lifecycle"""
        await self.manager.connect(websocket, user_id)
        
        try:
            while True:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                await self._handle_message(websocket, user_id, message)
        except WebSocketDisconnect:
            self.manager.disconnect(websocket, user_id)
            logger.info(f"WebSocket disconnected for user {user_id}")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            self.manager.disconnect(websocket, user_id)
    
    async def _handle_message(
        self,
        websocket: WebSocket,
        user_id: str,
        message: Dict[str, Any]
    ) -> None:
        """Handle incoming WebSocket message"""
        msg_type = message.get("type")
        
        if msg_type == "chat":
            await self._handle_chat_message(user_id, message)
        elif msg_type == "ping":
            await websocket.send_text(json.dumps({"type": "pong"}))
        else:
            logger.warning(f"Unknown message type: {msg_type}")
    
    async def _handle_chat_message(
        self,
        user_id: str,
        message: Dict[str, Any]
    ) -> None:
        """Handle chat message"""
        content = message.get("content", "")
        conversation_id = message.get("conversation_id")
        stream = message.get("stream", True)
        stream_id = message.get("stream_id", f"stream_{asyncio.current_task().get_name()}")
        
        if not content:
            await self.manager.broadcast_to_user(user_id, {
                "type": "error",
                "error": "Empty message content"
            })
            return
        
        try:
            # Process message through pipeline
            response = await self.pipeline.process_message(
                user_id=user_id,
                conversation_id=conversation_id,
                message_content=content,
                stream=stream
            )
            
            # Broadcast result
            if stream:
                await self.manager.broadcast_stream(
                    user_id,
                    stream_id,
                    response,
                    metadata={"type": "chat"}
                )
            else:
                await self.manager.broadcast_to_user(user_id, response)
        except Exception as e:
            logger.error(f"Error processing chat message: {e}")
            await self.manager.broadcast_to_user(user_id, {
                "type": "error",
                "error": str(e)
            })


class StreamSession:
    """Manages a streaming session"""
    
    def __init__(self, session_id: str, user_id: str):
        self.session_id = session_id
        self.user_id = user_id
        self.active = True
        self.start_time = None
        self.end_time = None
    
    def __aiter__(self):
        return self
    
    async def __anext__(self):
        if not self.active:
            raise StopAsyncIteration
        # Yield streaming data
        # Implementation depends on parent stream
        raise StopAsyncIteration
