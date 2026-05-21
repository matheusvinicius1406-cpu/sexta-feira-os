"""
Event system for Sexta-Feira OS
Implements Domain Events pattern for event-driven architecture
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional, List, Callable
from enum import Enum
import logging
import uuid

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Domain event types"""
    # User events
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"
    USER_AUTHENTICATED = "user.authenticated"
    USER_LOGGED_OUT = "user.logged_out"
    
    # Chat/Conversation events
    MESSAGE_SENT = "message.sent"
    MESSAGE_RECEIVED = "message.received"
    CONVERSATION_STARTED = "conversation.started"
    CONVERSATION_ENDED = "conversation.ended"
    
    # AI events
    AI_REQUEST_STARTED = "ai.request.started"
    AI_REQUEST_COMPLETED = "ai.request.completed"
    AI_REQUEST_FAILED = "ai.request.failed"
    AI_PROVIDER_SWITCHED = "ai.provider.switched"
    
    # Memory events
    MEMORY_CREATED = "memory.created"
    MEMORY_UPDATED = "memory.updated"
    MEMORY_DELETED = "memory.deleted"
    MEMORY_INDEXED = "memory.indexed"
    
    # Automation events
    AUTOMATION_TRIGGERED = "automation.triggered"
    AUTOMATION_EXECUTED = "automation.executed"
    AUTOMATION_FAILED = "automation.failed"
    
    # System events
    SYSTEM_STARTED = "system.started"
    SYSTEM_SHUTDOWN = "system.shutdown"
    HEALTH_CHECK_PASSED = "health.check.passed"
    HEALTH_CHECK_FAILED = "health.check.failed"


@dataclass
class DomainEvent:
    """Base domain event"""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: EventType = None
    aggregate_id: str = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    user_id: Optional[str] = None
    source: str = "system"
    version: int = 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary"""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value if isinstance(self.event_type, EventType) else self.event_type,
            "aggregate_id": self.aggregate_id,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
            "metadata": self.metadata,
            "user_id": self.user_id,
            "source": self.source,
            "version": self.version,
        }


@dataclass
class UserCreatedEvent(DomainEvent):
    """User created event"""
    def __init__(self, user_id: str, email: str, name: str, **kwargs):
        super().__init__(
            event_type=EventType.USER_CREATED,
            aggregate_id=user_id,
            data={"user_id": user_id, "email": email, "name": name},
            **kwargs
        )


@dataclass
class MessageSentEvent(DomainEvent):
    """Message sent event"""
    def __init__(self, message_id: str, user_id: str, content: str, **kwargs):
        super().__init__(
            event_type=EventType.MESSAGE_SENT,
            aggregate_id=message_id,
            user_id=user_id,
            data={"message_id": message_id, "user_id": user_id, "content": content},
            **kwargs
        )


@dataclass
class AIRequestCompletedEvent(DomainEvent):
    """AI request completed event"""
    def __init__(
        self,
        request_id: str,
        user_id: str,
        provider: str,
        response_time_ms: int,
        tokens_used: int = 0,
        **kwargs
    ):
        super().__init__(
            event_type=EventType.AI_REQUEST_COMPLETED,
            aggregate_id=request_id,
            user_id=user_id,
            data={
                "request_id": request_id,
                "provider": provider,
                "response_time_ms": response_time_ms,
                "tokens_used": tokens_used,
            },
            **kwargs
        )


@dataclass
class MemoryCreatedEvent(DomainEvent):
    """Memory entry created event"""
    def __init__(
        self,
        memory_id: str,
        user_id: str,
        key: str,
        category: str,
        **kwargs
    ):
        super().__init__(
            event_type=EventType.MEMORY_CREATED,
            aggregate_id=memory_id,
            user_id=user_id,
            data={
                "memory_id": memory_id,
                "key": key,
                "category": category,
            },
            **kwargs
        )


@dataclass
class AutomationTriggeredEvent(DomainEvent):
    """Automation triggered event"""
    def __init__(
        self,
        automation_id: str,
        user_id: str,
        trigger_type: str,
        **kwargs
    ):
        super().__init__(
            event_type=EventType.AUTOMATION_TRIGGERED,
            aggregate_id=automation_id,
            user_id=user_id,
            data={
                "automation_id": automation_id,
                "trigger_type": trigger_type,
            },
            **kwargs
        )


class EventHandler:
    """Event handler interface"""
    
    async def handle(self, event: DomainEvent) -> None:
        """Handle event"""
        raise NotImplementedError


class EventBus:
    """
    Central event bus for publish-subscribe pattern
    Enables loosely coupled, event-driven architecture
    """
    
    def __init__(self):
        self._handlers: Dict[EventType, List[Callable]] = {}
        self._event_history: List[DomainEvent] = []
        self._max_history_size = 10000
        logger.info("EventBus initialized")
    
    def subscribe(self, event_type: EventType, handler: Callable) -> None:
        """Subscribe to event type"""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
        logger.debug(f"Handler subscribed to {event_type.value}")
    
    def unsubscribe(self, event_type: EventType, handler: Callable) -> None:
        """Unsubscribe from event type"""
        if event_type in self._handlers:
            self._handlers[event_type].remove(handler)
            logger.debug(f"Handler unsubscribed from {event_type.value}")
    
    async def publish(self, event: DomainEvent) -> None:
        """Publish event to all subscribers"""
        logger.info(f"Publishing event: {event.event_type.value} (ID: {event.event_id})")
        
        # Store in history
        self._event_history.append(event)
        if len(self._event_history) > self._max_history_size:
            self._event_history.pop(0)
        
        # Get handlers for this event type
        handlers = self._handlers.get(event.event_type, [])
        
        # Execute all handlers
        for handler in handlers:
            try:
                if hasattr(handler, 'handle'):
                    await handler.handle(event)
                else:
                    await handler(event)
            except Exception as e:
                logger.error(f"Error in event handler: {str(e)}", exc_info=True)
    
    def get_event_history(self, limit: int = 100) -> List[DomainEvent]:
        """Get recent events from history"""
        return self._event_history[-limit:]
    
    def get_events_by_type(self, event_type: EventType, limit: int = 100) -> List[DomainEvent]:
        """Get events of specific type"""
        events = [e for e in self._event_history if e.event_type == event_type]
        return events[-limit:]
    
    def get_events_by_user(self, user_id: str, limit: int = 100) -> List[DomainEvent]:
        """Get events for specific user"""
        events = [e for e in self._event_history if e.user_id == user_id]
        return events[-limit:]
    
    def clear_history(self) -> None:
        """Clear event history (for testing)"""
        self._event_history.clear()


# Global event bus instance
event_bus = EventBus()


async def publish_event(event: DomainEvent) -> None:
    """Publish event to global bus"""
    await event_bus.publish(event)


def subscribe_to_event(event_type: EventType, handler: Callable) -> None:
    """Subscribe to event on global bus"""
    event_bus.subscribe(event_type, handler)


def unsubscribe_from_event(event_type: EventType, handler: Callable) -> None:
    """Unsubscribe from event on global bus"""
    event_bus.unsubscribe(event_type, handler)
