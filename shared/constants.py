"""
Shared constants and models used across mobile and backend
"""

# AI Provider Constants
class AIProvider:
    OPENAI = "openai"
    CLAUDE = "claude"
    GEMINI = "gemini"
    
    AVAILABLE = [OPENAI, CLAUDE, GEMINI]


# Message Types
class MessageType:
    TEXT = "text"
    VOICE = "voice"
    IMAGE = "image"
    MEDIA = "media"


# Response Status
class ResponseStatus:
    SUCCESS = "success"
    ERROR = "error"
    PENDING = "pending"
    PROCESSING = "processing"


# Feature Flags
class Features:
    VOICE_ENABLED = True
    MEMORY_ENABLED = True
    AUTOMATION_ENABLED = True
    MULTI_AI_ENABLED = True
    OFFLINE_MODE_ENABLED = True


# Memory Categories
class MemoryCategory:
    PROFILE = "profile"
    PREFERENCES = "preferences"
    HABITS = "habits"
    INTERACTIONS = "interactions"
    AUTOMATIONS = "automations"
    GENERAL = "general"


# API Versions
API_VERSION = "v1"
API_BASE_PATH = f"/api/{API_VERSION}"


# Timeout Constants (in seconds)
API_TIMEOUT = 30
VOICE_TIMEOUT = 60
AUDIO_CHUNK_TIMEOUT = 10


# Database Constants
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 1000
MAX_MESSAGE_LENGTH = 2000
MAX_MEMORY_VALUE_LENGTH = 50000


# Error Codes
class ErrorCode:
    INVALID_CREDENTIALS = "invalid_credentials"
    TOKEN_EXPIRED = "token_expired"
    INVALID_TOKEN = "invalid_token"
    USER_NOT_FOUND = "user_not_found"
    USER_ALREADY_EXISTS = "user_already_exists"
    INVALID_REQUEST = "invalid_request"
    SERVER_ERROR = "server_error"
    AI_ERROR = "ai_error"
    DATABASE_ERROR = "database_error"
