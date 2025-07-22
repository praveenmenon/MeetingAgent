"""
Pytest configuration and shared fixtures
"""

import asyncio
import json
import os
import tempfile
from typing import Any, Dict, Generator
from unittest.mock import MagicMock, Mock

import pytest
import redis

from meeting_agent.ai_client import AIClient
from meeting_agent.ai_config import AIConfig, TaskType
from meeting_agent.config import ConfigManager, ApplicationConfig
from meeting_agent.memory_client import MemoryClient
from meeting_agent.notion_client import NotionClient
from meeting_agent.rate_limiter import RateLimiter, RetryConfig
from meeting_agent.task_manager import TaskManager
from meeting_agent.ui import UserInterface


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_config_dir():
    """Create a temporary directory for configuration files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Mock environment variables for testing."""
    test_env = {
        "NOTION_TOKEN": "test_notion_token",
        "DATABASE_ID": "test_database_id",
        "TASKS_DATABASE_ID": "test_tasks_database_id",
        "OPENAI_API_KEY": "test_openai_key",
        "ANTHROPIC_API_KEY": "test_anthropic_key",
        "DEFAULT_ASSIGNEE": "Test User",
        "MEM0_API_KEY": "test_mem0_key",
        "DEFAULT_USER_ID": "test_user_123",
        "REDIS_URL": "redis://localhost:6379",
    }

    for key, value in test_env.items():
        monkeypatch.setenv(key, value)

    return test_env


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing."""
    mock_client = Mock()
    mock_response = Mock()
    mock_response.choices = [Mock(message=Mock(content="Test response"))]
    mock_client.chat.completions.create.return_value = mock_response
    return mock_client


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client for testing."""
    mock_client = Mock()
    mock_response = Mock()
    mock_response.content = [Mock(text='["test_id_1", "test_id_2"]')]
    mock_client.messages.create.return_value = mock_response
    return mock_client


@pytest.fixture
def mock_redis_client():
    """Mock Redis client for testing."""
    mock_client = Mock(spec=redis.Redis)
    mock_client.ping.return_value = True
    mock_client.get.return_value = None
    mock_client.set.return_value = True
    mock_client.setex.return_value = True
    mock_client.lpush.return_value = 1
    mock_client.brpop.return_value = None
    return mock_client


@pytest.fixture
def sample_transcript():
    """Sample meeting transcript for testing."""
    return """
    Meeting Title: Weekly Team Sync
    Date: 2023-12-15
    Time: 10:00 AM - 10:30 AM
    Attendees: John (PM), Alice (Dev), Bob (QA)
    
    [10:00] John (PM): Good morning everyone. Let's start with updates.
    [10:01] Alice (Dev): I completed the user authentication feature. 
    [10:02] Bob (QA): I've tested the login flow, found one minor bug.
    [10:03] John (PM): Great work. Alice, can you fix that bug by Friday?
    [10:04] Alice (Dev): Yes, I'll have it done by then.
    [10:05] John (PM): Perfect. Meeting adjourned.
    """


@pytest.fixture
def sample_meeting_notes():
    """Sample meeting notes for testing."""
    return """
    # Meeting Notes: Weekly Team Sync - December 15, 2023

    ## Attendees
    - John (PM)
    - Alice (Dev) 
    - Bob (QA)

    ## Key Points
    - User authentication feature completed
    - One minor bug found in login flow
    - Bug fix scheduled for Friday

    ## Decisions
    - Alice to fix login bug by Friday

    ## Action Items
    - Alice: Fix login bug (Due: Friday)

    Meeting adjourned at 10:05 AM
    """


@pytest.fixture
def sample_tasks():
    """Sample tasks for testing."""
    return [
        {
            "title": "Fix login bug",
            "priority": "High",
            "suggested_due_date": "2023-12-22",
            "reason": "Critical bug affecting user experience",
        },
        {
            "title": "Update documentation",
            "priority": "Medium",
            "suggested_due_date": "2023-12-25",
            "reason": "Keep docs up to date with new feature",
        },
    ]


@pytest.fixture
def mock_notion_response():
    """Mock Notion API response."""
    return {
        "id": "test_page_id_123",
        "properties": {
            "Title": {"title": [{"text": {"content": "Test Meeting"}}]},
            "Description": {"rich_text": [{"text": {"content": "Test description"}}]},
            "Meeting Type": {"select": {"name": "Weekly Sync"}},
            "Status": {"select": {"name": "Completed"}},
        },
    }


@pytest.fixture
def ai_config():
    """AI configuration instance for testing."""
    config = AIConfig()
    # Override with test-friendly values
    config.task_configs[TaskType.SUMMARIZATION].temperature = 0.1
    config.task_configs[TaskType.SUMMARIZATION].max_tokens = 100
    return config


@pytest.fixture
def retry_config():
    """Retry configuration for testing."""
    return RetryConfig(
        max_retries=2,
        base_delay=0.1,
        max_delay=1.0,
        rate_limit_delay=0.5,
        quota_exceeded_delay=1.0,
        jitter=False,  # Disable for predictable testing
    )


@pytest.fixture
def mock_ai_client(mock_openai_client, mock_anthropic_client, ai_config):
    """Mock AI client with all dependencies."""
    with pytest.mock.patch("meeting_agent.ai_client.OPENAI_CLIENT", mock_openai_client):
        with pytest.mock.patch(
            "meeting_agent.ai_client.ANTHROPIC_CLIENT", mock_anthropic_client
        ):
            with pytest.mock.patch(
                "meeting_agent.ai_client.get_ai_config", return_value=ai_config
            ):
                client = AIClient()
                return client


@pytest.fixture
def mock_notion_client(mock_notion_response):
    """Mock Notion client."""
    mock_client = Mock(spec=NotionClient)
    mock_client.create_meeting_page.return_value = "test_page_id"
    mock_client.append_notes_to_page.return_value = True
    mock_client.update_meeting_fields.return_value = True
    mock_client.get_select_options.return_value = ["Option 1", "Option 2"]
    mock_client.query_past_meetings.return_value = [mock_notion_response]
    mock_client.get_meeting_details.return_value = mock_notion_response
    mock_client.get_full_notes.return_value = "Sample meeting notes"
    return mock_client


@pytest.fixture
def mock_memory_client():
    """Mock memory client."""
    mock_client = Mock(spec=MemoryClient)
    mock_client.is_enabled.return_value = True
    mock_client.store_meeting_memory.return_value = True
    mock_client.get_relevant_context.return_value = []
    mock_client.get_memory_stats.return_value = {
        "total_memories": 10,
        "categories": {"meetings": 8, "tasks": 2},
    }
    return mock_client


@pytest.fixture
def mock_ui():
    """Mock user interface."""
    mock_ui = Mock(spec=UserInterface)
    mock_ui.get_user_input.return_value = "test input"
    mock_ui.prompt_for_select.return_value = "Test Selection"
    mock_ui.ask_to_add_tasks.return_value = True
    mock_ui.get_task_selection.return_value = ["action_items"]
    return mock_ui


@pytest.fixture
def mock_task_manager(mock_notion_client, mock_ai_client, mock_ui, mock_memory_client):
    """Mock task manager with all dependencies."""
    return TaskManager(mock_notion_client, mock_ai_client, mock_ui, mock_memory_client)


@pytest.fixture
def rate_limiter(retry_config):
    """Rate limiter instance for testing."""
    return RateLimiter(retry_config)


# Integration test fixtures
@pytest.fixture
def integration_config():
    """Configuration for integration tests."""
    return {
        "use_real_apis": os.getenv("INTEGRATION_TESTS", "false").lower() == "true",
        "redis_url": os.getenv("TEST_REDIS_URL", "redis://localhost:6379"),
        "test_timeout": 30,
    }


@pytest.fixture
def sample_chunks():
    """Sample transcript chunks for testing."""
    return [
        {
            "id": 1,
            "text": "[10:00] John (PM): Good morning everyone. Let's start with updates.",
            "size": 67,
            "speaker_count": 1,
        },
        {
            "id": 2,
            "text": "[10:01] Alice (Dev): I completed the user authentication feature.",
            "size": 62,
            "speaker_count": 1,
        },
        {
            "id": 3,
            "text": "[10:02] Bob (QA): I've tested the login flow, found one minor bug.",
            "size": 64,
            "speaker_count": 1,
        },
    ]


# Markers for test categorization
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")
    config.addinivalue_line("markers", "api: marks tests that make real API calls")


# Pytest collection hooks
def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically."""
    for item in items:
        # Add unit marker to all tests by default
        if not any(
            mark.name in ["integration", "api", "slow"] for mark in item.iter_markers()
        ):
            item.add_marker(pytest.mark.unit)

        # Add slow marker to tests with 'slow' in name
        if "slow" in item.name or "integration" in str(item.fspath):
            item.add_marker(pytest.mark.slow)


# Test data generators
def generate_test_transcript(num_speakers: int = 3, num_exchanges: int = 5) -> str:
    """Generate a test transcript with specified parameters."""
    speakers = [f"Speaker{i}" for i in range(1, num_speakers + 1)]
    transcript_lines = [
        "Meeting Title: Generated Test Meeting",
        "Date: 2023-12-15",
        f"Attendees: {', '.join(speakers)}",
    ]

    for i in range(num_exchanges):
        speaker = speakers[i % len(speakers)]
        timestamp = f"[10:{i:02d}]"
        message = f"This is message {i+1} from {speaker}"
        transcript_lines.append(f"{timestamp} {speaker}: {message}")

    return "\n".join(transcript_lines)


# Cleanup fixtures
@pytest.fixture(autouse=True)
def cleanup_temp_files():
    """Cleanup temporary files after each test."""
    yield
    # Cleanup logic here if needed
    pass
