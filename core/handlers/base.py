"""
Base Handler Classes

This module contains base classes and utilities for all handlers.
It provides common functionality and interfaces that all handlers can inherit from.

Classes:
    BaseHandler: Abstract base class for all handlers
    HandlerRegistry: Registry for managing handlers
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type

from telegram import Update
from telegram.ext import BaseHandler as TelegramBaseHandler
from telegram.ext import ContextTypes

from utils.logging import LoggerMixin

logger = logging.getLogger(__name__)


class BaseHandler(LoggerMixin, ABC):
    """
    Abstract base class for all bot handlers.

    This class provides common functionality that all handlers should have,
    including logging, error handling, and service access patterns.
    """

    def __init__(self, handler_name: str):
        """
        Initialize base handler.

        Args:
            handler_name: Name of the handler for logging purposes
        """
        self.handler_name = handler_name
        self.logger.info(f"Handler '{handler_name}' initialized")

    @abstractmethod
    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> Any:
        """
        Abstract method for handling updates.

        All concrete handlers must implement this method.

        Args:
            update: Telegram update object
            context: Telegram context object

        Returns:
            Any: Handler-specific return value
        """
        pass

    def get_user_info(self, update: Update) -> Dict[str, Any]:
        """
        Extract user information from update.

        Args:
            update: Telegram update object

        Returns:
            Dict[str, Any]: User information dictionary
        """
        if not update.effective_user:
            return {"user_id": None, "username": None, "language_code": None}

        return {
            "user_id": update.effective_user.id,
            "username": update.effective_user.username,
            "first_name": update.effective_user.first_name,
            "last_name": update.effective_user.last_name,
            "language_code": update.effective_user.language_code,
            "is_bot": update.effective_user.is_bot,
        }

    def get_chat_info(self, update: Update) -> Dict[str, Any]:
        """
        Extract chat information from update.

        Args:
            update: Telegram update object

        Returns:
            Dict[str, Any]: Chat information dictionary
        """
        if not update.effective_chat:
            return {"chat_id": None, "chat_type": None}

        return {
            "chat_id": update.effective_chat.id,
            "chat_type": update.effective_chat.type,
            "title": getattr(update.effective_chat, "title", None),
        }

    def get_message_info(self, update: Update) -> Dict[str, Any]:
        """
        Extract message information from update.

        Args:
            update: Telegram update object

        Returns:
            Dict[str, Any]: Message information dictionary
        """
        if not update.message:
            return {"message_id": None, "text": None, "date": None}

        return {
            "message_id": update.message.message_id,
            "text": update.message.text,
            "date": update.message.date,
            "reply_to_message_id": (
                getattr(update.message.reply_to_message, "message_id", None)
                if update.message.reply_to_message
                else None
            ),
        }

    def log_handler_call(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Log handler call with context information.

        Args:
            update: Telegram update object
            context: Telegram context object
        """
        user_info = self.get_user_info(update)
        chat_info = self.get_chat_info(update)
        message_info = self.get_message_info(update)

        self.logger.info(
            f"Handler '{self.handler_name}' called - "
            f"User: {user_info['user_id']} (@{user_info['username']}), "
            f"Chat: {chat_info['chat_id']} ({chat_info['chat_type']}), "
            f"Message: '{message_info['text'][:50] if message_info['text'] else ''}'"
        )


class HandlerRegistry:
    """
    Registry for managing and organizing handlers.

    This class provides a centralized way to register, retrieve,
    and manage all bot handlers.
    """

    def __init__(self):
        """Initialize handler registry."""
        self._handlers: Dict[str, BaseHandler] = {}
        self._handler_types: Dict[str, Type[BaseHandler]] = {}
        self.logger = logging.getLogger(f"{__name__}.HandlerRegistry")

        self.logger.info("Handler registry initialized")

    def register_handler(self, name: str, handler: BaseHandler) -> None:
        """
        Register a handler instance.

        Args:
            name: Handler name
            handler: Handler instance
        """
        if name in self._handlers:
            self.logger.warning(f"Handler '{name}' already registered, overwriting")

        self._handlers[name] = handler
        self._handler_types[name] = type(handler)

        self.logger.info(f"Registered handler '{name}' of type {type(handler).__name__}")

    def get_handler(self, name: str) -> Optional[BaseHandler]:
        """
        Get a registered handler by name.

        Args:
            name: Handler name

        Returns:
            Optional[BaseHandler]: Handler instance or None if not found
        """
        return self._handlers.get(name)

    def get_all_handlers(self) -> Dict[str, BaseHandler]:
        """
        Get all registered handlers.

        Returns:
            Dict[str, BaseHandler]: Dictionary of all handlers
        """
        return self._handlers.copy()

    def get_handlers_by_type(self, handler_type: Type[BaseHandler]) -> List[BaseHandler]:
        """
        Get all handlers of a specific type.

        Args:
            handler_type: Handler type class

        Returns:
            List[BaseHandler]: List of handlers of the specified type
        """
        return [handler for handler in self._handlers.values() if isinstance(handler, handler_type)]

    def unregister_handler(self, name: str) -> bool:
        """
        Unregister a handler.

        Args:
            name: Handler name to unregister

        Returns:
            bool: True if handler was found and removed, False otherwise
        """
        if name in self._handlers:
            del self._handlers[name]
            del self._handler_types[name]
            self.logger.info(f"Unregistered handler '{name}'")
            return True

        self.logger.warning(f"Attempted to unregister unknown handler '{name}'")
        return False

    def list_handler_names(self) -> List[str]:
        """
        Get list of all registered handler names.

        Returns:
            List[str]: List of handler names
        """
        return list(self._handlers.keys())

    def get_handler_stats(self) -> Dict[str, Any]:
        """
        Get statistics about registered handlers.

        Returns:
            Dict[str, Any]: Handler statistics
        """
        type_counts = {}
        for handler_type in self._handler_types.values():
            type_name = handler_type.__name__
            type_counts[type_name] = type_counts.get(type_name, 0) + 1

        return {
            "total_handlers": len(self._handlers),
            "handler_types": type_counts,
            "handler_names": self.list_handler_names(),
        }

    def clear_all_handlers(self) -> None:
        """Clear all registered handlers."""
        count = len(self._handlers)
        self._handlers.clear()
        self._handler_types.clear()
        self.logger.info(f"Cleared {count} registered handlers")


class HandlerValidationMixin:
    """
    Mixin class providing common validation methods for handlers.

    This mixin can be used by handler classes to add common validation
    functionality without inheritance complexity.
    """

    @staticmethod
    def validate_update(update: Update) -> bool:
        """
        Validate that update object is properly formed.

        Args:
            update: Telegram update object to validate

        Returns:
            bool: True if update is valid, False otherwise
        """
        if not update:
            return False

        if not update.effective_user:
            return False

        if not update.effective_chat:
            return False

        return True

    @staticmethod
    def validate_message_content(update: Update) -> bool:
        """
        Validate that update contains a valid message.

        Args:
            update: Telegram update object to validate

        Returns:
            bool: True if message is valid, False otherwise
        """
        if not update.message:
            return False

        if not update.message.text:
            return False

        if not update.message.text.strip():
            return False

        return True

    @staticmethod
    def validate_user_permissions(update: Update, required_permissions: List[str] = None) -> bool:
        """
        Validate user permissions (placeholder for future implementation).

        Args:
            update: Telegram update object
            required_permissions: List of required permissions

        Returns:
            bool: True if user has required permissions
        """
        # Placeholder implementation
        # In a real application, you would check user permissions here
        return True


class HandlerMetrics:
    """
    Class for tracking handler performance metrics.

    This class can be used to track calls, response times,
    success rates, and other metrics for handlers.
    """

    def __init__(self):
        """Initialize handler metrics."""
        self.metrics: Dict[str, Dict[str, Any]] = {}
        self.logger = logging.getLogger(f"{__name__}.HandlerMetrics")

    def record_handler_call(
        self, handler_name: str, success: bool = True, duration: float = 0.0
    ) -> None:
        """
        Record a handler call.

        Args:
            handler_name: Name of the handler
            success: Whether the call was successful
            duration: Duration of the call in seconds
        """
        if handler_name not in self.metrics:
            self.metrics[handler_name] = {
                "total_calls": 0,
                "successful_calls": 0,
                "failed_calls": 0,
                "total_duration": 0.0,
                "average_duration": 0.0,
            }

        metrics = self.metrics[handler_name]
        metrics["total_calls"] += 1

        if success:
            metrics["successful_calls"] += 1
        else:
            metrics["failed_calls"] += 1

        metrics["total_duration"] += duration
        metrics["average_duration"] = metrics["total_duration"] / metrics["total_calls"]

    def get_handler_metrics(self, handler_name: str) -> Optional[Dict[str, Any]]:
        """
        Get metrics for a specific handler.

        Args:
            handler_name: Name of the handler

        Returns:
            Optional[Dict[str, Any]]: Metrics dictionary or None if not found
        """
        return self.metrics.get(handler_name)

    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """
        Get metrics for all handlers.

        Returns:
            Dict[str, Dict[str, Any]]: All metrics
        """
        return self.metrics.copy()

    def reset_metrics(self, handler_name: Optional[str] = None) -> None:
        """
        Reset metrics for a handler or all handlers.

        Args:
            handler_name: Optional handler name. If None, resets all metrics.
        """
        if handler_name:
            if handler_name in self.metrics:
                del self.metrics[handler_name]
                self.logger.info(f"Reset metrics for handler '{handler_name}'")
        else:
            self.metrics.clear()
            self.logger.info("Reset all handler metrics")


# Global instances for use throughout the application
handler_registry = HandlerRegistry()
handler_metrics = HandlerMetrics()
