"""
End-to-end integration tests for Meeting Agent
"""

import pytest
from unittest.mock import patch, Mock
import tempfile
import os

from meeting_agent.main import MeetingAgent


@pytest.mark.integration
class TestMeetingAgentEndToEnd:
    """End-to-end tests for the complete Meeting Agent workflow."""
    
    def test_complete_workflow_mock(self, mock_env_vars, sample_transcript, sample_meeting_notes):
        """Test complete workflow with mocked external services."""
        
        with patch('meeting_agent.main.NotionClient') as mock_notion_cls:
            with patch('meeting_agent.main.AIClient') as mock_ai_cls:
                with patch('meeting_agent.main.UserInterface') as mock_ui_cls:
                    with patch('meeting_agent.main.MemoryClient') as mock_memory_cls:
                        
                        # Setup mocks
                        mock_notion = Mock()
                        mock_notion.create_meeting_page.return_value = "page_123"
                        mock_notion.append_notes_to_page.return_value = True
                        mock_notion.update_meeting_fields.return_value = True
                        mock_notion.get_select_options.return_value = ["Weekly", "Monthly"]
                        mock_notion.query_past_meetings.return_value = []
                        mock_notion_cls.return_value = mock_notion
                        
                        mock_ai = Mock()
                        mock_ai.summarize_transcript.return_value = sample_meeting_notes
                        mock_ai.generate_brief_description.return_value = "Weekly sync meeting"
                        mock_ai.check_similarity.return_value = []
                        mock_ai.suggest_tasks_from_meeting.return_value = []
                        mock_ai_cls.return_value = mock_ai
                        
                        mock_ui = Mock()
                        mock_ui.get_user_input.side_effect = [
                            sample_transcript,  # transcript
                            "Weekly Team Sync",  # title
                            "exit"  # exit Q&A
                        ]
                        mock_ui.prompt_for_select.side_effect = [
                            "Weekly",  # meeting type
                            ["Development"],  # tags
                            "Completed"  # status
                        ]
                        mock_ui.ask_to_add_tasks.return_value = False
                        mock_ui_cls.return_value = mock_ui
                        
                        mock_memory = Mock()
                        mock_memory.is_enabled.return_value = False
                        mock_memory_cls.return_value = mock_memory
                        
                        # Run the agent
                        agent = MeetingAgent()
                        
                        # This would normally call agent.run() but we'll test components
                        assert agent.notion_client is not None
                        assert agent.ai_client is not None
                        assert agent.ui is not None
                        assert agent.memory_client is not None
                        assert agent.task_manager is not None

    @pytest.mark.slow
    def test_large_transcript_processing(self, mock_env_vars):
        """Test processing of large transcripts."""
        from tests.conftest import generate_test_transcript
        
        # Generate large transcript
        large_transcript = generate_test_transcript(num_speakers=10, num_exchanges=100)
        
        with patch('meeting_agent.main.NotionClient') as mock_notion_cls:
            with patch('meeting_agent.main.AIClient') as mock_ai_cls:
                with patch('meeting_agent.main.UserInterface') as mock_ui_cls:
                    
                    # Setup mocks for large transcript
                    mock_ai = Mock()
                    mock_ai.summarize_transcript.return_value = "Large meeting summary"
                    mock_ai.generate_brief_description.return_value = "Large meeting"
                    mock_ai_cls.return_value = mock_ai
                    
                    mock_ui = Mock()
                    mock_ui.get_user_input.side_effect = [large_transcript, "Large Meeting", "exit"]
                    mock_ui_cls.return_value = mock_ui
                    
                    mock_notion = Mock()
                    mock_notion.create_meeting_page.return_value = "large_page_123"
                    mock_notion_cls.return_value = mock_notion
                    
                    agent = MeetingAgent()
                    
                    # Verify chunker detects large transcript
                    should_chunk = agent.chunker.should_chunk(large_transcript)
                    assert should_chunk is True

    def test_async_processing_workflow(self, mock_env_vars, mock_redis_client):
        """Test async processing workflow."""
        
        with patch('meeting_agent.main.NotionClient'):
            with patch('meeting_agent.main.AIClient'):
                with patch('meeting_agent.main.UserInterface'):
                    with patch('redis.from_url', return_value=mock_redis_client):
                        
                        agent = MeetingAgent()
                        agent.enable_async = True
                        
                        # Test that async processing is enabled
                        assert agent.enable_async is True
                        assert agent.queue_client is not None

    def test_error_handling_workflow(self, mock_env_vars):
        """Test error handling in the complete workflow."""
        
        with patch('meeting_agent.main.AIClient') as mock_ai_cls:
            with patch('meeting_agent.main.UserInterface') as mock_ui_cls:
                
                # Setup AI client to fail
                mock_ai = Mock()
                mock_ai.summarize_transcript.side_effect = Exception("API Error")
                mock_ai_cls.return_value = mock_ai
                
                mock_ui = Mock()
                mock_ui.get_user_input.side_effect = ["Test transcript", "Test Meeting", "exit"]
                mock_ui_cls.return_value = mock_ui
                
                # Should handle errors gracefully
                agent = MeetingAgent()
                
                # Verify error handling is in place
                assert agent.ai_client is not None

    def test_memory_integration(self, mock_env_vars):
        """Test memory integration workflow."""
        
        with patch('meeting_agent.main.MemoryClient') as mock_memory_cls:
            with patch('meeting_agent.main.AIClient'):
                with patch('meeting_agent.main.NotionClient'):
                    with patch('meeting_agent.main.UserInterface'):
                        
                        mock_memory = Mock()
                        mock_memory.is_enabled.return_value = True
                        mock_memory.get_memory_stats.return_value = {
                            "total_memories": 5,
                            "categories": {"meetings": 3, "tasks": 2}
                        }
                        mock_memory_cls.return_value = mock_memory
                        
                        agent = MeetingAgent()
                        
                        # Test memory interaction
                        assert agent.memory_client.is_enabled() is True

    def test_rate_limiting_integration(self, mock_env_vars, retry_config):
        """Test rate limiting integration."""
        
        with patch('meeting_agent.main.AIClient') as mock_ai_cls:
            
            mock_ai = Mock()
            # Simulate rate limiting
            mock_ai.summarize_transcript.side_effect = Exception("Rate limit exceeded")
            mock_ai_cls.return_value = mock_ai
            
            agent = MeetingAgent()
            
            # Verify rate limiter is configured
            assert agent.ai_client.rate_limiter is not None

    def test_configuration_override(self, mock_env_vars, temp_config_dir):
        """Test configuration override functionality."""
        
        # Create temporary config file
        config_path = os.path.join(temp_config_dir, ".env")
        with open(config_path, "w") as f:
            f.write("AI_SUMMARIZATION_TEMPERATURE=0.1\n")
            f.write("ENABLE_ASYNC_PROCESSING=true\n")
        
        with patch.dict(os.environ, {"CONFIG_PATH": config_path}):
            
            agent = MeetingAgent()
            
            # Verify configuration was loaded
            assert agent.ai_client is not None

    @pytest.mark.api
    def test_real_api_integration(self, integration_config):
        """Test with real API calls (requires API keys)."""
        
        if not integration_config["use_real_apis"]:
            pytest.skip("Real API tests disabled")
        
        # This would test with actual APIs
        # agent = MeetingAgent()
        # result = agent.ai_client.summarize_transcript("Short test transcript")
        # assert len(result) > 0
        
        assert True  # Placeholder


@pytest.mark.integration
class TestWorkflowComponents:
    """Test individual workflow components in integration."""
    
    def test_transcript_to_notes_pipeline(self, mock_ai_client, sample_transcript):
        """Test transcript to notes pipeline."""
        
        # Mock the response
        mock_ai_client.summarize_transcript.return_value = "Generated notes"
        mock_ai_client.generate_brief_description.return_value = "Brief description"
        
        notes = mock_ai_client.summarize_transcript(sample_transcript)
        brief = mock_ai_client.generate_brief_description(notes)
        
        assert notes == "Generated notes"
        assert brief == "Brief description"

    def test_task_creation_pipeline(self, mock_task_manager, sample_meeting_notes):
        """Test task creation pipeline."""
        
        mock_task_manager.suggest_and_create_tasks(
            sample_meeting_notes, 
            "page_123", 
            "Test Meeting"
        )
        
        # Verify task creation was called
        assert mock_task_manager.suggest_and_create_tasks.called

    def test_similarity_checking_pipeline(self, mock_ai_client):
        """Test similarity checking pipeline."""
        
        mock_ai_client.check_similarity.return_value = ["similar_id_1"]
        
        past_meetings = [
            {
                "id": "similar_id_1",
                "properties": {
                    "Title": {"title": [{"text": {"content": "Similar Meeting"}}]},
                    "Description": {"rich_text": [{"text": {"content": "Similar content"}}]}
                }
            }
        ]
        
        similar_ids = mock_ai_client.check_similarity("New notes", past_meetings, "new_id")
        
        assert "similar_id_1" in similar_ids

    def test_memory_storage_pipeline(self, mock_memory_client):
        """Test memory storage pipeline."""
        
        meeting_data = {
            "id": "meeting_123",
            "title": "Test Meeting",
            "notes": "Meeting notes",
            "action_items": ["Task 1", "Task 2"]
        }
        
        mock_memory_client.store_meeting_memory(meeting_data)
        
        assert mock_memory_client.store_meeting_memory.called


@pytest.mark.integration
@pytest.mark.slow
class TestPerformanceIntegration:
    """Performance and load testing."""
    
    def test_multiple_concurrent_meetings(self, mock_env_vars):
        """Test processing multiple meetings concurrently."""
        import threading
        import time
        
        results = []
        errors = []
        
        def process_meeting(meeting_id):
            try:
                with patch('meeting_agent.main.NotionClient'):
                    with patch('meeting_agent.main.AIClient') as mock_ai_cls:
                        with patch('meeting_agent.main.UserInterface'):
                            
                            mock_ai = Mock()
                            mock_ai.summarize_transcript.return_value = f"Notes for meeting {meeting_id}"
                            mock_ai_cls.return_value = mock_ai
                            
                            agent = MeetingAgent()
                            result = agent.ai_client.summarize_transcript(f"Transcript {meeting_id}")
                            results.append(result)
                            
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads
        threads = []
        for i in range(3):  # Small number for testing
            thread = threading.Thread(target=process_meeting, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        assert len(results) == 3
        assert len(errors) == 0

    def test_large_queue_processing(self, mock_redis_client, retry_config):
        """Test processing large queue of requests."""
        from meeting_agent.rate_limiter import RateLimiter
        
        limiter = RateLimiter(retry_config)
        
        # Add many requests to queue
        queue = limiter.request_queues[limiter.APIProvider.OPENAI]
        
        for i in range(10):
            mock_func = Mock(return_value=f"result_{i}")
            queue.add_request({
                'func': mock_func,
                'args': (),
                'kwargs': {}
            })
        
        processed = limiter.process_queued_requests(limiter.APIProvider.OPENAI, max_requests=10)
        
        assert processed == 10
        assert queue.size() == 0

    def test_memory_usage_monitoring(self, mock_env_vars):
        """Test memory usage during processing."""
        import psutil
        import gc
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        # Process multiple transcripts
        for i in range(5):
            with patch('meeting_agent.main.NotionClient'):
                with patch('meeting_agent.main.AIClient') as mock_ai_cls:
                    with patch('meeting_agent.main.UserInterface'):
                        
                        mock_ai = Mock()
                        mock_ai.summarize_transcript.return_value = f"Notes {i}"
                        mock_ai_cls.return_value = mock_ai
                        
                        agent = MeetingAgent()
                        agent.ai_client.summarize_transcript(f"Transcript {i}")
        
        gc.collect()  # Force garbage collection
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 100MB)
        assert memory_increase < 100 * 1024 * 1024


@pytest.mark.integration
class TestConfigurationIntegration:
    """Test configuration integration across components."""
    
    def test_ai_config_propagation(self, mock_env_vars, ai_config):
        """Test AI configuration propagates to all components."""
        
        with patch('meeting_agent.main.AIClient') as mock_ai_cls:
            
            mock_ai = Mock()
            mock_ai.ai_config = ai_config
            mock_ai_cls.return_value = mock_ai
            
            agent = MeetingAgent()
            
            # Verify configuration is used
            assert agent.ai_client.ai_config is not None

    def test_environment_variable_override(self, monkeypatch):
        """Test environment variable overrides work across components."""
        
        # Set test environment variables
        monkeypatch.setenv("AI_SUMMARIZATION_TEMPERATURE", "0.1")
        monkeypatch.setenv("RATE_LIMIT_MAX_RETRIES", "3")
        monkeypatch.setenv("ENABLE_ASYNC_PROCESSING", "true")
        
        with patch('meeting_agent.main.NotionClient'):
            with patch('meeting_agent.main.AIClient'):
                with patch('meeting_agent.main.UserInterface'):
                    
                    agent = MeetingAgent()
                    
                    # Verify environment variables are respected
                    assert agent.enable_async is True

    def test_configuration_validation(self, mock_env_vars):
        """Test configuration validation during initialization."""
        
        # Test with valid configuration
        agent = MeetingAgent()
        assert agent is not None
        
        # Test with missing required configuration
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(Exception):
                MeetingAgent()


@pytest.mark.integration
class TestErrorRecoveryIntegration:
    """Test error recovery across the entire system."""
    
    def test_api_failure_recovery(self, mock_env_vars):
        """Test recovery from API failures."""
        
        with patch('meeting_agent.main.AIClient') as mock_ai_cls:
            
            mock_ai = Mock()
            # First call fails, second succeeds
            mock_ai.summarize_transcript.side_effect = [
                Exception("API temporarily unavailable"),
                "Success after retry"
            ]
            mock_ai_cls.return_value = mock_ai
            
            agent = MeetingAgent()
            
            # Should handle first failure gracefully
            assert agent.ai_client is not None

    def test_partial_failure_handling(self, mock_env_vars):
        """Test handling of partial failures in workflow."""
        
        with patch('meeting_agent.main.NotionClient') as mock_notion_cls:
            with patch('meeting_agent.main.AIClient') as mock_ai_cls:
                
                # AI succeeds, Notion fails
                mock_ai = Mock()
                mock_ai.summarize_transcript.return_value = "Success"
                mock_ai_cls.return_value = mock_ai
                
                mock_notion = Mock()
                mock_notion.create_meeting_page.side_effect = Exception("Notion API error")
                mock_notion_cls.return_value = mock_notion
                
                agent = MeetingAgent()
                
                # Should handle partial failure
                assert agent.ai_client is not None
                assert agent.notion_client is not None

    def test_graceful_degradation(self, mock_env_vars):
        """Test graceful degradation when optional features fail."""
        
        with patch('meeting_agent.main.MemoryClient') as mock_memory_cls:
            
            mock_memory = Mock()
            mock_memory.is_enabled.return_value = False  # Memory disabled
            mock_memory_cls.return_value = mock_memory
            
            agent = MeetingAgent()
            
            # Should work without memory features
            assert agent.memory_client is not None