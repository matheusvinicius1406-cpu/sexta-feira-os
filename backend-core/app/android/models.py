"""
Android Intent Models - Data models for Android intents and responses
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from enum import Enum
from datetime import datetime


class IntentType(str, Enum):
    """Types of Android intents"""
    VOICE_COMMAND = "voice_command"
    UI_ACTION = "ui_action"
    AUTOMATION_TRIGGER = "automation_trigger"
    REMINDER = "reminder"
    NOTIFICATION = "notification"
    LOCATION_BASED = "location_based"
    BACKGROUND_SYNC = "background_sync"


class IntentPriority(str, Enum):
    """Priority levels for intent execution"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AndroidIntent:
    """Android intent data model"""
    action: str  # e.g., "VOICE_COMMAND", "SEND_MESSAGE"
    intent_type: IntentType
    payload: Dict[str, Any]
    device_id: str
    user_id: str
    priority: IntentPriority = IntentPriority.NORMAL
    request_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    requires_response: bool = True
    timeout_seconds: int = 30
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "action": self.action,
            "intent_type": self.intent_type.value,
            "payload": self.payload,
            "device_id": self.device_id,
            "user_id": self.user_id,
            "priority": self.priority.value,
            "request_id": self.request_id,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
            "requires_response": self.requires_response,
            "timeout_seconds": self.timeout_seconds,
        }


@dataclass
class AndroidResponse:
    """Android response data model"""
    request_id: str
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    execution_time_ms: float = 0.0
    device_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "request_id": self.request_id,
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "error_type": self.error_type,
            "timestamp": self.timestamp.isoformat(),
            "execution_time_ms": self.execution_time_ms,
            "device_id": self.device_id,
        }
