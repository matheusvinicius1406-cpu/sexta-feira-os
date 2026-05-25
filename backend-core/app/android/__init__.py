"""
Android Module - Android-specific functionality and integration
Provides intent dispatching, request handling, and device communication.
"""
from app.android.dispatcher import IntentDispatcher
from app.android.intent_builder import IntentBuilder
from app.android.intent_service import IntentService
from app.android.models import AndroidIntent, AndroidResponse

__all__ = [
    "IntentDispatcher",
    "IntentBuilder",
    "IntentService",
    "AndroidIntent",
    "AndroidResponse",
]
