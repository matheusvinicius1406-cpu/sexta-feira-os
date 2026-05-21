"""
Voice Router - Speech recognition and synthesis endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, WebSocket
from fastapi.responses import StreamingResponse
import logging
from typing import Optional

from app.core.security import get_current_user
from app.core.di import get_container

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/voice", tags=["voice"])


@router.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    language: str = "en",
    current_user = Depends(get_current_user)
):
    """Transcribe audio file to text"""
    try:
        # Read file
        audio_bytes = await file.read()
        
        # Get audio pipeline
        container = get_container()
        audio_pipeline = container.ai_orchestrator  # TODO: Add to container
        
        if not hasattr(container, 'audio_pipeline'):
            # Create temporary pipeline
            from app.infrastructure.voice.audio import AudioPipeline
            audio_pipeline = AudioPipeline()
            await audio_pipeline.initialize()
            container.audio_pipeline = audio_pipeline
        
        # Transcribe
        text = await container.audio_pipeline.speech_to_text(audio_bytes, language)
        
        return {
            "success": True,
            "text": text,
            "language": language
        }
    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/synthesize")
async def synthesize_text(
    text: str,
    voice: Optional[str] = None,
    speed: float = 1.0,
    current_user = Depends(get_current_user)
):
    """Synthesize text to speech (returns audio file)"""
    try:
        if not text or len(text) > 5000:
            raise HTTPException(status_code=400, detail="Text too long or empty")
        
        # Get audio pipeline
        container = get_container()
        
        if not hasattr(container, 'audio_pipeline'):
            from app.infrastructure.voice.audio import AudioPipeline
            audio_pipeline = AudioPipeline()
            await audio_pipeline.initialize()
            container.audio_pipeline = audio_pipeline
        
        # Synthesize
        audio_bytes = await container.audio_pipeline.text_to_speech(text, voice)
        
        return StreamingResponse(
            iter([audio_bytes]),
            media_type="audio/wav",
            headers={"Content-Disposition": "attachment; filename=speech.wav"}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Synthesis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/synthesize/stream")
async def synthesize_stream(
    text: str,
    voice: Optional[str] = None,
    speed: float = 1.0,
    current_user = Depends(get_current_user)
):
    """Stream synthesized speech"""
    try:
        if not text or len(text) > 5000:
            raise HTTPException(status_code=400, detail="Text too long or empty")
        
        async def generate_stream():
            container = get_container()
            
            if not hasattr(container, 'audio_pipeline'):
                from app.infrastructure.voice.audio import AudioPipeline
                audio_pipeline = AudioPipeline()
                await audio_pipeline.initialize()
                container.audio_pipeline = audio_pipeline
            
            async for chunk in container.audio_pipeline.text_to_speech_stream(text, voice):
                yield chunk
        
        return StreamingResponse(
            generate_stream(),
            media_type="audio/wav"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Streaming synthesis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.websocket("/stream")
async def websocket_voice_stream(websocket: WebSocket):
    """
    WebSocket for real-time voice interaction
    
    Protocol:
    - receive: {"type": "audio", "data": base64_audio}
    - send: {"type": "text", "content": transcribed_text}
    - send: {"type": "response", "audio": base64_audio}
    """
    await websocket.accept()
    
    try:
        container = get_container()
        
        if not hasattr(container, 'audio_pipeline'):
            from app.infrastructure.voice.audio import AudioPipeline
            audio_pipeline = AudioPipeline()
            await audio_pipeline.initialize()
            container.audio_pipeline = audio_pipeline
        
        while True:
            data = await websocket.receive_json()
            
            if data.get("type") == "audio":
                # Decode audio
                import base64
                audio_bytes = base64.b64decode(data["data"])
                
                # Transcribe
                try:
                    text = await container.audio_pipeline.speech_to_text(audio_bytes)
                    
                    # Send back transcription
                    await websocket.send_json({
                        "type": "text",
                        "content": text
                    })
                except Exception as e:
                    await websocket.send_json({
                        "type": "error",
                        "error": str(e)
                    })
            
            elif data.get("type") == "synthesize":
                # Synthesize response
                try:
                    text = data.get("text", "")
                    audio_bytes = await container.audio_pipeline.text_to_speech(text)
                    
                    import base64
                    audio_b64 = base64.b64encode(audio_bytes).decode()
                    
                    await websocket.send_json({
                        "type": "audio",
                        "data": audio_b64
                    })
                except Exception as e:
                    await websocket.send_json({
                        "type": "error",
                        "error": str(e)
                    })
    
    except Exception as e:
        logger.error(f"WebSocket voice error: {e}")
        await websocket.close(code=1011, reason=str(e))
