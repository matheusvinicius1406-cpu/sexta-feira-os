"""
Configuration for Sexta-Feira OS — Private Local Cognitive Kernel.

Design principles (do not violate):
  * LOCAL-ONLY: the brain runs on your machine (Ollama). No cloud LLM. Ever.
  * SINGLE-OWNER: exactly one owner. No open registration.
  * PRIVATE-BY-DEFAULT: no telemetry, no external egress, data stays on disk.
"""
import os
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

    # Treat an unauthenticated request as the owner. Convenience for a local HUD
    # talking to a loopback kernel — OFF by default, and ignored entirely unless
    # environment is development AND access_mode is loopback (see auth/jwt.py).
    # It used to be implicitly on for every dev kernel, including LAN-bound ones.
    auth_dev_bypass: bool = False

    # ============ Tuning measured by app/brain/optimizer.py ============
    # All four are Ollama knobs. 0 / "" means "let Ollama decide", which is the
    # right default for a machine nobody has measured yet — a guessed number is
    # worse than the library's, and the optimizer exists to replace guesses.
    #
    # num_ctx caps how much context is READ per turn. Past the knee the model
    # pays to read context it will not use and the first token arrives late.
    brain_num_ctx: int = 0
    # A turn carrying an IMAGE does not fit in Ollama's 4096-token default, and
    # "let Ollama decide" is the wrong answer only in this one case. Measured on
    # the first real photo through /chat: 5791 tokens against a 4096 ceiling —
    # the picture is worth thousands before persona, recalled memories and the
    # tool specs are even counted. Ollama answers that with a flat 400, so the
    # brain did not see badly, it did not see at all.
    #
    # This is a FLOOR, applied only when images are attached. A text turn keeps
    # whatever brain_num_ctx says, because context is KV cache the CPU pays for
    # whether the tokens get used or not.
    brain_num_ctx_vision: int = 8192
    # num_thread: more is not monotonically better; cores contend for the memory
    # bus, and the last core is also the one the OS and this kernel need.
    brain_num_thread: int = 0
    # num_batch for embeddings, which run in the background while you talk.
    embedding_num_batch: int = 0
    # How long a model stays resident after its last use.
    brain_keep_alive: str = "10m"
    # Only consulted when VISION_MODEL names a model OTHER than the brain. When
    # one model does both — the default — this must not apply: Ollama's
    # keep_alive is per model and last-write-wins, so a 30s vision call would
    # schedule the brain's own eviction seconds after it looked at a photo.
    # See vision_keep_alive_resolved.
    vision_keep_alive: str = "30s"
    # Prune the history before sending it: drop spent tool payloads, then slide
    # a window over what is left.
    prompt_compression: bool = True
    # The budget compression targets when BRAIN_NUM_CTX has not been measured
    # yet (0 = "let Ollama decide", which defaults to 4096 for most models).
    # Without this, an unmeasured machine got NO compression at all — the
    # setting above was a no-op until the owner ran the optimizer once. 3072 is
    # ~75% of that 4096 default, leaving headroom for the reply so the model
    # is not generating right up against its own read ceiling. A measured
    # BRAIN_NUM_CTX always wins over this guess.
    prompt_compression_max_tokens: int = 3072

    # ============ Local Brain (Ollama) ============
    # This is the ONLY inference backend. It runs on your machine.
    ollama_endpoint: str = "http://127.0.0.1:11434"
    # ONE model, every job: it thinks, it acts, and it sees.
    #
    # It used to be two, and the split cost more than it bought:
    #   * qwen2.5:3b could call tools but was blind.
    #   * llava:7b could see but reports ["completion", "vision"] with NO
    #     "tools", so it refused every tool-calling request outright.
    # Two models meant two residents evicting each other from RAM — a single
    # camera frame pushed the chat model out and the next message paid a cold
    # load. Worse, no turn could ever look at an image AND act on what it saw:
    # those were different models, and only one of them had hands.
    #
    # qwen3-vl:2b reports ["completion", "tools", "vision", "thinking"] — the
    # whole assistant in 1.9 GB, and it is the largest size this reference
    # machine (2 cores / ~12 GB RAM) can actually answer on: the 4b is
    # measurably better but far too slow on it. Whatever you put here needs
    # BOTH "tools" and "vision"; the kernel checks at boot and says so if it
    # doesn't (see app/kernel/pipeline/steps/core_steps.py).
    brain_model: str = "qwen3-vl:2b"
    # NOT a chat model and not merged into the brain: an embedder turns text
    # into a vector for semantic recall, costs 274 MB, and running that job on
    # a 4B generative model would be slower and worse at it.
    embedding_model: str = "nomic-embed-text"
    # qwen3-vl can "think" before answering. On a CPU box that spends the reply
    # budget on reasoning nobody reads and pushes first-token latency into
    # minutes. Ollama rejects this flag on models without the capability, so it
    # is only ever sent when the brain reports "thinking".
    brain_thinking: bool = False
    brain_temperature: float = 0.7
    # This is a CEILING on generation (`num_predict`), paid in full whenever the
    # model doesn't stop on its own — and on CPU it routinely doesn't. The old
    # default (2048) made a rambling reply take ~7.5 minutes; a first "fix"
    # to 320 was WORSE — measured directly against Ollama with think:false
    # (ignored by this model — see brain_thinking below), qwen3-vl spent
    # 800-1100 tokens on a <think> block before answering EVEN A GREETING,
    # every single time. 320 didn't shorten the answer, it just guaranteed
    # the model got cut off mid-thought and returned nothing (see
    # LocalBrain._post_chat's thinking-retry — that band-aid exists because
    # of this). 1536 is calibrated with headroom above the measured ~1106
    # tokens a trivial question needed to actually converge to a real reply
    # (`done_reason: "stop"`, not "length"). This does not make replies
    # fast — nothing here can, short of a model that actually stops
    # thinking when told to — it makes them CORRECT instead of empty.
    brain_max_tokens: int = 1536
    brain_context_messages: int = 12
    # Agentic tool-calling: let the brain act on its own (remember/recall/automations)
    # during a normal conversation — driven by voice/chat from the phone, no terminal.
    tools_enabled: bool = True
    # optimizer.py's own _analyse() has recommended 2 here since it was written
    # ("cada rodada é uma inferência inteira; em CPU o custo de uma quarta
    # rodada supera o que ela costuma acrescentar") but the default stayed at
    # 4 — the finding was never actually applied. On CPU each extra round is
    # tens of seconds to minutes; 2 still lets the model call a tool, see the
    # result, and act on it once, which covers the common case.
    tool_max_rounds: int = 2
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

    # ============ Agent — Cognitive Pulse (the kernel's own initiative) ============
    # The kernel is an agent, not only a chat endpoint: on an interval it wakes,
    # looks at the present (World Model), the goals (Planning), the lessons
    # (Learning) and the pending proposals, judges whether anything is worth
    # doing RIGHT NOW, and either DOES it (read/reversible tools) or PROPOSES it
    # to the owner (anything that changes the world waits for confirmation — the
    # "age com confirmação" mode). Disable to go back to a purely reactive
    # kernel. The tick logic is a pure method (`CognitivePulse.tick`), so the
    # loop is as testable as the scheduler's run_due.
    agent_pulse_enabled: bool = True
    agent_pulse_interval_seconds: int = 600
    # How long an executed safe action is remembered before the same (tool,args)
    # may run again — stops the pulse from repeating itself every cycle.
    agent_pulse_cooldown_seconds: int = 3600
    # The judgment call is skipped when the digest is byte-identical to the
    # last one judged AND that judgment was {"nothing": true} — at the default
    # interval, an idle owner was paying for the same "nothing" answer 144
    # times a day. A digest that changes (a goal crosses an hour-until-due
    # boundary, a new lesson lands, a proposal resolves) always gets judged
    # again, so this trades nothing the deterministic scan couldn't already
    # tell you were the same. True restores the old always-judge behaviour.
    agent_pulse_judge_when_idle: bool = False

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
    # a generic "related". Costs one small local LLM call per new edge — up to
    # graph_autolink_k of them per fact remembered, ON TOP of whatever inference
    # produced the reply. Off by default because nothing reads the label back:
    # recall_graph ranks purely on similarity*decay*weight, and the prompt only
    # ever shows a memory's CONTENT, never its relation. Worse, `relation` is
    # part of link()'s idempotency key, so a non-deterministic label on the same
    # pair (re-remembered, or the LLM answering differently) files a SECOND
    # edge instead of updating the first. A visualization nice-to-have was
    # quietly both the biggest inference cost per turn and a graph-correctness
    # bug; turn it on only if you want the labels for the graph view.
    graph_relation_labels: bool = False

    # ============ Vision (local, offline) ============
    # The brain sees for itself — camera frames, screenshots, documents, OCR.
    #
    # Empty is the answer, not a missing value: it means "whichever model is
    # BRAIN_MODEL", which is the entire point of having one. Set this only to
    # deliberately send images somewhere else than the model holding the
    # conversation, and know that you are paying for a second resident model
    # again. Read it through `vision_model_resolved`, never raw.
    vision_enabled: bool = True
    vision_model: str = ""
    vision_max_image_dim: int = 1024  # resize larger images
    vision_jpeg_quality: int = 85

    @property
    def vision_model_resolved(self) -> str:
        """The model that actually receives images. Empty VISION_MODEL = the brain."""
        return self.vision_model or self.brain_model

    @property
    def vision_shares_the_brain(self) -> bool:
        """Is the model that sees the same one that talks? Normally yes."""
        return self.vision_model_resolved == self.brain_model

    @property
    def vision_keep_alive_resolved(self) -> str:
        """How long to hold the model that just looked at an image.

        When it IS the brain, the answer has to be the brain's own keep_alive.
        Ollama tracks keep_alive per model with last-write-wins, so passing the
        short vision value here would let a single photo schedule the brain's
        eviction 30 seconds later — the very RAM thrash that having one model
        was meant to end, reintroduced by a setting nobody would think to look at.
        """
        return self.brain_keep_alive if self.vision_shares_the_brain else self.vision_keep_alive

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
    # Load the speech model during boot instead of at the first spoken word.
    # Loading costs ~2 min on CPU, and paid on first use it is indistinguishable
    # from the assistant being deaf. Off for tests and for anything that boots
    # the kernel just to poke at it — half a gigabyte of model to run a unit
    # test is pure cost.
    stt_warm_on_boot: bool = True
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
    # Outbound URL firewall (netguard.py): the HTTP node refuses internal
    # destinations by default — loopback, private/LAN IPs, link-local, cloud
    # metadata. A host listed here is explicitly allowed (e.g. a home NAS you
    # want automations to reach). Empty = nothing internal, ever.
    teia_allowed_outbound_hosts: list[str] = []
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
        # Overridable so tests can point this at a file that does not exist —
        # see conftest.py. pydantic-settings reads env_file with its OWN
        # DotEnvSettingsSource, independent of the top-level `dotenv.load_dotenv`
        # main.py calls; conftest.py stubs THAT function to keep tests off the
        # developer's real .env, which silently did nothing to stop THIS path.
        # It never surfaced because no .env existed on the reference dev
        # machine — the day one did, every test started reading the owner's
        # real local settings (AGENT_PULSE_ENABLED, model choice, ...).
        env_file = os.environ.get(
            "SEXTA_ENV_FILE", str(Path(__file__).resolve().parents[3] / ".env")
        )
        case_sensitive = False
        extra = "ignore"
        # list[str] fields (teia_allowed_paths, teia_shell_allowlist, ...) are
        # JSON-decoded by pydantic-settings when the env var is SET, and both
        # ship in .env.template as a blank line ("separe por vírgula" — empty
        # means none). A blank string is not valid JSON, so every fresh boot
        # that follows the template as written crashed here before the app
        # ever started. env_ignore_empty makes a blank env var behave like an
        # unset one (falls back to the field default) instead of being handed
        # to json.loads. No string field relies on "" from the env overriding
        # a non-empty class default, so this changes nothing for those.
        env_ignore_empty = True

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
