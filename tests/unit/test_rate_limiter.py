"""
Unit tests for rate limiter functionality
"""

import asyncio
import time
from unittest.mock import Mock, patch

import pytest

from meeting_agent.rate_limiter import (
    APIProvider,
    RateLimiter,
    RateLimitInfo,
    RequestQueue,
    RetryConfig,
)


class TestRetryConfig:
    """Test RetryConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = RetryConfig()

        assert config.max_retries == 5
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 2.0
        assert config.jitter is True
        assert config.rate_limit_delay == 60.0
        assert config.quota_exceeded_delay == 3600.0

    def test_custom_values(self):
        """Test custom configuration values."""
        config = RetryConfig(max_retries=3, base_delay=0.5, jitter=False)

        assert config.max_retries == 3
        assert config.base_delay == 0.5
        assert config.jitter is False


class TestRequestQueue:
    """Test RequestQueue functionality."""

    def test_queue_initialization(self):
        """Test queue initialization."""
        queue = RequestQueue(max_size=10)

        assert queue.size() == 0
        assert queue.max_size == 10

    def test_add_request(self):
        """Test adding requests to queue."""
        queue = RequestQueue(max_size=2)

        request1 = {"id": "req1", "data": "test"}
        request2 = {"id": "req2", "data": "test"}
        request3 = {"id": "req3", "data": "test"}

        # Should add successfully
        assert queue.add_request(request1) is True
        assert queue.size() == 1

        assert queue.add_request(request2) is True
        assert queue.size() == 2

        # Should fail when queue is full
        assert queue.add_request(request3) is False
        assert queue.size() == 2

    def test_get_next_request(self):
        """Test getting requests from queue (FIFO)."""
        queue = RequestQueue()

        request1 = {"id": "req1"}
        request2 = {"id": "req2"}

        queue.add_request(request1)
        queue.add_request(request2)

        # Should get first request added
        next_req = queue.get_next_request()
        assert next_req["id"] == "req1"
        assert queue.size() == 1

        # Should get second request
        next_req = queue.get_next_request()
        assert next_req["id"] == "req2"
        assert queue.size() == 0

        # Should return None when empty
        next_req = queue.get_next_request()
        assert next_req is None

    def test_clear_queue(self):
        """Test clearing the queue."""
        queue = RequestQueue()

        queue.add_request({"id": "req1"})
        queue.add_request({"id": "req2"})
        assert queue.size() == 2

        queue.clear()
        assert queue.size() == 0


class TestRateLimiter:
    """Test RateLimiter functionality."""

    def test_initialization(self, retry_config):
        """Test rate limiter initialization."""
        limiter = RateLimiter(retry_config)

        assert limiter.retry_config == retry_config
        assert APIProvider.OPENAI in limiter.request_queues
        assert APIProvider.ANTHROPIC in limiter.request_queues
        assert len(limiter.rate_limits) == 2
        assert len(limiter.backoff_until) == 2

    def test_add_jitter(self, retry_config):
        """Test jitter addition."""
        retry_config.jitter = True
        limiter = RateLimiter(retry_config)

        delay = 1.0
        jittered = limiter._add_jitter(delay)

        # Should be slightly different due to jitter
        assert jittered >= delay
        assert jittered <= delay * (1 + retry_config.jitter_max)

    def test_add_jitter_disabled(self, retry_config):
        """Test jitter when disabled."""
        retry_config.jitter = False
        limiter = RateLimiter(retry_config)

        delay = 1.0
        jittered = limiter._add_jitter(delay)

        assert jittered == delay

    def test_calculate_backoff_delay(self, retry_config):
        """Test backoff delay calculation."""
        retry_config.jitter = False  # Disable for predictable testing
        limiter = RateLimiter(retry_config)

        # Test exponential backoff
        delay0 = limiter._calculate_backoff_delay(0, "generic")
        delay1 = limiter._calculate_backoff_delay(1, "generic")
        delay2 = limiter._calculate_backoff_delay(2, "generic")

        assert delay1 == retry_config.base_delay * 2
        assert delay2 == retry_config.base_delay * 4

        # Test rate limit specific delay
        rate_delay = limiter._calculate_backoff_delay(0, "rate_limit")
        assert rate_delay == retry_config.rate_limit_delay

        # Test quota exceeded delay
        quota_delay = limiter._calculate_backoff_delay(0, "quota_exceeded")
        assert quota_delay == retry_config.quota_exceeded_delay

    def test_should_retry_logic(self, retry_config):
        """Test retry decision logic."""
        limiter = RateLimiter(retry_config)

        # Test different error types
        rate_limit_error = Exception("Rate limit exceeded")
        should_retry, error_type = limiter._should_retry(rate_limit_error, 1)
        assert should_retry is True
        assert error_type == "rate_limit"

        quota_error = Exception("Quota exceeded for this month")
        should_retry, error_type = limiter._should_retry(quota_error, 1)
        assert should_retry is True
        assert error_type == "quota_exceeded"

        server_error = Exception("Internal server error 500")
        should_retry, error_type = limiter._should_retry(server_error, 1)
        assert should_retry is True
        assert error_type == "server_error"

        client_error = Exception("Invalid request 400")
        should_retry, error_type = limiter._should_retry(client_error, 1)
        assert should_retry is False
        assert error_type == "client_error"

        # Test max retries exceeded
        should_retry, error_type = limiter._should_retry(rate_limit_error, 10)
        assert should_retry is False
        assert error_type == "max_retries_exceeded"

    def test_parse_openai_headers(self, retry_config):
        """Test OpenAI header parsing."""
        limiter = RateLimiter(retry_config)

        mock_response = Mock()
        mock_response.headers = {
            "x-ratelimit-limit-requests": "5000",
            "x-ratelimit-remaining-requests": "4500",
            "x-ratelimit-limit-tokens": "1000000",
            "x-ratelimit-remaining-tokens": "800000",
            "x-ratelimit-reset-requests": str(time.time() + 60),
            "x-ratelimit-reset-tokens": str(time.time() + 30),
        }

        rate_info = limiter._parse_openai_rate_limit_headers(mock_response)

        assert rate_info.limit_requests == 5000
        assert rate_info.remaining_requests == 4500
        assert rate_info.limit_tokens == 1000000
        assert rate_info.remaining_tokens == 800000

    def test_parse_anthropic_headers(self, retry_config):
        """Test Anthropic header parsing."""
        limiter = RateLimiter(retry_config)

        mock_response = Mock()
        mock_response.headers = {
            "anthropic-ratelimit-requests-limit": "50",
            "anthropic-ratelimit-requests-remaining": "30",
            "anthropic-ratelimit-tokens-limit": "40000",
            "anthropic-ratelimit-tokens-remaining": "35000",
            "retry-after": "60",
        }

        rate_info = limiter._parse_anthropic_rate_limit_headers(mock_response)

        assert rate_info.limit_requests == 50
        assert rate_info.remaining_requests == 30
        assert rate_info.limit_tokens == 40000
        assert rate_info.remaining_tokens == 35000
        assert rate_info.retry_after == 60.0

    def test_safe_conversions(self, retry_config):
        """Test safe type conversions."""
        limiter = RateLimiter(retry_config)

        # Test safe_int
        assert limiter._safe_int("123") == 123
        assert limiter._safe_int("invalid") is None
        assert limiter._safe_int(None) is None

        # Test safe_float
        assert limiter._safe_float("123.45") == 123.45
        assert limiter._safe_float("invalid") is None
        assert limiter._safe_float(None) is None

    def test_execute_with_retry_sync_success(self, retry_config):
        """Test successful synchronous execution."""
        limiter = RateLimiter(retry_config)

        mock_func = Mock(return_value="success")

        result = limiter.execute_with_retry_sync(
            APIProvider.OPENAI, mock_func, "arg1", kwarg1="value1"
        )

        assert result == "success"
        mock_func.assert_called_once_with("arg1", kwarg1="value1")

    def test_execute_with_retry_sync_with_retries(self, retry_config):
        """Test synchronous execution with retries."""
        retry_config.base_delay = 0.01  # Very small delay for testing
        limiter = RateLimiter(retry_config)

        mock_func = Mock()
        mock_func.side_effect = [
            Exception("Rate limit exceeded"),
            Exception("Rate limit exceeded"),
            "success",
        ]

        result = limiter.execute_with_retry_sync(APIProvider.OPENAI, mock_func)

        assert result == "success"
        assert mock_func.call_count == 3

    def test_execute_with_retry_sync_max_retries_exceeded(self, retry_config):
        """Test when max retries are exceeded."""
        retry_config.max_retries = 2
        retry_config.base_delay = 0.01
        limiter = RateLimiter(retry_config)

        mock_func = Mock()
        mock_func.side_effect = Exception("Persistent error")

        with pytest.raises(Exception, match="Persistent error"):
            limiter.execute_with_retry_sync(APIProvider.OPENAI, mock_func)

        assert mock_func.call_count == 3  # Initial + 2 retries

    def test_backoff_timing(self, retry_config):
        """Test backoff timing mechanism."""
        limiter = RateLimiter(retry_config)

        # Set backoff period
        future_time = time.time() + 0.1
        limiter.backoff_until[APIProvider.OPENAI] = future_time

        mock_func = Mock(return_value="success")

        start_time = time.time()
        result = limiter.execute_with_retry_sync(APIProvider.OPENAI, mock_func)
        end_time = time.time()

        # Should have waited for backoff period
        assert end_time - start_time >= 0.1
        assert result == "success"

    def test_queue_request_on_quota_exceeded(self, retry_config):
        """Test request queuing when quota is exceeded."""
        retry_config.max_retries = 1
        limiter = RateLimiter(retry_config)

        mock_func = Mock()
        mock_func.side_effect = Exception("Quota exceeded")

        with pytest.raises(Exception):
            limiter.execute_with_retry_sync(APIProvider.OPENAI, mock_func)

        # Should have queued the request
        assert limiter.request_queues[APIProvider.OPENAI].size() > 0

    def test_get_rate_limit_status(self, retry_config):
        """Test rate limit status retrieval."""
        limiter = RateLimiter(retry_config)

        # Set some rate limit info
        limiter.rate_limits[APIProvider.OPENAI].limit_requests = 5000
        limiter.rate_limits[APIProvider.OPENAI].remaining_requests = 4500

        # Add some request history
        current_time = time.time()
        limiter.request_history[APIProvider.OPENAI].extend(
            [
                current_time - 30,  # Within last minute
                current_time - 90,  # Outside last minute
            ]
        )

        status = limiter.get_rate_limit_status(APIProvider.OPENAI)

        assert status["provider"] == "openai"
        assert status["limit_requests"] == 5000
        assert status["remaining_requests"] == 4500
        assert status["requests_last_minute"] == 1  # Only one within last minute

    def test_process_queued_requests(self, retry_config):
        """Test processing queued requests."""
        limiter = RateLimiter(retry_config)

        # Add requests to queue
        queue = limiter.request_queues[APIProvider.OPENAI]
        mock_func = Mock(return_value="success")

        queue.add_request(
            {"func": mock_func, "args": ("arg1",), "kwargs": {"kwarg1": "value1"}}
        )
        queue.add_request({"func": mock_func, "args": ("arg2",), "kwargs": {}})

        processed = limiter.process_queued_requests(APIProvider.OPENAI, max_requests=5)

        assert processed == 2
        assert queue.size() == 0
        assert mock_func.call_count == 2

    def test_process_queued_requests_with_backoff(self, retry_config):
        """Test that queued requests are not processed during backoff."""
        limiter = RateLimiter(retry_config)

        # Set backoff period
        limiter.backoff_until[APIProvider.OPENAI] = time.time() + 60

        queue = limiter.request_queues[APIProvider.OPENAI]
        queue.add_request({"func": Mock(), "args": (), "kwargs": {}})

        processed = limiter.process_queued_requests(APIProvider.OPENAI)

        assert processed == 0
        assert queue.size() == 1  # Request still in queue


@pytest.mark.asyncio
class TestRateLimiterAsync:
    """Test async functionality of rate limiter."""

    async def test_execute_with_retry_async_success(self, retry_config):
        """Test successful async execution."""
        limiter = RateLimiter(retry_config)

        mock_func = Mock(return_value="async_success")

        result = await limiter.execute_with_retry(APIProvider.OPENAI, mock_func, "arg1")

        assert result == "async_success"

    async def test_execute_with_retry_async_with_retries(self, retry_config):
        """Test async execution with retries."""
        retry_config.base_delay = 0.01
        limiter = RateLimiter(retry_config)

        mock_func = Mock()
        mock_func.side_effect = [Exception("Network error"), "async_success"]

        result = await limiter.execute_with_retry(APIProvider.OPENAI, mock_func)

        assert result == "async_success"
        assert mock_func.call_count == 2


class TestRateLimitInfo:
    """Test RateLimitInfo dataclass."""

    def test_default_values(self):
        """Test default values."""
        info = RateLimitInfo()

        assert info.limit_requests is None
        assert info.remaining_requests is None
        assert info.retry_after is None

    def test_custom_values(self):
        """Test with custom values."""
        info = RateLimitInfo(
            limit_requests=1000, remaining_requests=800, retry_after=60.0
        )

        assert info.limit_requests == 1000
        assert info.remaining_requests == 800
        assert info.retry_after == 60.0


@pytest.mark.integration
class TestRateLimiterIntegration:
    """Integration tests for rate limiter."""

    def test_with_real_redis(self, integration_config):
        """Test with real Redis instance."""
        if not integration_config["use_real_apis"]:
            pytest.skip("Integration tests disabled")

        # This would test with actual Redis
        # limiter = RateLimiter()
        # ... test actual Redis functionality

        assert True  # Placeholder

    def test_concurrent_requests(self, retry_config):
        """Test handling concurrent requests."""
        import threading

        limiter = RateLimiter(retry_config)
        results = []
        errors = []

        def make_request(provider, func_id):
            try:
                mock_func = Mock(return_value=f"result_{func_id}")
                result = limiter.execute_with_retry_sync(provider, mock_func)
                results.append(result)
            except Exception as e:
                errors.append(e)

        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=make_request, args=(APIProvider.OPENAI, i))
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        assert len(results) == 5
        assert len(errors) == 0
