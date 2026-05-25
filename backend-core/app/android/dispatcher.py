"""
Android Intent Dispatcher - Routes and dispatches intents to appropriate handlers
"""
from typing import Dict, Any, Optional, Callable, List
from app.android.models import AndroidIntent, AndroidResponse, IntentType
import asyncio
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class IntentDispatcher:
    """
    Routes Android intents to appropriate handlers.
    Manages intent processing pipelines and response handling.
    """
    
    def __init__(self):
        self._handlers: Dict[str, Callable] = {}
        self._type_handlers: Dict[IntentType, List[Callable]] = {}
        logger.info("Intent Dispatcher initialized")
    
    def register_handler(
        self,
        action: str,
        handler: Callable,
    ) -> None:
        """Register handler for specific action"""
        self._handlers[action] = handler
        logger.info(f"Registered handler for action: {action}")
    
    def register_type_handler(
        self,
        intent_type: IntentType,
        handler: Callable,
    ) -> None:
        """Register handler for intent type"""
        if intent_type not in self._type_handlers:
            self._type_handlers[intent_type] = []
        self._type_handlers[intent_type].append(handler)
        logger.info(f"Registered handler for intent type: {intent_type.value}")
    
    async def dispatch(self, intent: AndroidIntent) -> AndroidResponse:
        """
        Dispatch an intent to appropriate handler.
        
        Args:
            intent: Android intent to process
        
        Returns:
            Android response from handler
        """
        start_time = datetime.utcnow()
        
        try:
            logger.info(
                f"Dispatching intent: {intent.action} "
                f"(device: {intent.device_id}, user: {intent.user_id})"
            )
            
            # Try action-specific handler first
            if intent.action in self._handlers:
                handler = self._handlers[intent.action]
                result = await self._execute_handler(handler, intent)
                
                execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                
                return AndroidResponse(
                    request_id=intent.request_id,
                    success=True,
                    data=result,
                    device_id=intent.device_id,
                    execution_time_ms=execution_time,
                )
            
            # Try type-specific handlers
            handlers = self._type_handlers.get(intent.intent_type, [])
            if handlers:
                for handler in handlers:
                    result = await self._execute_handler(handler, intent)
                    if result is not None:
                        execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                        return AndroidResponse(
                            request_id=intent.request_id,
                            success=True,
                            data=result,
                            device_id=intent.device_id,
                            execution_time_ms=execution_time,
                        )
            
            # No handler found
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            error_msg = f"No handler for action: {intent.action}"
            
            logger.warning(f"✗ {error_msg}")
            return AndroidResponse(
                request_id=intent.request_id,
                success=False,
                error=error_msg,
                error_type="NoHandlerError",
                device_id=intent.device_id,
                execution_time_ms=execution_time,
            )
            
        except asyncio.TimeoutError:
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            error_msg = f"Intent processing timeout ({intent.timeout_seconds}s)"
            
            logger.warning(f"⚠ {error_msg}")
            return AndroidResponse(
                request_id=intent.request_id,
                success=False,
                error=error_msg,
                error_type="TimeoutError",
                device_id=intent.device_id,
                execution_time_ms=execution_time,
            )
            
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            logger.error(f"✗ Error dispatching intent: {e}")
            return AndroidResponse(
                request_id=intent.request_id,
                success=False,
                error=str(e),
                error_type=type(e).__name__,
                device_id=intent.device_id,
                execution_time_ms=execution_time,
            )
    
    async def _execute_handler(
        self,
        handler: Callable,
        intent: AndroidIntent,
    ) -> Any:
        """Execute handler with timeout"""
        try:
            if asyncio.iscoroutinefunction(handler):
                return await asyncio.wait_for(
                    handler(intent),
                    timeout=intent.timeout_seconds,
                )
            else:
                # Run sync function in thread pool
                loop = asyncio.get_event_loop()
                return await asyncio.wait_for(
                    loop.run_in_executor(None, handler, intent),
                    timeout=intent.timeout_seconds,
                )
        except asyncio.TimeoutError:
            raise
        except Exception:
            raise
    
    def has_handler(self, action: str) -> bool:
        """Check if handler exists for action"""
        return action in self._handlers
    
    def has_type_handler(self, intent_type: IntentType) -> bool:
        """Check if handler exists for intent type"""
        return intent_type in self._type_handlers and len(self._type_handlers[intent_type]) > 0
