"""
Configuration management for Sexта-Feira OS Backend
Enterprise-grade configuration with support for multi-cloud, multimodal AI, and advanced features
"""
import os
from typing import Optional, List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # ============ Service Configuration ============
    app_name: str = "Sexта-Feira OS"
    app_version: str = "0.2.0"  # Sprint 2: The Awakening
    environment: str = os.getenv("ENVIRONMENT", "development")
    debug: bool = environment == "development"
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    
    # ============ Server Configuration ============
    backend_host: str = os.getenv("BACKEND_HOST", "0.0.0.0")
    backend_port: int = int(os.getenv("BACKEND_PORT", "8000"))
    api_prefix: str = "/api/v2"
    
    # ============ Database Configuration ============
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./sexta_feira_os.db")
    sqlite_db_path: str = os.getenv("SQLITE_DB_PATH", "./data/sexta_feira_os.db")
    database_echo: bool = debug
    
    # ============ JWT & Authentication ============
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "dev-secret-key-change-in-production")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    jwt_expiration_hours: int = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))
    refresh_token_expiration_days: int = int(os.getenv("REFRESH_TOKEN_EXPIRATION_DAYS", "30"))
    access_token_expiration_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRATION_MINUTES", "30"))
    
    # ============ AI Provider Configuration ============
    openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
    claude_api_key: Optional[str] = os.getenv("CLAUDE_API_KEY")
    gemini_api_key: Optional[str] = os.getenv("GEMINI_API_KEY")
    ollama_endpoint: Optional[str] = os.getenv("OLLAMA_ENDPOINT")
    
    default_ai_provider: str = os.getenv("DEFAULT_AI_PROVIDER", "gemini")
    ai_model_gemini: str = os.getenv("AI_MODEL_GEMINI", "gemini-2.0-flash")
    ai_model_openai: str = os.getenv("AI_MODEL_OPENAI", "gpt-4-turbo")
    ai_model_claude: str = os.getenv("AI_MODEL_CLAUDE", "claude-3-opus")
    
    # ============ AI Routing & Optimization ============
    ai_routing_strategy: str = os.getenv("AI_ROUTING_STRATEGY", "fallback_chain")
    ai_default_temperature: float = float(os.getenv("AI_DEFAULT_TEMPERATURE", "0.7"))
    ai_default_max_tokens: int = int(os.getenv("AI_DEFAULT_MAX_TOKENS", "2000"))
    ai_context_window_size: int = int(os.getenv("AI_CONTEXT_WINDOW_SIZE", "100000"))
    
    # ============ Memory & Embeddings ============
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    vector_store_type: str = os.getenv("VECTOR_STORE_TYPE", "memory")  # memory, chroma, faiss
    memory_retention_days: int = int(os.getenv("MEMORY_RETENTION_DAYS", "365"))
    
    # ============ CORS & Security ============
    cors_origins: List[str] = [
        "http://localhost:3000",
        "http://localhost:8080",
        "http://localhost:5173",
        "http://localhost:19006",  # Android emulator
    ]
    allowed_origins: str = os.getenv("ALLOWED_ORIGINS", "*")
    rate_limit_enabled: bool = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
    rate_limit_requests_per_minute: int = int(os.getenv("RATE_LIMIT_RPM", "100"))
    
    # ============ Voice & Audio ============
    voice_enabled: bool = os.getenv("VOICE_ENABLED", "true").lower() == "true"
    stt_provider: str = os.getenv("STT_PROVIDER", "whisper")  # whisper, google
    tts_provider: str = os.getenv("TTS_PROVIDER", "edge")      # edge, elevenlabs
    audio_sample_rate: int = int(os.getenv("AUDIO_SAMPLE_RATE", "16000"))
    
    # ============ Vision & Processing ============
    vision_enabled: bool = os.getenv("VISION_ENABLED", "true").lower() == "true"
    ocr_enabled: bool = os.getenv("OCR_ENABLED", "true").lower() == "true"
    screenshot_analysis_enabled: bool = os.getenv("SCREENSHOT_ANALYSIS", "true").lower() == "true"
    
    # ============ Storage & Media ============
    media_storage_path: str = os.getenv("MEDIA_STORAGE_PATH", "./data/media")
    max_upload_size_mb: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "50"))
    
    # ============ Cache Configuration ============
    redis_url: Optional[str] = os.getenv("REDIS_URL")
    cache_ttl_seconds: int = int(os.getenv("CACHE_TTL", "3600"))
    
    # ============ Background Jobs ============
    celery_broker_url: Optional[str] = os.getenv("CELERY_BROKER_URL")
    celery_result_backend: Optional[str] = os.getenv("CELERY_RESULT_BACKEND")
    background_jobs_enabled: bool = os.getenv("BACKGROUND_JOBS_ENABLED", "false").lower() == "true"
    
    # ============ Observability ============
    telemetry_enabled: bool = os.getenv("TELEMETRY_ENABLED", "true").lower() == "true"
    prometheus_enabled: bool = os.getenv("PROMETHEUS_ENABLED", "false").lower() == "true"
    structured_logging_enabled: bool = os.getenv("STRUCTURED_LOGGING_ENABLED", "true").lower() == "true"
    
    # ============ Feature Flags ============
    enable_memory_persistence: bool = os.getenv("ENABLE_MEMORY_PERSISTENCE", "true").lower() == "true"
    enable_automation_engine: bool = os.getenv("ENABLE_AUTOMATION_ENGINE", "true").lower() == "true"
    enable_multi_ai_orchestration: bool = os.getenv("ENABLE_MULTI_AI_ORCHESTRATION", "true").lower() == "true"
    enable_websocket_streaming: bool = os.getenv("ENABLE_WEBSOCKET_STREAMING", "true").lower() == "true"
    enable_voice_input: bool = os.getenv("ENABLE_VOICE_INPUT", "true").lower() == "true"
    enable_vision_processing: bool = os.getenv("ENABLE_VISION_PROCESSING", "true").lower() == "true"
    
    # ============ Android & Mobile ============
    android_app_id: str = os.getenv("ANDROID_APP_ID", "com.sextafeira.os")
    mobile_api_prefix: str = "/api/v2/mobile"
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


# Singleton instance
settings = Settings()
