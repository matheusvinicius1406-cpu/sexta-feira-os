"""
Android Intent Service - High-level service for Android intent processing
Provides business logic for handling Android requests.
"""
from typing import Dict, Any, Optional, List
import logging
from app.android.dispatcher import IntentDispatcher
from app.android.intent_builder import IntentBuilder
from app.android.models import AndroidIntent, AndroidResponse, IntentType, IntentPriority

logger = logging.getLogger(__name__)


class IntentService:
    """
    Service for processing Android intents.
    Handles intent validation, routing, and response management.
    """
    
    def __init__(self, dispatcher: Optional[IntentDispatcher] = None):
        self.dispatcher = dispatcher or IntentDispatcher()
        self._response_handlers: Dict[str, List[callable]] = {}
        logger.info("Intent Service initialized")
    
    async def process_intent(
        self,
        action: str,
        payload: Dict[str, Any],
        device_id: str,
        user_id: str,
        intent_type: IntentType = IntentType.UI_ACTION,
        priority: IntentPriority = IntentPriority.NORMAL,
    ) -> AndroidResponse:
        """
        Process an Android intent.
        
        Args:
            action: Intent action
            payload: Intent payload
            device_id: Device identifier
            user_id: User identifier
            intent_type: Type of intent
            priority: Execution priority
        
        Returns:
            Android response
        """
        # Build intent
        intent = IntentBuilder() \
            .action(action) \
            .intent_type(intent_type) \
            .payload(payload) \
            .device_id(device_id) \
            .user_id(user_id) \
            .priority(priority) \
            .build()
        
        # Dispatch intent
        response = await self.dispatcher.dispatch(intent)
        
        # Handle response callbacks
        await self._handle_response_callbacks(intent, response)
        
        return response
    
    async def process_intents_batch(
        self,
        intents: List[Dict[str, Any]],
        device_id: str,
        user_id: str,
    ) -> List[AndroidResponse]:
        """
        Process multiple intents.
        
        Args:
            intents: List of intent specifications
            device_id: Device identifier
            user_id: User identifier
        
        Returns:
            List of responses
        """
        responses = []
        for intent_spec in intents:
            response = await self.process_intent(
                action=intent_spec.get("action"),
                payload=intent_spec.get("payload", {}),
                device_id=device_id,
                user_id=user_id,
                intent_type=IntentType(intent_spec.get("type", "ui_action")),
                priority=IntentPriority(intent_spec.get("priority", "normal")),
            )
            responses.append(response)
        
        return responses
    
    def register_response_handler(
        self,
        event: str,
        handler: callable,
    ) -> None:
        """Register handler for response events"""
        if event not in self._response_handlers:
            self._response_handlers[event] = []
        self._response_handlers[event].append(handler)
        logger.info(f"Registered response handler for event: {event}")
    
    async def _handle_response_callbacks(
        self,
        intent: AndroidIntent,
        response: AndroidResponse,
    ) -> None:
        """Handle response callbacks"""
        event_key = "success" if response.success else "error"
        handlers = self._response_handlers.get(event_key, [])
        
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(intent, response)
                else:
                    handler(intent, response)
            except Exception as e:
                logger.error(f"Error in response handler: {e}")
    
    def get_intent_info(self, action: str) -> Optional[Dict[str, Any]]:
        """Get information about an intent action"""
        if not self.dispatcher.has_handler(action):
            return None
        
        return {
            "action": action,
            "has_handler": True,
            "handler_available": True,
        }


# Import asyncio for iscoroutinefunction
import asyncio
