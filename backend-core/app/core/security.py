"""
Advanced security module for Sexta-Feira OS
Implements RBAC, audit logging, and security best practices
"""
from enum import Enum
from typing import Set, Optional, List
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class Role(str, Enum):
    """User roles for RBAC"""
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    MODERATOR = "moderator"
    POWER_USER = "power_user"
    USER = "user"
    GUEST = "guest"


class Permission(str, Enum):
    """Application permissions"""
    # User management
    USER_CREATE = "user:create"
    USER_READ = "user:read"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"
    
    # Chat/Messages
    CHAT_READ = "chat:read"
    CHAT_WRITE = "chat:write"
    CHAT_DELETE = "chat:delete"
    
    # Memory
    MEMORY_READ = "memory:read"
    MEMORY_WRITE = "memory:write"
    MEMORY_DELETE = "memory:delete"
    
    # Automation
    AUTOMATION_READ = "automation:read"
    AUTOMATION_WRITE = "automation:write"
    AUTOMATION_DELETE = "automation:delete"
    AUTOMATION_EXECUTE = "automation:execute"
    
    # Admin
    ADMIN_READ = "admin:read"
    ADMIN_WRITE = "admin:write"
    SYSTEM_CONFIG = "system:config"
    AUDIT_LOG = "audit:log"
    
    # Analytics
    ANALYTICS_READ = "analytics:read"
    ANALYTICS_EXPORT = "analytics:export"


# Role to Permissions mapping
ROLE_PERMISSIONS: dict[Role, Set[Permission]] = {
    Role.SUPER_ADMIN: set(Permission),  # All permissions
    Role.ADMIN: {
        Permission.USER_CREATE,
        Permission.USER_READ,
        Permission.USER_UPDATE,
        Permission.USER_DELETE,
        Permission.CHAT_READ,
        Permission.MEMORY_READ,
        Permission.AUTOMATION_READ,
        Permission.ADMIN_READ,
        Permission.ADMIN_WRITE,
        Permission.AUDIT_LOG,
        Permission.ANALYTICS_READ,
    },
    Role.MODERATOR: {
        Permission.USER_READ,
        Permission.CHAT_READ,
        Permission.CHAT_DELETE,
        Permission.MEMORY_READ,
        Permission.AUTOMATION_READ,
        Permission.AUDIT_LOG,
        Permission.ANALYTICS_READ,
    },
    Role.POWER_USER: {
        Permission.CHAT_READ,
        Permission.CHAT_WRITE,
        Permission.MEMORY_READ,
        Permission.MEMORY_WRITE,
        Permission.AUTOMATION_READ,
        Permission.AUTOMATION_WRITE,
        Permission.AUTOMATION_EXECUTE,
        Permission.ANALYTICS_READ,
    },
    Role.USER: {
        Permission.USER_READ,
        Permission.CHAT_READ,
        Permission.CHAT_WRITE,
        Permission.MEMORY_READ,
        Permission.MEMORY_WRITE,
        Permission.AUTOMATION_READ,
        Permission.AUTOMATION_WRITE,
    },
    Role.GUEST: {
        Permission.CHAT_READ,
        Permission.MEMORY_READ,
    },
}


@dataclass
class SecurityContext:
    """Security context for requests"""
    user_id: str
    roles: List[Role]
    permissions: Set[Permission]
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    authenticated_at: datetime = None
    
    def has_permission(self, permission: Permission) -> bool:
        """Check if user has permission"""
        return permission in self.permissions
    
    def has_role(self, role: Role) -> bool:
        """Check if user has role"""
        return role in self.roles
    
    def has_any_role(self, roles: List[Role]) -> bool:
        """Check if user has any of the given roles"""
        return any(role in self.roles for role in roles)
    
    def has_all_permissions(self, permissions: Set[Permission]) -> bool:
        """Check if user has all permissions"""
        return permissions.issubset(self.permissions)
    
    def has_any_permission(self, permissions: Set[Permission]) -> bool:
        """Check if user has any permission"""
        return bool(permissions & self.permissions)


class RBACManager:
    """Role-Based Access Control manager"""
    
    @staticmethod
    def get_permissions_for_role(role: Role) -> Set[Permission]:
        """Get permissions for a role"""
        return ROLE_PERMISSIONS.get(role, set())
    
    @staticmethod
    def get_permissions_for_roles(roles: List[Role]) -> Set[Permission]:
        """Get combined permissions for multiple roles"""
        permissions: Set[Permission] = set()
        for role in roles:
            permissions.update(ROLE_PERMISSIONS.get(role, set()))
        return permissions
    
    @staticmethod
    def create_security_context(
        user_id: str,
        roles: List[Role],
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> SecurityContext:
        """Create security context from user roles"""
        permissions = RBACManager.get_permissions_for_roles(roles)
        return SecurityContext(
            user_id=user_id,
            roles=roles,
            permissions=permissions,
            ip_address=ip_address,
            user_agent=user_agent,
            authenticated_at=datetime.utcnow(),
        )


@dataclass
class AuditLogEntry:
    """Audit log entry for tracking user actions"""
    user_id: str
    action: str
    resource_type: str
    resource_id: str
    timestamp: datetime
    status: str  # "success" or "failure"
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    details: dict = None
    error_message: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "user_id": self.user_id,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "timestamp": self.timestamp.isoformat(),
            "status": self.status,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "details": self.details or {},
            "error_message": self.error_message,
        }


class AuditLogger:
    """Logger for audit trails"""
    
    def __init__(self):
        self._audit_logs: List[AuditLogEntry] = []
        self._max_logs = 100000
    
    def log_action(
        self,
        user_id: str,
        action: str,
        resource_type: str,
        resource_id: str,
        status: str = "success",
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: dict = None,
        error_message: Optional[str] = None,
    ) -> AuditLogEntry:
        """Log a user action"""
        entry = AuditLogEntry(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            timestamp=datetime.utcnow(),
            status=status,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details,
            error_message=error_message,
        )
        
        self._audit_logs.append(entry)
        if len(self._audit_logs) > self._max_logs:
            self._audit_logs.pop(0)
        
        logger.info(f"Audit: {action} on {resource_type}/{resource_id} by {user_id} - {status}")
        
        return entry
    
    def get_user_audit_trail(self, user_id: str, limit: int = 100) -> List[AuditLogEntry]:
        """Get audit trail for user"""
        entries = [e for e in self._audit_logs if e.user_id == user_id]
        return entries[-limit:]
    
    def get_resource_audit_trail(
        self,
        resource_type: str,
        resource_id: str,
        limit: int = 100
    ) -> List[AuditLogEntry]:
        """Get audit trail for resource"""
        entries = [
            e for e in self._audit_logs
            if e.resource_type == resource_type and e.resource_id == resource_id
        ]
        return entries[-limit:]
    
    def get_failed_attempts(self, user_id: str, limit: int = 100) -> List[AuditLogEntry]:
        """Get failed audit attempts for user"""
        entries = [
            e for e in self._audit_logs
            if e.user_id == user_id and e.status == "failure"
        ]
        return entries[-limit:]


class RateLimiter:
    """Rate limiter for API requests"""
    
    def __init__(self):
        self._requests: dict[str, list[datetime]] = {}
        self._limits: dict[Role, int] = {
            Role.SUPER_ADMIN: 10000,  # 10k/minute
            Role.ADMIN: 5000,          # 5k/minute
            Role.MODERATOR: 2000,      # 2k/minute
            Role.POWER_USER: 1000,     # 1k/minute
            Role.USER: 500,            # 500/minute
            Role.GUEST: 100,           # 100/minute
        }
    
    def is_allowed(self, user_id: str, role: Role, window_seconds: int = 60) -> bool:
        """Check if request is within rate limit"""
        limit = self._limits.get(role, 100)
        now = datetime.utcnow()
        
        if user_id not in self._requests:
            self._requests[user_id] = []
        
        # Remove old requests outside window
        self._requests[user_id] = [
            req_time for req_time in self._requests[user_id]
            if (now - req_time).total_seconds() < window_seconds
        ]
        
        # Check limit
        if len(self._requests[user_id]) >= limit:
            return False
        
        # Add current request
        self._requests[user_id].append(now)
        return True
    
    def get_remaining(self, user_id: str, role: Role, window_seconds: int = 60) -> int:
        """Get remaining requests in window"""
        limit = self._limits.get(role, 100)
        now = datetime.utcnow()
        
        if user_id not in self._requests:
            return limit
        
        # Remove old requests
        self._requests[user_id] = [
            req_time for req_time in self._requests[user_id]
            if (now - req_time).total_seconds() < window_seconds
        ]
        
        return max(0, limit - len(self._requests[user_id]))


# Global instances
audit_logger = AuditLogger()
rate_limiter = RateLimiter()

# Import at the end to avoid circular imports
from app.auth.jwt import get_current_user

__all__ = [
    "get_current_user",
    "Role",
    "Permission",
    "RBACManager",
    "SecurityContext",
    "audit_logger",
    "rate_limiter",
]

