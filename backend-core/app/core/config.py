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
    brain_model: str = "llava:7b"  # your local reasoning model
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

    # ============ Vision (local, offline) ============
    # Vision analysis uses Ollama vision models (llava, bakllava, etc.)
    # for image understanding, camera analysis, and document OCR.
    vision_enabled: bool = True
    vision_model: str = ""  # auto-detect if empty (llava preferred)
    vision_max_image_dim: int = 1024  # resize larger images
    vision_jpeg_quality: int = 85
    # Web search engine (DuckDuckGo by default, no API key needed)
    web_search_enabled: bool = True

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
    tts_engine: str = "edge"  # edge | piper | voicebox
    tts_voice: str = ""  # path to a Piper voice .onnx
    tts_speak_replies: bool = True
    # VoiceBox integration (jamiepine/voicebox) — local voice studio
    # with 7 TTS engines, voice cloning, Whisper STT, REST API + MCP.
    # Runs as a separate process; the kernel calls it over HTTP.
    voicebox_enabled: bool = False  # set True to use VoiceBox instead of Piper
    voicebox_endpoint: str = "http://127.0.0.1:17493"  # VoiceBox REST API
    voicebox_tts_engine: str = "kokoro"  # kokoro|chatterbox|qwen3|luxtts|tada|chatterbox-turbo
    voicebox_voice_profile: str = ""  # name of a voice profile for cloning (optional)
    voicebox_clone_audio: str = ""  # path to reference audio for voice cloning (optional)

    # ============ Automations — Teia (Python-first, in-process) ============
    # The kernel's hands. Workflows are Python objects executed by our own
    # orchestrator + worker pool; there is no external automation runtime and no
    # Node.js. See ADR-0013 and docs/jarvis/architecture/AUTOMATION_PLATFORM.md.
    automations_enabled: bool = True
    # How many nodes of ONE execution may run at the same time.
    teia_max_parallel: int = 4
    # Runaway guards: an automation that exceeds either of these is stopped.
    teia_max_nodes_per_run: int = 200
    teia_run_timeout_seconds: float = 900.0
    # How deep `sub_automacao` may nest before it's treated as recursion.
    teia_max_depth: int = 3
    # How often the trigger manager checks the clock (cron/interval resolution).
    teia_tick_seconds: int = 30
    # Timezone for cron triggers. Empty = this machine's local time.
    teia_timezone: str = ""
    # Cap on how often event triggers may fire, per workflow, per minute — the
    # backstop against two automations triggering each other forever.
    teia_event_fires_per_minute: int = 30
    # HTTP node limits.
    teia_http_timeout_seconds: float = 30.0
    teia_http_max_response_kb: int = 512
    # Where file nodes may read and write. The workspace is always allowed (and
    # created on boot); the Obsidian vault is added when configured.
    teia_workspace: str = str(Path(__file__).resolve().parents[2] / "data" / "teia")
    teia_allowed_paths: list[str] = []
    # Running local programs from a workflow: off by default. When enabled, only
    # the programs named here may run, and never through a shell.
    teia_shell_enabled: bool = False
    teia_shell_allowlist: list[str] = []
    # Install the built-in automation catalog for the owner on first boot.
    teia_seed_catalog: bool = True

    # ============ Connectors (API capabilities) ============
    vault_key: str = ""
    connectors_timeout_seconds: float = 30
    connectors_max_response_kb: int = 256

    # ============ gRPC server ============
    grpc_enabled: bool = True
    grpc_port: int = 50051
    grpc_max_workers: int = 10

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
        "http://localhost:3000",  # Vite dev server
        "http://127.0.0.1:3000",  # Vite dev server (IP)
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
