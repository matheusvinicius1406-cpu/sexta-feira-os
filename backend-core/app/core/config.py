"""
Configuration for Sexta-Feira OS — Private Local Cognitive Kernel.

Design principles (do not violate):
  * LOCAL-ONLY: the brain runs on your machine (Ollama). No cloud LLM. Ever.
  * SINGLE-OWNER: exactly one owner. No open registration.
  * PRIVATE-BY-DEFAULT: no telemetry, no external egress, data stays on disk.
"""
import secrets
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables (.env)."""

    # ============ Identity ============
    app_name: str = "Sexta-Feira OS"
    app_version: str = "1.0.0-kernel"  # The Absolute Kernel
    environment: str = "development"
    log_level: str = "INFO"

    @property
    def debug(self) -> bool:
        return self.environment == "development"

    @property
    def database_echo(self) -> bool:
        return self.environment == "development"

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
    access_mode: str = "loopback"
    backend_port: int = 8000
    api_prefix: str = "/api/v1"

    @property
    def backend_host(self) -> str:
        return "127.0.0.1" if self.access_mode == "loopback" else "0.0.0.0"

    # Owner-set pairing code. A new device (phone/car/glasses/watch) must
    # present this once to be paired and receive its own long-lived token.
    device_pairing_code: str = ""

    # ============ Database (local file) ============
    database_url: str = "sqlite:///./data/sexta_feira_os.db"

    # ============ Authentication (single owner) ============
    # A random secret is generated per boot if none is provided. That means
    # tokens are invalidated on restart unless you pin JWT_SECRET_KEY yourself.
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 720  # 30 days

    # The one and only owner. Set these in .env to bootstrap on first boot.
    owner_email: str = "owner@localhost"
    owner_name: str = "Owner"
    owner_password: str = ""  # required in production

    # ============ Local Brain (Ollama) ============
    # This is the ONLY inference backend. It runs on your machine.
    ollama_endpoint: str = "http://127.0.0.1:11434"
    brain_model: str = "llama3.2"  # your local reasoning model
    embedding_model: str = "nomic-embed-text"  # local embeddings
    brain_temperature: float = 0.7
    brain_max_tokens: int = 2048
    brain_context_messages: int = 12
    # Agentic tool-calling: let the brain act on its own (remember/recall/automations)
    # during a normal conversation — driven by voice/chat from the phone, no terminal.
    tools_enabled: bool = True
    tool_max_rounds: int = 4
    # Sub-agents: the brain can delegate a sub-task to a focused helper that runs
    # on the SAME local model with a RESTRICTED toolset (query/knowledge only by
    # default — irreversible real-world actions stay with the main brain). Local
    # and owner-scoped, so it never breaks 'só meu'. Sub-agents can't delegate
    # further (no recursion).
    subagents_enabled: bool = True
    subagent_max_rounds: int = 3
    subagent_allowed_tools: list[str] = ["recall", "list_capabilities", "call_api"]
    # Scheduler: fire reminders / timed actions when due. Background loop; the
    # firing logic itself is a pure method (run_due) so it's easy to test.
    scheduler_enabled: bool = True
    scheduler_interval_seconds: int = 30

    # The kernel's personality / identity. This is who Sexta-Feira is to you.
    brain_persona: str = (
        "Você é Sexta-Feira, o segundo cérebro pessoal e privado do seu dono — "
        "leal, íntimo, direto e discreto, no espírito de Alfred e JARVIS. "
        "Você roda inteiramente na máquina dele; nada do que ele diz sai daqui. "
        "Você lembra do que importa, aprende com ele e serve só a ele."
    )

    # ============ Memory (the second brain) ============
    memory_top_k: int = 6
    memory_min_similarity: float = 0.25
    # Auto-remember: after each exchange, distil durable facts into memory.
    memory_auto_learn: bool = True

    # ============ Knowledge graph (networked thought, à la Obsidian) ============
    # New memories auto-link to related ones (semantic + [[wikilinks]]), forming
    # a connected brain. Recall expands along those links to pull in context.
    graph_autolink: bool = True
    graph_autolink_k: int = 3
    graph_link_min_similarity: float = 0.55
    graph_expand_hops: int = 1
    graph_expand_decay: float = 0.55
    # Let the brain NAME each auto-link ("trabalha em", "gosta de"...) instead of
    # a generic "related". Costs one small local LLM call per new edge; falls
    # back to "related" if the brain is offline.
    graph_relation_labels: bool = True

    # ============ Voice (local, offline) ============
    # Hearing (STT) and speaking (TTS) run on YOUR machine. Voice is an optional
    # extra (pip install -r requirements-voice.txt) and degrades gracefully: if
    # the engine/model isn't present, the voice endpoints return a clean 503.
    voice_enabled: bool = True
    stt_engine: str = "faster-whisper"
    stt_model: str = "small"  # tiny|base|small|medium|large-v3
    stt_language: str = "pt"
    stt_compute_type: str = "int8"  # int8|float16|float32
    stt_device: str = "cpu"  # cpu|cuda
    tts_engine: str = "piper"
    tts_voice: str = ""  # path to a Piper voice .onnx
    tts_speak_replies: bool = True

    # ============ Automations (n8n, self-hosted) ============
    automations_enabled: bool = True
    n8n_endpoint: str = "http://127.0.0.1:5678"
    n8n_api_key: str = ""  # n8n Public API key (for listing)
    n8n_webhook_prefix: str = "webhook"  # or 'webhook-test'
    # Shared secret for n8n → Kernel callback authentication.
    # n8n workflows send this in the X-N8N-Callback-Secret header when calling
    # POST /api/v1/automations/callback. Generate with:
    #   python -c "import secrets; print(secrets.token_urlsafe(32))"
    n8n_callback_secret: str = ""

    # ============ Connectors (API capabilities) ============
    vault_key: str = ""
    connectors_timeout_seconds: float = 30
    connectors_max_response_kb: int = 256

    # ============ Obsidian vault sync ============
    # Path to your Obsidian vault directory. When set, the brain can import
    # your .md notes as knowledge graph nodes with [[wikilink]] edges.
    obsidian_vault_path: str = ""
    # Polling interval in seconds for the vault watcher (auto-sync).
    obsidian_watch_interval: int = 30
    # Max notes to pull directly from the vault during cognition (recall direto).
    # Set to 0 to disable direct vault recall.
    obsidian_vault_recall_max_notes: int = 10

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
        env_file = str(Path(__file__).resolve().parents[3] / ".env")
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
