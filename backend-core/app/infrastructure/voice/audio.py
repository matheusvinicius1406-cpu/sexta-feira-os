"""
Voice System - Speech Recognition (STT) and Text-to-Speech (TTS)
"""
from typing import Optional, AsyncIterator
from dataclasses import dataclass
from enum import Enum
import logging
import asyncio

logger = logging.getLogger(__name__)


class VoiceFormat(str, Enum):
    """Audio format"""
    WAV = "wav"
    MP3 = "mp3"
    OGG = "ogg"
    PCM = "pcm"


@dataclass
class VoiceConfig:
    """Voice configuration"""
    language: str = "en-US"
    sample_rate: int = 16000
    channels: int = 1
    format: VoiceFormat = VoiceFormat.PCM


class SpeechRecognitionService:
    """Speech-to-Text service using OpenAI Whisper"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "base"):
        """
        Initialize Whisper service
        
        Models: tiny, base, small, medium, large
        """
        self.api_key = api_key
        self.model = model
        self.whisper_model = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize Whisper model"""
        if self._initialized:
            return
        
        try:
            # Try using OpenAI API if api_key provided
            if self.api_key:
                logger.info("Using OpenAI Whisper API")
                self._use_api = True
            else:
                # Fall back to local Whisper
                try:
                    import whisper
                    logger.info(f"Loading local Whisper model: {self.model}")
                    self.whisper_model = whisper.load_model(self.model)
                    self._use_api = False
                except ImportError:
                    logger.warning("Whisper not installed. Install with: pip install openai-whisper")
                    self._use_api = None
            
            self._initialized = True
        except Exception as e:
            logger.error(f"Failed to initialize Whisper: {e}")
    
    async def transcribe(
        self,
        audio_bytes: bytes,
        language: str = "en",
        config: Optional[VoiceConfig] = None
    ) -> str:
        """Transcribe audio to text"""
        if not self._initialized:
            await self.initialize()
        
        if self._use_api:
            return await self._transcribe_via_api(audio_bytes, language)
        elif self.whisper_model:
            return await self._transcribe_local(audio_bytes, language)
        else:
            raise RuntimeError("Whisper not available")
    
    async def _transcribe_via_api(self, audio_bytes: bytes, language: str) -> str:
        """Transcribe using OpenAI API"""
        import httpx
        
        async with httpx.AsyncClient() as client:
            files = {"file": ("audio.wav", audio_bytes, "audio/wav")}
            data = {"model": "whisper-1", "language": language}
            
            response = await client.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                files=files,
                data=data,
                timeout=60.0
            )
            response.raise_for_status()
            return response.json()["text"]
    
    async def _transcribe_local(self, audio_bytes: bytes, language: str) -> str:
        """Transcribe using local Whisper model"""
        # Save bytes to temp file
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(audio_bytes)
            temp_path = f.name
        
        try:
            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.whisper_model.transcribe(temp_path, language=language)
            )
            return result["text"]
        finally:
            os.unlink(temp_path)


class TextToSpeechService:
    """Text-to-Speech service"""
    
    def __init__(self, provider: str = "piper", voice: str = "en-US-hfc_female"):
        """
        Initialize TTS service
        
        Providers: piper, edge, google
        """
        self.provider = provider
        self.voice = voice
        self.piper_model = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize TTS model"""
        if self._initialized:
            return
        
        if self.provider == "piper":
            try:
                import piper
                logger.info(f"Loading Piper TTS model: {self.voice}")
                # Piper initialization would go here
                self._initialized = True
            except ImportError:
                logger.warning("Piper not installed. Install with: pip install piper-tts")
        elif self.provider == "edge":
            logger.info("Using Edge TTS")
            self._initialized = True
        else:
            logger.warning(f"Unknown TTS provider: {self.provider}")
        
        self._initialized = True
    
    async def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        speed: float = 1.0
    ) -> bytes:
        """Convert text to speech"""
        if not self._initialized:
            await self.initialize()
        
        selected_voice = voice or self.voice
        
        if self.provider == "piper":
            return await self._synthesize_piper(text, selected_voice, speed)
        elif self.provider == "edge":
            return await self._synthesize_edge(text, selected_voice, speed)
        else:
            raise RuntimeError(f"Unknown TTS provider: {self.provider}")
    
    async def _synthesize_piper(self, text: str, voice: str, speed: float) -> bytes:
        """Synthesize using Piper (local)"""
        try:
            import piper
            import io
            
            audio = io.BytesIO()
            
            # Piper synthesis logic
            loop = asyncio.get_event_loop()
            # This would use piper.synthesize() in real implementation
            
            return audio.getvalue()
        except Exception as e:
            logger.error(f"Piper synthesis failed: {e}")
            raise
    
    async def _synthesize_edge(self, text: str, voice: str, speed: float) -> bytes:
        """Synthesize using Edge TTS (Microsoft)"""
        try:
            import edge_tts
            
            # Split voice string (e.g., "en-US-AriaNeural")
            communicate = edge_tts.Communicate(
                text=text,
                voice=voice,
                rate=f"{int((speed - 1) * 100):+d}%"
            )
            
            audio_data = io.BytesIO()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data.write(chunk["data"])
            
            return audio_data.getvalue()
        except ImportError:
            logger.warning("edge-tts not installed. Install with: pip install edge-tts")
            raise
        except Exception as e:
            logger.error(f"Edge TTS synthesis failed: {e}")
            raise
    
    async def synthesize_stream(
        self,
        text: str,
        voice: Optional[str] = None,
        speed: float = 1.0
    ) -> AsyncIterator[bytes]:
        """Stream audio chunks as text is synthesized"""
        if not self._initialized:
            await self.initialize()
        
        selected_voice = voice or self.voice
        
        if self.provider == "edge":
            try:
                import edge_tts
                
                communicate = edge_tts.Communicate(
                    text=text,
                    voice=selected_voice,
                    rate=f"{int((speed - 1) * 100):+d}%"
                )
                
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        yield chunk["data"]
            except Exception as e:
                logger.error(f"Edge TTS streaming failed: {e}")
        else:
            # For non-streaming providers, yield all at once
            audio = await self.synthesize(text, selected_voice, speed)
            yield audio


class WakeWordEngine:
    """Wake word detection for voice activation"""
    
    def __init__(self, wake_word: str = "jarvis", sensitivity: float = 0.5):
        """
        Initialize wake word detection
        
        wake_word: Word to detect (e.g., "jarvis", "ok google", "hey siri")
        sensitivity: 0.0-1.0, higher = more sensitive but more false positives
        """
        self.wake_word = wake_word.lower()
        self.sensitivity = sensitivity
        self.detector = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize wake word detection"""
        if self._initialized:
            return
        
        try:
            # Try to use pvporcupine for wake word detection
            import pvporcupine
            
            # In production, provide access key
            self.detector = pvporcupine.create(
                keywords=[self.wake_word],
                sensitivities=[self.sensitivity]
            )
            self._initialized = True
            logger.info(f"Wake word engine initialized for: {self.wake_word}")
        except ImportError:
            logger.warning("pvporcupine not installed. Install with: pip install pvporcupine")
        except Exception as e:
            logger.error(f"Failed to initialize wake word engine: {e}")
    
    async def detect(self, audio_chunk: bytes) -> bool:
        """Detect if wake word is in audio"""
        if not self._initialized:
            await self.initialize()
        
        if not self.detector:
            # Fallback: simple substring matching
            return await self._simple_detect(audio_chunk)
        
        try:
            import struct
            
            # Convert bytes to PCM samples
            pcm = struct.unpack_from("h" * (len(audio_chunk) // 2), audio_chunk)
            
            # Process with detector
            keyword_index = self.detector.process(pcm)
            return keyword_index == 0  # 0 is our wake word
        except Exception as e:
            logger.error(f"Wake word detection failed: {e}")
            return False
    
    async def _simple_detect(self, audio_chunk: bytes) -> bool:
        """Simple substring-based wake word detection"""
        try:
            # Try to transcribe and check for wake word
            # This is a fallback for when pvporcupine is not available
            return self.wake_word in str(audio_chunk).lower()
        except:
            return False


class AudioPipeline:
    """Integrated audio processing pipeline"""
    
    def __init__(
        self,
        stt_service: Optional[SpeechRecognitionService] = None,
        tts_service: Optional[TextToSpeechService] = None,
        wake_word_engine: Optional[WakeWordEngine] = None
    ):
        self.stt = stt_service or SpeechRecognitionService()
        self.tts = tts_service or TextToSpeechService()
        self.wake_word = wake_word_engine or WakeWordEngine()
    
    async def initialize(self):
        """Initialize all audio components"""
        await self.stt.initialize()
        await self.tts.initialize()
        await self.wake_word.initialize()
        logger.info("Audio pipeline initialized")
    
    async def speech_to_text(self, audio_bytes: bytes, language: str = "en") -> str:
        """Convert speech to text"""
        return await self.stt.transcribe(audio_bytes, language)
    
    async def text_to_speech(self, text: str, voice: Optional[str] = None) -> bytes:
        """Convert text to speech"""
        return await self.tts.synthesize(text, voice)
    
    async def text_to_speech_stream(
        self,
        text: str,
        voice: Optional[str] = None
    ) -> AsyncIterator[bytes]:
        """Stream text-to-speech"""
        async for chunk in self.tts.synthesize_stream(text, voice):
            yield chunk
    
    async def is_wake_word_detected(self, audio_chunk: bytes) -> bool:
        """Check if wake word is detected"""
        return await self.wake_word.detect(audio_chunk)
