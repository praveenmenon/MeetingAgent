"""
Rate limiting and retry logic for AI API calls
"""

import asyncio
import time
import random
import logging
from typing import Dict, Any, Optional, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import threading
from collections import deque, defaultdict
import json


class APIProvider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class RateLimitType(Enum):
    REQUESTS_PER_MINUTE = "rpm"
    TOKENS_PER_MINUTE = "tpm"
    REQUESTS_PER_DAY = "rpd"
    TOKENS_PER_DAY = "tpd"


@dataclass
class RateLimitInfo:
    """Information about rate limits from API response headers"""
    limit_requests: Optional[int] = None
    limit_tokens: Optional[int] = None
    remaining_requests: Optional[int] = None
    remaining_tokens: Optional[int] = None
    reset_requests: Optional[float] = None
    reset_tokens: Optional[float] = None
    retry_after: Optional[float] = None


@dataclass
class RetryConfig:
    """Configuration for retry logic"""
    max_retries: int = 5
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    jitter_max: float = 0.1
    
    # Rate limit specific delays
    rate_limit_delay: float = 60.0
    quota_exceeded_delay: float = 3600.0  # 1 hour for quota exceeded


class RequestQueue:
    """Queue for managing API requests with rate limiting"""
    
    def __init__(self, max_size: int = 1000):
        self.queue = deque()
        self.max_size = max_size
        self._lock = threading.Lock()
        
    def add_request(self, request_data: Dict[str, Any]) -> bool:
        """Add request to queue. Returns False if queue is full"""
        with self._lock:
            if len(self.queue) >= self.max_size:
                return False
            
            request_data['queued_at'] = time.time()
            self.queue.append(request_data)
            return True
    
    def get_next_request(self) -> Optional[Dict[str, Any]]:
        """Get next request from queue"""
        with self._lock:
            if self.queue:
                return self.queue.popleft()
            return None
    
    def size(self) -> int:
        """Get current queue size"""
        with self._lock:
            return len(self.queue)
    
    def clear(self):
        """Clear all requests from queue"""
        with self._lock:
            self.queue.clear()


class RateLimiter:
    """Rate limiter with exponential backoff and request queuing"""
    
    def __init__(self, retry_config: RetryConfig = None):
        self.retry_config = retry_config or RetryConfig()
        self.request_queues = {
            APIProvider.OPENAI: RequestQueue(),
            APIProvider.ANTHROPIC: RequestQueue()
        }
        
        # Track rate limit info per provider
        self.rate_limits = {
            APIProvider.OPENAI: RateLimitInfo(),
            APIProvider.ANTHROPIC: RateLimitInfo()
        }
        
        # Track request history for local rate limiting
        self.request_history = {
            APIProvider.OPENAI: deque(),
            APIProvider.ANTHROPIC: deque()
        }
        
        # Exponential backoff state
        self.backoff_until = {
            APIProvider.OPENAI: 0,
            APIProvider.ANTHROPIC: 0
        }
        
        self.logger = logging.getLogger(__name__)
        
    def _add_jitter(self, delay: float) -> float:
        """Add jitter to delay to avoid thundering herd"""
        if not self.retry_config.jitter:
            return delay
            
        jitter = random.uniform(0, self.retry_config.jitter_max * delay)
        return delay + jitter
    
    def _calculate_backoff_delay(self, attempt: int, error_type: str = "generic") -> float:
        """Calculate exponential backoff delay with jitter"""
        if error_type == "rate_limit":
            base_delay = self.retry_config.rate_limit_delay
        elif error_type == "quota_exceeded":
            base_delay = self.retry_config.quota_exceeded_delay
        else:
            base_delay = self.retry_config.base_delay
        
        # Exponential backoff
        delay = min(
            base_delay * (self.retry_config.exponential_base ** attempt),
            self.retry_config.max_delay
        )
        
        return self._add_jitter(delay)
    
    def _parse_openai_rate_limit_headers(self, response) -> RateLimitInfo:
        """Parse OpenAI rate limit headers"""
        headers = getattr(response, 'headers', {}) or {}
        
        return RateLimitInfo(
            limit_requests=self._safe_int(headers.get('x-ratelimit-limit-requests')),
            limit_tokens=self._safe_int(headers.get('x-ratelimit-limit-tokens')),
            remaining_requests=self._safe_int(headers.get('x-ratelimit-remaining-requests')),
            remaining_tokens=self._safe_int(headers.get('x-ratelimit-remaining-tokens')),
            reset_requests=self._safe_float(headers.get('x-ratelimit-reset-requests')),
            reset_tokens=self._safe_float(headers.get('x-ratelimit-reset-tokens'))
        )
    
    def _parse_anthropic_rate_limit_headers(self, response) -> RateLimitInfo:
        """Parse Anthropic rate limit headers"""
        headers = getattr(response, 'headers', {}) or {}
        
        return RateLimitInfo(
            limit_requests=self._safe_int(headers.get('anthropic-ratelimit-requests-limit')),
            limit_tokens=self._safe_int(headers.get('anthropic-ratelimit-tokens-limit')),
            remaining_requests=self._safe_int(headers.get('anthropic-ratelimit-requests-remaining')),
            remaining_tokens=self._safe_int(headers.get('anthropic-ratelimit-tokens-remaining')),
            reset_requests=self._safe_float(headers.get('anthropic-ratelimit-requests-reset')),
            reset_tokens=self._safe_float(headers.get('anthropic-ratelimit-tokens-reset')),
            retry_after=self._safe_float(headers.get('retry-after'))
        )
    
    def _safe_int(self, value) -> Optional[int]:
        """Safely convert to int"""
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None
    
    def _safe_float(self, value) -> Optional[float]:
        """Safely convert to float"""
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def _should_retry(self, error: Exception, attempt: int) -> tuple[bool, str]:
        """Determine if request should be retried and error type"""
        if attempt >= self.retry_config.max_retries:
            return False, "max_retries_exceeded"
        
        error_msg = str(error).lower()
        error_type = type(error).__name__.lower()
        
        # Rate limiting errors
        if any(term in error_msg for term in ['rate limit', 'too many requests', '429']):
            return True, "rate_limit"
        
        # Quota exceeded errors
        if any(term in error_msg for term in ['quota exceeded', 'insufficient_quota', 'billing']):
            return True, "quota_exceeded"
        
        # Server errors (5xx)
        if any(term in error_msg for term in ['500', '502', '503', '504', 'internal server', 'bad gateway', 'service unavailable']):
            return True, "server_error"
        
        # Connection errors
        if any(term in error_msg for term in ['connection', 'timeout', 'network']):
            return True, "connection_error"
        
        # Don't retry client errors (4xx except 429)
        if any(term in error_msg for term in ['400', '401', '403', '404', 'invalid', 'unauthorized', 'forbidden']):
            return False, "client_error"
        
        # Default: retry for unknown errors
        return True, "generic"
    
    def _wait_for_backoff(self, provider: APIProvider):
        """Wait if we're in backoff period"""
        backoff_until = self.backoff_until[provider]
        if backoff_until > time.time():
            wait_time = backoff_until - time.time()
            self.logger.info(f"Waiting {wait_time:.1f}s due to {provider.value} backoff")
            time.sleep(wait_time)
    
    def _update_rate_limit_info(self, provider: APIProvider, response):
        """Update rate limit information from response"""
        try:
            if provider == APIProvider.OPENAI:
                rate_info = self._parse_openai_rate_limit_headers(response)
            else:
                rate_info = self._parse_anthropic_rate_limit_headers(response)
            
            self.rate_limits[provider] = rate_info
            
            # Log rate limit status
            if rate_info.remaining_requests is not None and rate_info.limit_requests is not None:
                usage_pct = (1 - rate_info.remaining_requests / rate_info.limit_requests) * 100
                if usage_pct > 80:
                    self.logger.warning(
                        f"{provider.value} request limit usage: {usage_pct:.1f}% "
                        f"({rate_info.remaining_requests}/{rate_info.limit_requests})"
                    )
                    
        except Exception as e:
            self.logger.warning(f"Failed to parse rate limit headers for {provider.value}: {e}")
    
    def _queue_request(self, provider: APIProvider, request_func: Callable, *args, **kwargs) -> bool:
        """Queue a request for later execution"""
        request_data = {
            'func': request_func,
            'args': args,
            'kwargs': kwargs,
            'provider': provider
        }
        
        success = self.request_queues[provider].add_request(request_data)
        if success:
            self.logger.info(f"Queued request for {provider.value} (queue size: {self.request_queues[provider].size()})")
        else:
            self.logger.warning(f"Request queue full for {provider.value}")
        
        return success
    
    async def execute_with_retry(
        self,
        provider: APIProvider,
        request_func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """Execute request with retry logic and rate limiting"""
        
        # Wait for any existing backoff period
        self._wait_for_backoff(provider)
        
        last_error = None
        
        for attempt in range(self.retry_config.max_retries + 1):
            try:
                # Record request time for local rate limiting
                self.request_history[provider].append(time.time())
                
                # Clean old history (keep last 60 seconds)
                cutoff = time.time() - 60
                while self.request_history[provider] and self.request_history[provider][0] < cutoff:
                    self.request_history[provider].popleft()
                
                # Make the API call
                response = request_func(*args, **kwargs)
                
                # Update rate limit info if response has headers
                self._update_rate_limit_info(provider, response)
                
                # Success - reset backoff
                self.backoff_until[provider] = 0
                
                return response
                
            except Exception as error:
                last_error = error
                should_retry, error_type = self._should_retry(error, attempt)
                
                if not should_retry:
                    self.logger.error(f"{provider.value} request failed (no retry): {error}")
                    raise error
                
                # Calculate delay
                delay = self._calculate_backoff_delay(attempt, error_type)
                
                # Set backoff period
                self.backoff_until[provider] = time.time() + delay
                
                self.logger.warning(
                    f"{provider.value} request failed (attempt {attempt + 1}/{self.retry_config.max_retries + 1}): "
                    f"{error}. Retrying in {delay:.1f}s"
                )
                
                # For quota exceeded, also try to queue the request
                if error_type == "quota_exceeded":
                    self.logger.info(f"Attempting to queue request due to quota exceeded")
                    self._queue_request(provider, request_func, *args, **kwargs)
                
                # Wait before retry
                if attempt < self.retry_config.max_retries:
                    await asyncio.sleep(delay)
        
        # All retries exhausted
        self.logger.error(f"{provider.value} request failed after {self.retry_config.max_retries} retries: {last_error}")
        raise last_error
    
    def execute_with_retry_sync(
        self,
        provider: APIProvider,
        request_func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """Synchronous version of execute_with_retry"""
        
        # Wait for any existing backoff period
        self._wait_for_backoff(provider)
        
        last_error = None
        
        for attempt in range(self.retry_config.max_retries + 1):
            try:
                # Record request time for local rate limiting
                self.request_history[provider].append(time.time())
                
                # Clean old history (keep last 60 seconds)
                cutoff = time.time() - 60
                while self.request_history[provider] and self.request_history[provider][0] < cutoff:
                    self.request_history[provider].popleft()
                
                # Make the API call
                response = request_func(*args, **kwargs)
                
                # Update rate limit info if response has headers
                self._update_rate_limit_info(provider, response)
                
                # Success - reset backoff
                self.backoff_until[provider] = 0
                
                return response
                
            except Exception as error:
                last_error = error
                should_retry, error_type = self._should_retry(error, attempt)
                
                if not should_retry:
                    self.logger.error(f"{provider.value} request failed (no retry): {error}")
                    raise error
                
                # Calculate delay
                delay = self._calculate_backoff_delay(attempt, error_type)
                
                # Set backoff period
                self.backoff_until[provider] = time.time() + delay
                
                self.logger.warning(
                    f"{provider.value} request failed (attempt {attempt + 1}/{self.retry_config.max_retries + 1}): "
                    f"{error}. Retrying in {delay:.1f}s"
                )
                
                # For quota exceeded, also try to queue the request
                if error_type == "quota_exceeded":
                    self.logger.info(f"Attempting to queue request due to quota exceeded")
                    self._queue_request(provider, request_func, *args, **kwargs)
                
                # Wait before retry
                if attempt < self.retry_config.max_retries:
                    time.sleep(delay)
        
        # All retries exhausted
        self.logger.error(f"{provider.value} request failed after {self.retry_config.max_retries} retries: {last_error}")
        raise last_error
    
    def get_rate_limit_status(self, provider: APIProvider) -> Dict[str, Any]:
        """Get current rate limit status"""
        rate_info = self.rate_limits[provider]
        history = self.request_history[provider]
        
        # Calculate recent request rate
        recent_requests = len([t for t in history if t > time.time() - 60])
        
        return {
            "provider": provider.value,
            "requests_last_minute": recent_requests,
            "limit_requests": rate_info.limit_requests,
            "remaining_requests": rate_info.remaining_requests,
            "limit_tokens": rate_info.limit_tokens,
            "remaining_tokens": rate_info.remaining_tokens,
            "reset_requests": rate_info.reset_requests,
            "reset_tokens": rate_info.reset_tokens,
            "backoff_until": self.backoff_until[provider],
            "queue_size": self.request_queues[provider].size()
        }
    
    def process_queued_requests(self, provider: APIProvider, max_requests: int = 10) -> int:
        """Process queued requests when rate limits allow"""
        processed = 0
        queue = self.request_queues[provider]
        
        # Check if we're still in backoff
        if self.backoff_until[provider] > time.time():
            return 0
        
        while processed < max_requests and queue.size() > 0:
            request_data = queue.get_next_request()
            if not request_data:
                break
            
            try:
                # Execute the queued request
                request_data['func'](*request_data['args'], **request_data['kwargs'])
                processed += 1
                
                self.logger.info(f"Processed queued request for {provider.value}")
                
                # Small delay between queued requests
                time.sleep(0.1)
                
            except Exception as e:
                self.logger.error(f"Failed to process queued request for {provider.value}: {e}")
                # Re-queue if it's a retryable error
                should_retry, _ = self._should_retry(e, 0)
                if should_retry:
                    queue.add_request(request_data)
        
        return processed


# Global rate limiter instance
_rate_limiter = RateLimiter()


def get_rate_limiter() -> RateLimiter:
    """Get the global rate limiter instance"""
    return _rate_limiter


def configure_rate_limiter(retry_config: RetryConfig):
    """Configure the global rate limiter"""
    global _rate_limiter
    _rate_limiter = RateLimiter(retry_config)