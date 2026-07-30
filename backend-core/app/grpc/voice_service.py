"""
VoiceStream gRPC service — bidirectional audio streaming.

Thin gateway: delegates to VoiceAdapter. No Kernel imports.
"""
from __future__ import annotations

import logging

from app.adapters.voice_adapter import VoiceAdapter
from app.grpc import voice_stream_pb2 as pb2
from app.grpc import voice_stream_pb2_grpc as pb2_grpc

logger = logging.getLogger("sexta-feira.grpc.voice")


class VoiceStreamService(pb2_grpc.VoiceStreamServicer):
    """gRPC servicer for bidirectional voice — delegates to VoiceAdapter."""

    def __init__(self) -> None:
        self._voice = VoiceAdapter()

    async def StreamVoice(self, request_iterator, context):
        if not self._voice.available:
            yield pb2.VoicePacket(
                event=pb2.VOICE_EVENT_ERROR,
                error=pb2.VoiceError(code="voice_unavailable",
                                     message="Voice system not loaded"),
            )
            return

        session_config = None
        audio_buffer = bytearray()
        sequence = 0

        async for packet in request_iterator:
            sequence += 1

            if packet.HasField("session_config"):
                session_config = packet.session_config
                logger.info("Voice session started: codec=%s sample_rate=%d",
                            pb2.AudioCodec.Name(session_config.codec),
                            session_config.sample_rate_hz)
                yield pb2.VoicePacket(event=pb2.VOICE_EVENT_UNSPECIFIED,
                                      session_config=session_config,
                                      sequence=sequence,
                                      timestamp_ns=packet.timestamp_ns)
                continue

            if packet.event == pb2.VOICE_EVENT_AUDIO_CHUNK and packet.HasField("audio_data"):
                audio_buffer.extend(packet.audio_data)
                yield pb2.VoicePacket(event=pb2.VOICE_EVENT_SILENCE,
                                      sequence=sequence,
                                      timestamp_ns=packet.timestamp_ns)
                continue

            if packet.event == pb2.VOICE_EVENT_END_OF_SPEECH and audio_buffer:
                try:
                    result = await self._voice.chat(bytes(audio_buffer))
                    if result:
                        if result.get("transcript"):
                            yield pb2.VoicePacket(
                                event=pb2.VOICE_EVENT_TRANSCRIPT,
                                transcript=result["transcript"],
                                sequence=sequence,
                            )
                        if result.get("reply"):
                            yield pb2.VoicePacket(
                                event=pb2.VOICE_EVENT_TRANSCRIPT,
                                transcript=result["reply"],
                                sequence=sequence + 1,
                            )
                        if result.get("audio") and session_config and session_config.speak_reply:
                            yield pb2.VoicePacket(
                                event=pb2.VOICE_EVENT_AUDIO_CHUNK,
                                audio_data=result["audio"],
                                sequence=sequence + 2,
                            )
                except Exception as exc:
                    logger.error("Voice processing error: %s", exc)
                    yield pb2.VoicePacket(
                        event=pb2.VOICE_EVENT_ERROR,
                        error=pb2.VoiceError(code="processing_error", message=str(exc)),
                        sequence=sequence,
                    )
                audio_buffer.clear()

            if packet.event == pb2.VOICE_EVENT_SESSION_END:
                yield pb2.VoicePacket(event=pb2.VOICE_EVENT_SESSION_END, sequence=sequence)
                return
