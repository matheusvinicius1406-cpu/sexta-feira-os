"""
Android Intent Builder - Fluent builder for constructing Android intents
"""
from typing import Dict, Any, Optional
from app.android.models import AndroidIntent, IntentType, IntentPriority
from datetime import datetime
import uuid


class IntentBuilder:
    """Fluent builder for creating Android intents"""
    
    def __init__(self):
        self._action: str = ""
        self._intent_type: IntentType = IntentType.UI_ACTION
        self._payload: Dict[str, Any] = {}
        self._device_id: str = ""
        self._user_id: str = ""
        self._priority: IntentPriority = IntentPriority.NORMAL
        self._request_id: str = str(uuid.uuid4())
        self._metadata: Dict[str, Any] = {}
        self._requires_response: bool = True
        self._timeout_seconds: int = 30
    
    def action(self, action: str) -> "IntentBuilder":
        """Set intent action"""
        self._action = action
        return self
    
    def intent_type(self, intent_type: IntentType) -> "IntentBuilder":
        """Set intent type"""
        self._intent_type = intent_type
        return self
    
    def payload(self, payload: Dict[str, Any]) -> "IntentBuilder":
        """Set intent payload"""
        self._payload = payload
        return self
    
    def add_payload(self, key: str, value: Any) -> "IntentBuilder":
        """Add a key-value pair to payload"""
        self._payload[key] = value
        return self
    
    def device_id(self, device_id: str) -> "IntentBuilder":
        """Set device ID"""
        self._device_id = device_id
        return self
    
    def user_id(self, user_id: str) -> "IntentBuilder":
        """Set user ID"""
        self._user_id = user_id
        return self
    
    def priority(self, priority: IntentPriority) -> "IntentBuilder":
        """Set priority level"""
        self._priority = priority
        return self
    
    def request_id(self, request_id: str) -> "IntentBuilder":
        """Set request ID"""
        self._request_id = request_id
        return self
    
    def metadata(self, metadata: Dict[str, Any]) -> "IntentBuilder":
        """Set metadata"""
        self._metadata = metadata
        return self
    
    def add_metadata(self, key: str, value: Any) -> "IntentBuilder":
        """Add metadata key-value pair"""
        self._metadata[key] = value
        return self
    
    def requires_response(self, requires: bool) -> "IntentBuilder":
        """Set whether response is required"""
        self._requires_response = requires
        return self
    
    def timeout(self, seconds: int) -> "IntentBuilder":
        """Set timeout in seconds"""
        self._timeout_seconds = seconds
        return self
    
    def voice_command(self, command: str, user_id: str) -> "IntentBuilder":
        """Convenience method for voice commands"""
        self._action = "VOICE_COMMAND"
        self._intent_type = IntentType.VOICE_COMMAND
        self._payload = {"command": command}
        self._user_id = user_id
        return self
    
    def build(self) -> AndroidIntent:
        """Build the Android intent"""
        if not self._action:
            raise ValueError("Action is required")
        if not self._device_id:
            raise ValueError("Device ID is required")
        if not self._user_id:
            raise ValueError("User ID is required")
        
        return AndroidIntent(
            action=self._action,
            intent_type=self._intent_type,
            payload=self._payload,
            device_id=self._device_id,
            user_id=self._user_id,
            priority=self._priority,
            request_id=self._request_id,
            timestamp=datetime.utcnow(),
            metadata=self._metadata,
            requires_response=self._requires_response,
            timeout_seconds=self._timeout_seconds,
        )
