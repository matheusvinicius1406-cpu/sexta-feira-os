"""
Structured logging configuration for Sexta-Feira OS
Implements JSON logging, correlation IDs, and contextual logging
"""
import logging
import json
from typing import Any, Dict, Optional
from datetime import datetime
from pythonjsonlogger import jsonlogger
import sys
from contextvars import ContextVar


# Context variables for correlation tracking
correlation_id_ctx: ContextVar[str] = ContextVar('correlation_id', default='')
user_id_ctx: ContextVar[str] = ContextVar('user_id', default='')
request_id_ctx: ContextVar[str] = ContextVar('request_id', default='')


class ContextFilter(logging.Filter):
    """Filter to add context variables to log records"""
    
    def filter(self, record):
        record.correlation_id = correlation_id_ctx.get('')
        record.user_id = user_id_ctx.get('')
        record.request_id = request_id_ctx.get('')
        return True


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional fields"""
    
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        log_record['timestamp'] = datetime.utcnow().isoformat()
        log_record['level'] = record.levelname
        log_record['logger'] = record.name
        log_record['module'] = record.module
        log_record['function'] = record.funcName
        log_record['line'] = record.lineno
        
        # Add context
        if hasattr(record, 'correlation_id'):
            log_record['correlation_id'] = record.correlation_id
        if hasattr(record, 'user_id'):
            log_record['user_id'] = record.user_id
        if hasattr(record, 'request_id'):
            log_record['request_id'] = record.request_id
        
        # Add exception info
        if record.exc_info:
            log_record['exception'] = self.formatException(record.exc_info)


def setup_logging(log_level: str = "INFO", json_output: bool = True) -> None:
    """Setup structured logging for the application"""
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    
    # Add context filter
    context_filter = ContextFilter()
    console_handler.addFilter(context_filter)
    
    if json_output:
        # JSON formatter
        formatter = CustomJsonFormatter('%(message)s %(additional)s')
    else:
        # Pretty formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(correlation_id)s - %(message)s'
        )
    
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)


class StructuredLogger:
    """Structured logger wrapper with correlation tracking"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
    
    def info(
        self,
        message: str,
        **kwargs
    ) -> None:
        """Log info with structured data"""
        self.logger.info(self._format_message(message, kwargs))
    
    def error(
        self,
        message: str,
        error: Optional[Exception] = None,
        **kwargs
    ) -> None:
        """Log error with structured data"""
        if error:
            kwargs['error'] = str(error)
            kwargs['error_type'] = type(error).__name__
        self.logger.error(self._format_message(message, kwargs), exc_info=error)
    
    def warning(
        self,
        message: str,
        **kwargs
    ) -> None:
        """Log warning with structured data"""
        self.logger.warning(self._format_message(message, kwargs))
    
    def debug(
        self,
        message: str,
        **kwargs
    ) -> None:
        """Log debug with structured data"""
        self.logger.debug(self._format_message(message, kwargs))
    
    def _format_message(self, message: str, data: Dict[str, Any]) -> str:
        """Format message with structured data"""
        if data:
            try:
                return f"{message} | {json.dumps(data)}"
            except (TypeError, ValueError):
                return message
        return message
    
    def set_correlation_id(self, correlation_id: str) -> None:
        """Set correlation ID for request tracking"""
        correlation_id_ctx.set(correlation_id)
    
    def set_user_id(self, user_id: str) -> None:
        """Set user ID for audit logging"""
        user_id_ctx.set(user_id)
    
    def set_request_id(self, request_id: str) -> None:
        """Set request ID for tracing"""
        request_id_ctx.set(request_id)


def get_logger(name: str) -> StructuredLogger:
    """Get a structured logger instance"""
    return StructuredLogger(name)


# Setup default logging on import
setup_logging()
