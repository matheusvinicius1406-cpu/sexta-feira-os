"""
Custom exception hierarchy for Sexta-Feira OS
Implements clean exception handling following SOLID principles
"""
from typing import Optional, Dict, Any
from enum import Enum


class ErrorCode(str, Enum):
    """Standardized error codes for the system"""
    # Auth errors
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    INSUFFICIENT_PERMISSIONS = "INSUFFICIENT_PERMISSIONS"
    USER_NOT_FOUND = "USER_NOT_FOUND"
    USER_ALREADY_EXISTS = "USER_ALREADY_EXISTS"
    
    # AI Provider errors
    AI_PROVIDER_UNAVAILABLE = "AI_PROVIDER_UNAVAILABLE"
    AI_RATE_LIMITED = "AI_RATE_LIMITED"
    AI_INVALID_REQUEST = "AI_INVALID_REQUEST"
    AI_CONTEXT_TOO_LARGE = "AI_CONTEXT_TOO_LARGE"
    
    # Memory errors
    MEMORY_NOT_FOUND = "MEMORY_NOT_FOUND"
    MEMORY_QUOTA_EXCEEDED = "MEMORY_QUOTA_EXCEEDED"
    VECTOR_STORE_ERROR = "VECTOR_STORE_ERROR"
    
    # Automation errors
    AUTOMATION_NOT_FOUND = "AUTOMATION_NOT_FOUND"
    AUTOMATION_EXECUTION_FAILED = "AUTOMATION_EXECUTION_FAILED"
    
    # System errors
    DATABASE_ERROR = "DATABASE_ERROR"
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"


class SextaFeiraException(Exception):
    """Base exception for all Sexta-Feira OS exceptions"""
    
    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.INTERNAL_SERVER_ERROR,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        self.cause = cause
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses"""
        return {
            "error": self.error_code.value,
            "message": self.message,
            "status_code": self.status_code,
            "details": self.details,
        }


# ============ Authentication Exceptions ============

class AuthenticationException(SextaFeiraException):
    """Base authentication exception"""
    pass


class InvalidCredentialsException(AuthenticationException):
    """Invalid email or password"""
    
    def __init__(self, message: str = "Invalid email or password"):
        super().__init__(
            message=message,
            error_code=ErrorCode.INVALID_CREDENTIALS,
            status_code=401,
        )


class TokenExpiredException(AuthenticationException):
    """JWT token expired"""
    
    def __init__(self, message: str = "Token has expired"):
        super().__init__(
            message=message,
            error_code=ErrorCode.TOKEN_EXPIRED,
            status_code=401,
        )


class InsufficientPermissionsException(AuthenticationException):
    """User doesn't have required permissions"""
    
    def __init__(self, message: str = "Insufficient permissions", required_roles: Optional[list] = None):
        super().__init__(
            message=message,
            error_code=ErrorCode.INSUFFICIENT_PERMISSIONS,
            status_code=403,
            details={"required_roles": required_roles or []},
        )


class UserNotFoundException(AuthenticationException):
    """User not found"""
    
    def __init__(self, user_id: str):
        super().__init__(
            message=f"User not found: {user_id}",
            error_code=ErrorCode.USER_NOT_FOUND,
            status_code=404,
            details={"user_id": user_id},
        )


class UserAlreadyExistsException(AuthenticationException):
    """User already registered"""
    
    def __init__(self, email: str):
        super().__init__(
            message=f"User already registered: {email}",
            error_code=ErrorCode.USER_ALREADY_EXISTS,
            status_code=400,
            details={"email": email},
        )


# ============ AI Provider Exceptions ============

class AIProviderException(SextaFeiraException):
    """Base AI provider exception"""
    pass


class AIProviderUnavailableException(AIProviderException):
    """AI provider is unavailable"""
    
    def __init__(self, provider: str, message: str = None):
        super().__init__(
            message=message or f"AI provider unavailable: {provider}",
            error_code=ErrorCode.AI_PROVIDER_UNAVAILABLE,
            status_code=503,
            details={"provider": provider},
        )


class AIRateLimitedException(AIProviderException):
    """AI provider rate limit exceeded"""
    
    def __init__(self, provider: str, retry_after: Optional[int] = None):
        super().__init__(
            message=f"Rate limit exceeded for {provider}",
            error_code=ErrorCode.AI_RATE_LIMITED,
            status_code=429,
            details={"provider": provider, "retry_after": retry_after},
        )


class AIInvalidRequestException(AIProviderException):
    """Invalid request to AI provider"""
    
    def __init__(self, provider: str, details: str):
        super().__init__(
            message=f"Invalid request to {provider}: {details}",
            error_code=ErrorCode.AI_INVALID_REQUEST,
            status_code=400,
            details={"provider": provider, "validation_error": details},
        )


class AIContextTooLargeException(AIProviderException):
    """Context/prompt too large for AI provider"""
    
    def __init__(self, provider: str, max_tokens: int):
        super().__init__(
            message=f"Context too large for {provider}. Max: {max_tokens}",
            error_code=ErrorCode.AI_CONTEXT_TOO_LARGE,
            status_code=400,
            details={"provider": provider, "max_tokens": max_tokens},
        )


# ============ Memory Exceptions ============

class MemoryException(SextaFeiraException):
    """Base memory exception"""
    pass


class MemoryNotFoundException(MemoryException):
    """Memory entry not found"""
    
    def __init__(self, memory_id: str):
        super().__init__(
            message=f"Memory entry not found: {memory_id}",
            error_code=ErrorCode.MEMORY_NOT_FOUND,
            status_code=404,
            details={"memory_id": memory_id},
        )


class MemoryQuotaExceededException(MemoryException):
    """User memory quota exceeded"""
    
    def __init__(self, user_id: str, quota_mb: int, used_mb: int):
        super().__init__(
            message=f"Memory quota exceeded. Limit: {quota_mb}MB, Used: {used_mb}MB",
            error_code=ErrorCode.MEMORY_QUOTA_EXCEEDED,
            status_code=400,
            details={"user_id": user_id, "quota_mb": quota_mb, "used_mb": used_mb},
        )


class VectorStoreException(MemoryException):
    """Vector store operation failed"""
    
    def __init__(self, operation: str, message: str):
        super().__init__(
            message=f"Vector store error in {operation}: {message}",
            error_code=ErrorCode.VECTOR_STORE_ERROR,
            status_code=500,
            details={"operation": operation},
        )


# ============ Automation Exceptions ============

class AutomationException(SextaFeiraException):
    """Base automation exception"""
    pass


class AutomationNotFoundException(AutomationException):
    """Automation not found"""
    
    def __init__(self, automation_id: str):
        super().__init__(
            message=f"Automation not found: {automation_id}",
            error_code=ErrorCode.AUTOMATION_NOT_FOUND,
            status_code=404,
            details={"automation_id": automation_id},
        )


class AutomationExecutionFailedException(AutomationException):
    """Automation execution failed"""
    
    def __init__(self, automation_id: str, reason: str, cause: Optional[Exception] = None):
        super().__init__(
            message=f"Automation execution failed: {reason}",
            error_code=ErrorCode.AUTOMATION_EXECUTION_FAILED,
            status_code=500,
            details={"automation_id": automation_id, "reason": reason},
            cause=cause,
        )


# ============ System Exceptions ============

class DatabaseException(SextaFeiraException):
    """Database operation failed"""
    
    def __init__(self, message: str, operation: str = None, cause: Exception = None):
        super().__init__(
            message=message,
            error_code=ErrorCode.DATABASE_ERROR,
            status_code=500,
            details={"operation": operation} if operation else {},
            cause=cause,
        )


class ValidationException(SextaFeiraException):
    """Request validation failed"""
    
    def __init__(self, message: str, field: str = None, constraint: str = None):
        super().__init__(
            message=message,
            error_code=ErrorCode.VALIDATION_ERROR,
            status_code=400,
            details={"field": field, "constraint": constraint},
        )


class ResourceNotFoundException(SextaFeiraException):
    """Resource not found"""
    
    def __init__(self, resource_type: str, resource_id: str):
        super().__init__(
            message=f"{resource_type} not found: {resource_id}",
            error_code=ErrorCode.RESOURCE_NOT_FOUND,
            status_code=404,
            details={"resource_type": resource_type, "resource_id": resource_id},
        )


class RateLimitExceededException(SextaFeiraException):
    """Rate limit exceeded"""
    
    def __init__(self, user_id: str, limit: int, window_seconds: int, retry_after: int = None):
        super().__init__(
            message=f"Rate limit exceeded: {limit} requests per {window_seconds}s",
            error_code=ErrorCode.RATE_LIMIT_EXCEEDED,
            status_code=429,
            details={
                "user_id": user_id,
                "limit": limit,
                "window_seconds": window_seconds,
                "retry_after": retry_after,
            },
        )
