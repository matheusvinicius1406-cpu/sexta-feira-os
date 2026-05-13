"""
Configuration management for Sexta-Feira OS Backend
"""
import os
from typing import Optional, List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Service Configuration
    app_name: str = "Sexta-Feira OS"
    app_version: str = "0.1.0"
    environment: str = os.getenv("ENVIRONMENT", "development")
    debug: bool = environment == "development"
    
    # Server Configuration
    backend_host: str = os.getenv("BACKEND_HOST", "0.0.0.0")
    backend_port: int = int(os.getenv("BACKEND_PORT", "8000"))
    
    # Database Configuration
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./sexta_feira_os.db")
    sqlite_db_path: str = os.getenv("SQLITE_DB_PATH", "./data/sexta_feira_os.db")
    
    # JWT & Authentication
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "dev-secret-key-change-in-production")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    jwt_expiration_hours: int = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))
    refresh_token_expiration_days: int = int(os.getenv("REFRESH_TOKEN_EXPIRATION_DAYS", "30"))
    
    # AI Provider Configuration
    openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
    claude_api_key: Optional[str] = os.getenv("CLAUDE_API_KEY")
    gemini_api_key: Optional[str] = os.getenv("GEMINI_API_KEY")
    default_ai_provider: str = os.getenv("DEFAULT_AI_PROVIDER", "openai")
    
    # CORS Configuration
    cors_origins: List[str] = [
        "http://localhost:3000",
        "http://localhost:8080",
        "http://localhost:5173"
    ]
    
    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Feature Flags
    enable_memory_persistence: bool = os.getenv("ENABLE_MEMORY_PERSISTENCE", "true").lower() == "true"
    enable_automation_engine: bool = os.getenv("ENABLE_AUTOMATION_ENGINE", "true").lower() == "true"
    enable_multi_ai_orchestration: bool = os.getenv("ENABLE_MULTI_AI_ORCHESTRATION", "true").lower() == "true"
    
    # Voice & Media
    voice_enabled: bool = os.getenv("VOICE_ENABLED", "true").lower() == "true"
    media_storage_path: str = os.getenv("MEDIA_STORAGE_PATH", "./data/media")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Singleton instance
settings = Settings()
