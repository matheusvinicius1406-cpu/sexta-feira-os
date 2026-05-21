"""
Chat Router - Conversation API endpoints with streaming support
"""
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from typing import Optional, AsyncIterator
import logging
import json
import uuid

from app.application.dtos.responses import (
    ChatMessageRequest, ConversationResponse, ChatMessageResponse,
    StreamingChatRequest
)
from app.core.config import settings
from app.core.security import get_current_user
from app.infrastructure.events.websocket import ConnectionManager, WebSocketHandler

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/chat", tags=["chat"])

# Global connection manager
connection_manager = ConnectionManager()


# ============ REST Endpoints ============

@router.post("/message", response_model=dict)
async def send_message(
    request: ChatMessageRequest,
    current_user = Depends(get_current_user),
    pipeline = Depends(lambda: None)  # Injected
):
    """Send a chat message"""
    try:
        user_id = current_user.id if hasattr(current_user, 'id') else current_user.get('id')
        
        # Process through pipeline
        result = await pipeline.process_message(
            user_id=user_id,
            conversation_id=request.conversation_id,
            message_content=request.content,
            prompt_type=request.prompt_type,
            stream=False
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Processing failed")
            )
        
        return {
            "success": True,
            "conversation_id": result["conversation_id"],
            "message": result["message"],
            "metadata": result["metadata"]
        }
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process message: {str(e)}"
        )


@router.get("/conversations")
async def list_conversations(
    limit: int = 20,
    current_user = Depends(get_current_user),
    pipeline = Depends(lambda: None)
):
    """List user's conversations"""
    try:
        user_id = current_user.id if hasattr(current_user, 'id') else current_user.get('id')
        
        conversations = await pipeline.list_conversations(user_id, limit)
        
        return {
            "success": True,
            "conversations": [
                {
                    "id": conv.id,
                    "created_at": conv.created_at.isoformat(),
                    "updated_at": conv.updated_at.isoformat(),
                    "message_count": len(conv.messages),
                    "last_message": conv.messages[-1].content[:100] if conv.messages else None
                }
                for conv in conversations
            ]
        }
    except Exception as e:
        logger.error(f"Error listing conversations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    current_user = Depends(get_current_user),
    pipeline = Depends(lambda: None)
):
    """Get specific conversation"""
    try:
        user_id = current_user.id if hasattr(current_user, 'id') else current_user.get('id')
        
        conversation = await pipeline.get_conversation(conversation_id, user_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        return {
            "success": True,
            "conversation": {
                "id": conversation.id,
                "created_at": conversation.created_at.isoformat(),
                "updated_at": conversation.updated_at.isoformat(),
                "messages": [m.to_dict() for m in conversation.messages]
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/message/stream")
async def stream_message(
    request: StreamingChatRequest,
    current_user = Depends(get_current_user),
    pipeline = Depends(lambda: None)
):
    """Stream chat response (Server-Sent Events style)"""
    async def generate_stream():
        try:
            user_id = current_user.id if hasattr(current_user, 'id') else current_user.get('id')
            
            # Process through pipeline with streaming
            async for chunk in pipeline.process_message(
                user_id=user_id,
                conversation_id=request.conversation_id,
                message_content=request.content,
                prompt_type=request.prompt_type,
                stream=True
            ):
                yield f"data: {json.dumps(chunk)}\n\n"
        except Exception as e:
            logger.error(f"Error in stream: {e}")
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
    
    from fastapi.responses import StreamingResponse
    return StreamingResponse(generate_stream(), media_type="text/event-stream")


# ============ WebSocket Endpoint ============

@router.websocket("/ws/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: str,
    pipeline = Depends(lambda: None)
):
    """WebSocket endpoint for real-time streaming"""
    # Create handler
    handler = WebSocketHandler(connection_manager, pipeline)
    
    try:
        await handler.handle_connection(websocket, user_id)
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket, user_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close(code=1011, reason=str(e))


@router.get("/ws/status/{user_id}")
async def websocket_status(
    user_id: str,
    current_user = Depends(get_current_user)
):
    """Check WebSocket connection status"""
    is_connected = user_id in connection_manager.active_connections
    return {
        "user_id": user_id,
        "connected": is_connected,
        "active_connections": len(connection_manager.active_connections.get(user_id, set()))
    }
