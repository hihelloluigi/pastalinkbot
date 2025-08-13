"""
Common Decorators Module

This module provides common decorators used throughout the application,
including error handling, rate limiting, and Telegram-specific decorators.

Decorators:
    handle_telegram_errors: Error handling for Telegram handlers
    require_admin: Restrict commands to admin users
    log_handler_call: Log Telegram handler calls
    rate_limit: Simple rate limiting decorator
    retry: Retry decorator for unreliable operations
"""

import asyncio
import functools
import logging
import time
from collections import defaultdict
from typing import Any, Callable, Dict, Optional, Set

from telegram import Update
from telegram.ext import ContextTypes

from config.constants import ERROR_MESSAGES
from utils.i18n import get_translator

logger = logging.getLogger(__name__)


def handle_telegram_errors(func: Callable) -> Callable:
    """
    Decorator to handle common Telegram bot errors gracefully.

    This decorator catches exceptions in Telegram handlers and sends
    user-friendly error messages instead of letting the bot crash.

    Args:
        func: Telegram handler function to wrap

    Returns:
        Callable: Wrapped handler function
    """

    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            return await func(update, context)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}", exc_info=True)

            # Try to send error message to user
            try:
                user_lang = None
                if update.effective_user:
                    user_lang = update.effective_user.language_code

                _ = get_translator(user_lang)
                error_message = _(ERROR_MESSAGES["generic"])

                if update.message:
                    await update.message.reply_text(error_message)
                elif update.callback_query:
                    await update.callback_query.answer(error_message)

            except Exception as nested_e:
                logger.error(f"Failed to send error message to user: {nested_e}")

    return wrapper


def require_admin(admin_user_ids: Set[int]) -> Callable:
    """
    Decorator to restrict commands to admin users only.

    Args:
        admin_user_ids: Set of Telegram user IDs with admin privileges

    Returns:
        Callable: Decorator function
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if not update.effective_user:
                return

            user_id = update.effective_user.id

            if user_id not in admin_user_ids:
                _ = get_translator(update.effective_user.language_code)
                await update.message.reply_text(_(ERROR_MESSAGES["admin_only"]))
                return

            return await func(update, context)

        return wrapper

    return decorator


def log_handler_call(func: Callable) -> Callable:
    """
    Decorator to log Telegram handler calls with user information.

    Args:
        func: Telegram handler function to wrap

    Returns:
        Callable: Wrapped handler function
    """

    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Extract user and message info
        user_id = update.effective_user.id if update.effective_user else "unknown"
        username = update.effective_user.username if update.effective_user else "unknown"
        chat_id = update.effective_chat.id if update.effective_chat else "unknown"

        message_text = ""
        if update.message and update.message.text:
            # Log first 50 chars of message for context
            message_text = update.message.text[:50]
            if len(update.message.text) > 50:
                message_text += "..."

        logger.info(
            f"Handler {func.__name__} called by user {user_id} (@{username}) "
            f"in chat {chat_id}. Message: '{message_text}'"
        )

        start_time = time.time()
        try:
            result = await func(update, context)
            duration = time.time() - start_time
            logger.debug(f"Handler {func.__name__} completed in {duration:.3f}s")
            return result
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Handler {func.__name__} failed after {duration:.3f}s: {e}")
            raise

    return wrapper


class RateLimiter:
    """
    Simple rate limiter for preventing spam.

    Tracks requests per user and enforces limits.
    """

    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        """
        Initialize rate limiter.

        Args:
            max_requests: Maximum requests per window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[int, list] = defaultdict(list)

    def is_allowed(self, user_id: int) -> bool:
        """
        Check if user is allowed to make a request.

        Args:
            user_id: Telegram user ID

        Returns:
            bool: True if request is allowed, False otherwise
        """
        now = time.time()
        user_requests = self.requests[user_id]

        # Remove old requests outside the window
        user_requests[:] = [
            req_time for req_time in user_requests if now - req_time < self.window_seconds
        ]

        # Check if under limit
        if len(user_requests) >= self.max_requests:
            return False

        # Add current request
        user_requests.append(now)
        return True

    def get_reset_time(self, user_id: int) -> Optional[float]:
        """
        Get time until rate limit resets for user.

        Args:
            user_id: Telegram user ID

        Returns:
            Optional[float]: Seconds until reset, or None if not rate limited
        """
        if user_id not in self.requests:
            return None

        user_requests = self.requests[user_id]
        if not user_requests:
            return None

        oldest_request = min(user_requests)
        reset_time = oldest_request + self.window_seconds
        current_time = time.time()

        return max(0, reset_time - current_time)


def rate_limit(max_requests: int = 10, window_seconds: int = 60) -> Callable:
    """
    Decorator to add rate limiting to Telegram handlers.

    Args:
        max_requests: Maximum requests per window
        window_seconds: Time window in seconds

    Returns:
        Callable: Decorator function
    """
    limiter = RateLimiter(max_requests, window_seconds)

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if not update.effective_user:
                return

            user_id = update.effective_user.id

            if not limiter.is_allowed(user_id):
                reset_time = limiter.get_reset_time(user_id)
                _ = get_translator(update.effective_user.language_code)

                if reset_time:
                    message = f"Rate limit exceeded. Please wait {int(reset_time)} seconds."
                else:
                    message = "Rate limit exceeded. Please wait before trying again."

                await update.message.reply_text(_(message))
                logger.warning(f"Rate limit exceeded for user {user_id}")
                return

            return await func(update, context)

        return wrapper

    return decorator


def retry(
    max_attempts: int = 3,
    delay_seconds: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,),
) -> Callable:
    """
    Decorator to retry functions that may fail temporarily.

    Args:
        max_attempts: Maximum number of retry attempts
        delay_seconds: Initial delay between retries
        backoff_factor: Multiplier for delay on each retry
        exceptions: Tuple of exceptions to catch and retry

    Returns:
        Callable: Decorator function
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exception = None
            delay = delay_seconds

            for attempt in range(max_attempts):
                try:
                    if asyncio.iscoroutinefunction(func):
                        return await func(*args, **kwargs)
                    else:
                        return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt == max_attempts - 1:
                        # Last attempt failed, re-raise
                        break

                    logger.warning(
                        f"Attempt {attempt + 1}/{max_attempts} failed for {func.__name__}: {e}. "
                        f"Retrying in {delay}s"
                    )

                    await asyncio.sleep(delay)
                    delay *= backoff_factor

            # All attempts failed
            logger.error(
                f"All {max_attempts} attempts failed for {func.__name__}: {last_exception}"
            )
            raise last_exception

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            last_exception = None
            delay = delay_seconds

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt == max_attempts - 1:
                        # Last attempt failed, re-raise
                        break

                    logger.warning(
                        f"Attempt {attempt + 1}/{max_attempts} failed for {func.__name__}: {e}. "
                        f"Retrying in {delay}s"
                    )

                    time.sleep(delay)
                    delay *= backoff_factor

            # All attempts failed
            logger.error(
                f"All {max_attempts} attempts failed for {func.__name__}: {last_exception}"
            )
            raise last_exception

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def cache_result(ttl_seconds: int = 300) -> Callable:
    """
    Simple cache decorator for function results.

    Args:
        ttl_seconds: Time to live for cached results

    Returns:
        Callable: Decorator function
    """

    def decorator(func: Callable) -> Callable:
        cache: Dict[str, tuple] = {}  # key -> (result, timestamp)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key from arguments
            cache_key = str(hash((args, tuple(sorted(kwargs.items())))))

            now = time.time()

            # Check if we have a valid cached result
            if cache_key in cache:
                result, timestamp = cache[cache_key]
                if now - timestamp < ttl_seconds:
                    logger.debug(f"Cache hit for {func.__name__}")
                    return result

            # Compute result and cache it
            result = func(*args, **kwargs)
            cache[cache_key] = (result, now)

            # Clean old entries periodically
            if len(cache) > 1000:  # Prevent unbounded growth
                cutoff_time = now - ttl_seconds
                cache.clear()  # Simple cleanup - remove all

            logger.debug(f"Cache miss for {func.__name__}")
            return result

        return wrapper

    return decorator


def validate_update(func: Callable) -> Callable:
    """
    Decorator to validate Telegram update objects.

    Args:
        func: Telegram handler function to wrap

    Returns:
        Callable: Wrapped handler function
    """

    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Basic validation
        if not update:
            logger.error("Received None update")
            return

        if not update.effective_user:
            logger.warning("Update has no effective_user")
            return

        if not update.effective_chat:
            logger.warning("Update has no effective_chat")
            return

        return await func(update, context)

    return wrapper
