"""
Configuration for Sexta-Feira OS — Private Local Cognitive Kernel.

Design principles (do not violate):
  * LOCAL-ONLY: the brain runs on your machine (Ollama). No cloud LLM. Ever.
  * SINGLE-OWNER: exactly one owner. No open registration.
  * PRIVATE-BY-DEFAULT: no telemetry, no external egress, data stays on disk.
"""
import os
import secrets

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables (.env)."""

    # ============ Identity ============
    app_name: str = "Sexta-Feira OS"
    app_version: str = "1.0.0-kernel"  # The Absolute Kernel
    environment: str = os.getenv("ENVIRONMENT", "development")
    debug: bool = os.getenv("ENVIRONMENT", "development") == "development"
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    # ============ Server / Ambient access ============
    # The kernel is ONE private brain with MANY trusted bodies (phone, car,
    # glasses, watch). Devices reach it over your private network only.
    #
    #   access_mode = loopback  -> 127.0.0.1  (only this machine; safest default)
    #   access_mode = lan       -> 0.0.0.0    (other devices on your local network)
    #   access_mode = tunnel    -> 0.0.0.0    (reach via WireGuard/Tailscale — still private)
    #
    # It is NEVER meant to be exposed to the public internet. Use a private
    # tunnel (Tailscale/WireGuard) if you want it with you outside home.
    access_mode: str = os.getenv("ACCESS_MODE", "loopback")
    backend_port: int = int(os.getenv("BACKEND_PORT", "8000"))
    api_prefix: str = "/api/v1"

    @property
    def backend_host(self) -> str:
        return "127.0.0.1" if self.access_mode == "loopback" else "0.0.0.0"

    # Owner-set pairing code. A new device (phone/car/glasses/watch) must
    # present this once to be paired and receive its own long-lived token.
    device_pairing_code: str = os.getenv("DEVICE_PAIRING_CODE", "")

    # ============ Database (local file) ============
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./data/sexta_feira_os.db")
    database_echo: bool = os.getenv("ENVIRONMENT", "development") == "development"

    # ============ Authentication (single owner) ============
    # A random secret is generated per boot if none is provided. That means
    # tokens are invalidated on restart unless you pin JWT_SECRET_KEY yourself.
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "")
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = int(os.getenv("JWT_EXPIRATION_HOURS", "720"))  # 30 days

    # The one and only owner. Set these in .env to bootstrap on first boot.
    owner_email: str = os.getenv("OWNER_EMAIL", "owner@localhost")
    owner_name: str = os.getenv("OWNER_NAME", "Owner")
    owner_password: str = os.getenv("OWNER_PASSWORD", "")  # required in production

    # ============ Local Brain (Ollama) ============
    # This is the ONLY inference backend. It runs on your machine.
    ollama_endpoint: str = os.getenv("OLLAMA_ENDPOINT", "http://127.0.0.1:11434")
    brain_model: str = os.getenv("BRAIN_MODEL", "llama3.2")  # your local reasoning model
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")  # local embeddings
    brain_temperature: float = float(os.getenv("BRAIN_TEMPERATURE", "0.7"))
    brain_max_tokens: int = int(os.getenv("BRAIN_MAX_TOKENS", "2048"))
    brain_context_messages: int = int(os.getenv("BRAIN_CONTEXT_MESSAGES", "12"))

    # The kernel's personality / identity. This is who Sexta-Feira is to you.
    brain_persona: str = os.getenv(
        "BRAIN_PERSONA",
        "Você é Sexta-Feira, o segundo cérebro pessoal e privado do seu dono — "
        "leal, íntimo, direto e discreto, no espírito de Alfred e JARVIS. "
        "Você roda inteiramente na máquina dele; nada do que ele diz sai daqui. "
        "Você lembra do que importa, aprende com ele e serve só a ele.",
    )

    # ============ Memory (the second brain) ============
    memory_top_k: int = int(os.getenv("MEMORY_TOP_K", "6"))
    memory_min_similarity: float = float(os.getenv("MEMORY_MIN_SIMILARITY", "0.25"))
    # Auto-remember: after each exchange, distil durable facts into memory.
    memory_auto_learn: bool = os.getenv("MEMORY_AUTO_LEARN", "true").lower() == "true"

    # ============ Knowledge graph (networked thought, à la Obsidian) ============
    # New memories auto-link to related ones (semantic + [[wikilinks]]), forming
    # a connected brain. Recall expands along those links to pull in context.
    graph_autolink: bool = os.getenv("GRAPH_AUTOLINK", "true").lower() == "true"
    graph_autolink_k: int = int(os.getenv("GRAPH_AUTOLINK_K", "3"))
    graph_link_min_similarity: float = float(os.getenv("GRAPH_LINK_MIN_SIMILARITY", "0.55"))
    graph_expand_hops: int = int(os.getenv("GRAPH_EXPAND_HOPS", "1"))
    graph_expand_decay: float = float(os.getenv("GRAPH_EXPAND_DECAY", "0.55"))
    # Let the brain NAME each auto-link ("trabalha em", "gosta de"...) instead of
    # a generic "related". Costs one small local LLM call per new edge; falls
    # back to "related" if the brain is offline.
    graph_relation_labels: bool = os.getenv("GRAPH_RELATION_LABELS", "true").lower() == "true"

    # ============ Voice (local, offline) ============
    # Hearing (STT) and speaking (TTS) run on YOUR machine. Voice is an optional
    # extra (pip install -r requirements-voice.txt) and degrades gracefully: if
    # the engine/model isn't present, the voice endpoints return a clean 503.
    voice_enabled: bool = os.getenv("VOICE_ENABLED", "true").lower() == "true"
    stt_engine: str = os.getenv("STT_ENGINE", "faster-whisper")
    stt_model: str = os.getenv("STT_MODEL", "small")        # tiny|base|small|medium|large-v3
    stt_language: str = os.getenv("STT_LANGUAGE", "pt")
    stt_compute_type: str = os.getenv("STT_COMPUTE_TYPE", "int8")  # int8|float16|float32
    stt_device: str = os.getenv("STT_DEVICE", "cpu")        # cpu|cuda
    tts_engine: str = os.getenv("TTS_ENGINE", "piper")
    tts_voice: str = os.getenv("TTS_VOICE", "")             # path to a Piper voice .onnx
    tts_speak_replies: bool = os.getenv("TTS_SPEAK_REPLIES", "true").lower() == "true"

    # ============ Privacy ============
    # Loopback-only origins. The kernel refuses cross-origin browser calls.
    cors_origins: list[str] = [
        "http://localhost",
        "http://127.0.0.1",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]
    telemetry_enabled: bool = False  # hard off. Non-negotiable.

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"

    def resolve_jwt_secret(self) -> str:
        """
        Return the JWT secret. In production a strong secret MUST be provided;
        we fail fast instead of silently using an insecure default.
        In development we mint an ephemeral random secret per boot.
        """
        if self.jwt_secret_key:
            return self.jwt_secret_key
        if self.environment == "production":
            raise RuntimeError(
                "JWT_SECRET_KEY is required in production. "
                "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(48))\""
            )
        # Development: ephemeral secret (tokens reset on restart — that's fine locally).
        self.jwt_secret_key = secrets.token_urlsafe(48)
        return self.jwt_secret_key


# Singleton instance
settings = Settings()
