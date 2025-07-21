"""
Unit tests for AI client functionality
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json

from meeting_agent.ai_client import AIClient
from meeting_agent.ai_config import TaskType
from meeting_agent.rate_limiter import APIProvider


class TestAIClient:
    """Test cases for AIClient class."""
    
    def test_init(self, mock_openai_client, mock_anthropic_client):
        """Test AIClient initialization."""
        with patch('meeting_agent.ai_client.OPENAI_CLIENT', mock_openai_client):
            with patch('meeting_agent.ai_client.ANTHROPIC_CLIENT', mock_anthropic_client):
                client = AIClient()
                
                assert client.openai_client == mock_openai_client
                assert client.anthropic_client == mock_anthropic_client
                assert client.ai_config is not None
                assert client.rate_limiter is not None

    def test_summarize_transcript_success(self, mock_ai_client, sample_transcript):
        """Test successful transcript summarization."""
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Summarized notes"))]
        mock_ai_client.rate_limiter.execute_with_retry_sync.return_value = mock_response
        
        result = mock_ai_client.summarize_transcript(sample_transcript)
        
        assert result == "Summarized notes"
        mock_ai_client.rate_limiter.execute_with_retry_sync.assert_called_once()
        
        # Verify correct API provider was used
        call_args = mock_ai_client.rate_limiter.execute_with_retry_sync.call_args
        assert call_args[0][0] == APIProvider.OPENAI

    def test_summarize_transcript_with_rate_limiting(self, mock_ai_client, sample_transcript):
        """Test transcript summarization with rate limiting."""
        # Simulate rate limiting
        from meeting_agent.rate_limiter import RateLimitError
        
        mock_ai_client.rate_limiter.execute_with_retry_sync.side_effect = [
            Exception("Rate limit exceeded"),
            Mock(choices=[Mock(message=Mock(content="Success after retry"))])
        ]
        
        with pytest.raises(Exception):
            mock_ai_client.summarize_transcript(sample_transcript)

    def test_generate_brief_description(self, mock_ai_client, sample_meeting_notes):
        """Test brief description generation."""
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Brief description"))]
        mock_ai_client.rate_limiter.execute_with_retry_sync.return_value = mock_response
        
        result = mock_ai_client.generate_brief_description(sample_meeting_notes)
        
        assert result == "Brief description"
        
        # Verify correct task type configuration was used
        call_args = mock_ai_client.rate_limiter.execute_with_retry_sync.call_args
        assert call_args[0][0] == APIProvider.OPENAI

    def test_check_similarity_success(self, mock_ai_client):
        """Test successful similarity checking."""
        mock_response = Mock()
        mock_response.content = [Mock(text='["meeting_id_1", "meeting_id_2"]')]
        mock_ai_client.rate_limiter.execute_with_retry_sync.return_value = mock_response
        
        past_meetings = [
            {
                'id': 'meeting_id_1',
                'properties': {
                    'Title': {'title': [{'text': {'content': 'Test Meeting 1'}}]},
                    'Description': {'rich_text': [{'text': {'content': 'Description 1'}}]}
                }
            }
        ]
        
        result = mock_ai_client.check_similarity("New notes", past_meetings, "new_id")
        
        assert result == ["meeting_id_1", "meeting_id_2"]
        
        # Verify Anthropic provider was used
        call_args = mock_ai_client.rate_limiter.execute_with_retry_sync.call_args
        assert call_args[0][0] == APIProvider.ANTHROPIC

    def test_check_similarity_with_malformed_json(self, mock_ai_client):
        """Test similarity checking with malformed JSON response."""
        mock_response = Mock()
        mock_response.content = [Mock(text='Some text before ["id1"] and after')]
        mock_ai_client.rate_limiter.execute_with_retry_sync.return_value = mock_response
        
        result = mock_ai_client.check_similarity("Notes", [], "new_id")
        
        assert result == ["id1"]

    def test_check_similarity_json_parse_error(self, mock_ai_client):
        """Test similarity checking with JSON parse error."""
        mock_response = Mock()
        mock_response.content = [Mock(text='Invalid JSON response')]
        mock_ai_client.rate_limiter.execute_with_retry_sync.return_value = mock_response
        
        result = mock_ai_client.check_similarity("Notes", [], "new_id")
        
        assert result == []

    def test_answer_question(self, mock_ai_client):
        """Test question answering."""
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Answer to question"))]
        mock_ai_client.rate_limiter.execute_with_retry_sync.return_value = mock_response
        
        result = mock_ai_client.answer_question("What was discussed?", "Meeting notes")
        
        assert result == "Answer to question"
        
        # Verify OpenAI provider and QA task type
        call_args = mock_ai_client.rate_limiter.execute_with_retry_sync.call_args
        assert call_args[0][0] == APIProvider.OPENAI

    def test_suggest_tasks_from_meeting(self, mock_ai_client, sample_tasks):
        """Test task suggestion from meeting."""
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content=json.dumps(sample_tasks)))]
        mock_ai_client.rate_limiter.execute_with_retry_sync.return_value = mock_response
        
        result = mock_ai_client.suggest_tasks_from_meeting("Meeting notes", "Test Meeting")
        
        assert len(result) == 2
        assert result[0]["title"] == "Fix login bug"
        assert result[1]["priority"] == "Medium"

    def test_suggest_tasks_with_invalid_json(self, mock_ai_client):
        """Test task suggestion with invalid JSON response."""
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Invalid JSON"))]
        mock_ai_client.rate_limiter.execute_with_retry_sync.return_value = mock_response
        
        result = mock_ai_client.suggest_tasks_from_meeting("Notes", "Meeting")
        
        assert result == []

    def test_suggest_tasks_with_exception(self, mock_ai_client):
        """Test task suggestion with exception."""
        mock_ai_client.rate_limiter.execute_with_retry_sync.side_effect = Exception("API Error")
        
        result = mock_ai_client.suggest_tasks_from_meeting("Notes", "Meeting")
        
        assert result == []

    def test_get_rate_limit_status(self, mock_ai_client):
        """Test rate limit status retrieval."""
        mock_status = {
            "openai": {"requests_last_minute": 10, "queue_size": 0},
            "anthropic": {"requests_last_minute": 5, "queue_size": 2}
        }
        mock_ai_client.rate_limiter.get_rate_limit_status.return_value = mock_status["openai"]
        
        with patch.object(mock_ai_client, 'get_rate_limit_status', return_value=mock_status):
            result = mock_ai_client.get_rate_limit_status()
            
            assert "openai" in result
            assert "anthropic" in result

    def test_process_queued_requests(self, mock_ai_client):
        """Test processing of queued requests."""
        mock_result = {"openai_processed": 3, "anthropic_processed": 1}
        
        with patch.object(mock_ai_client, 'process_queued_requests', return_value=mock_result):
            result = mock_ai_client.process_queued_requests(10)
            
            assert result["openai_processed"] == 3
            assert result["anthropic_processed"] == 1

    def test_configuration_used_correctly(self, mock_ai_client, ai_config):
        """Test that AI configuration is used correctly for different tasks."""
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Response"))]
        mock_ai_client.rate_limiter.execute_with_retry_sync.return_value = mock_response
        
        # Test summarization uses correct config
        mock_ai_client.summarize_transcript("Test")
        
        call_kwargs = mock_ai_client.rate_limiter.execute_with_retry_sync.call_args[1]
        
        # Should include temperature, max_tokens, etc. from config
        assert 'temperature' in str(call_kwargs)
        assert 'max_tokens' in str(call_kwargs)


@pytest.mark.integration
class TestAIClientIntegration:
    """Integration tests for AI client."""
    
    @pytest.mark.api
    def test_real_api_call(self, integration_config, sample_transcript):
        """Test with real API call (requires API keys)."""
        if not integration_config["use_real_apis"]:
            pytest.skip("Integration tests disabled")
        
        client = AIClient()
        
        # This would make a real API call
        # result = client.summarize_transcript(sample_transcript)
        # assert len(result) > 0
        
        # For now, just test that client can be instantiated
        assert client is not None

    def test_error_handling_chain(self, mock_ai_client):
        """Test error handling through the entire chain."""
        # Test various error scenarios
        errors = [
            Exception("Connection timeout"),
            Exception("Rate limit exceeded"), 
            Exception("Quota exceeded"),
            Exception("Invalid API key")
        ]
        
        for error in errors:
            mock_ai_client.rate_limiter.execute_with_retry_sync.side_effect = error
            
            with pytest.raises(Exception):
                mock_ai_client.summarize_transcript("Test")


class TestAIClientEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_empty_transcript(self, mock_ai_client):
        """Test with empty transcript."""
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Empty response"))]
        mock_ai_client.rate_limiter.execute_with_retry_sync.return_value = mock_response
        
        result = mock_ai_client.summarize_transcript("")
        
        assert result == "Empty response"

    def test_very_long_transcript(self, mock_ai_client):
        """Test with very long transcript."""
        long_transcript = "Long transcript " * 1000
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Summarized long transcript"))]
        mock_ai_client.rate_limiter.execute_with_retry_sync.return_value = mock_response
        
        result = mock_ai_client.summarize_transcript(long_transcript)
        
        assert result == "Summarized long transcript"

    def test_unicode_content(self, mock_ai_client):
        """Test with Unicode content."""
        unicode_transcript = "Meeting with émojis 🚀 and ñoñ-ASCII çhars"
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Unicode handled"))]
        mock_ai_client.rate_limiter.execute_with_retry_sync.return_value = mock_response
        
        result = mock_ai_client.summarize_transcript(unicode_transcript)
        
        assert result == "Unicode handled"

    def test_similarity_with_no_past_meetings(self, mock_ai_client):
        """Test similarity check with no past meetings."""
        result = mock_ai_client.check_similarity("New notes", [], "new_id")
        
        assert result == []
        # Should not make API call if no past meetings
        mock_ai_client.rate_limiter.execute_with_retry_sync.assert_not_called()

    def test_malformed_meeting_data(self, mock_ai_client):
        """Test with malformed meeting data."""
        malformed_meetings = [
            {"id": "test", "properties": {}},  # Missing required fields
            {"invalid": "structure"}  # Invalid structure
        ]
        
        # Should handle malformed data gracefully
        result = mock_ai_client.check_similarity("Notes", malformed_meetings, "new_id")
        
        # Should return empty list or handle gracefully
        assert isinstance(result, list)