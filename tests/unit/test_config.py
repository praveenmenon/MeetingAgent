"""
Tests for configuration module
"""

import pytest
import os
from unittest.mock import patch, Mock
from meeting_agent.config import ConfigManager, ApplicationConfig


class TestConfigManager:
    """Test configuration management functionality"""
    
    def test_config_manager_initialization(self):
        """Test ConfigManager can initialize"""
        assert ConfigManager is not None
    
    @patch.dict(os.environ, {
        'NOTION_TOKEN': 'secret_test_token',
        'DATABASE_ID': 'test_db_id', 
        'TASKS_DATABASE_ID': 'test_tasks_db_id',
        'OPENAI_API_KEY': 'sk-test_key',
        'ANTHROPIC_API_KEY': 'test_anthropic_key'
    })
    def test_load_config_from_environment(self):
        """Test loading configuration from environment variables"""
        config = ConfigManager.load_config()
        assert config is not None
        assert isinstance(config, ApplicationConfig)
        assert config.notion.token == 'secret_test_token'
        assert config.notion.database_id == 'test_db_id'
    
    def test_config_validation_with_invalid_token(self):
        """Test config validation fails with invalid token format"""
        with patch.dict(os.environ, {
            'NOTION_TOKEN': 'invalid_token',  # Should start with secret_ or ntn_
            'DATABASE_ID': 'test_db_id',
            'TASKS_DATABASE_ID': 'test_tasks_db_id', 
            'OPENAI_API_KEY': 'sk-test_key',
            'ANTHROPIC_API_KEY': 'test_anthropic_key'
        }):
            with pytest.raises(Exception):
                ConfigManager.load_config()
    
    def test_config_singleton_behavior(self):
        """Test that ConfigManager returns same instance"""
        with patch.dict(os.environ, {
            'NOTION_TOKEN': 'secret_test_token',
            'DATABASE_ID': 'test_db_id',
            'TASKS_DATABASE_ID': 'test_tasks_db_id',
            'OPENAI_API_KEY': 'sk-test_key', 
            'ANTHROPIC_API_KEY': 'test_anthropic_key'
        }):
            config1 = ConfigManager.get_config()
            config2 = ConfigManager.get_config()
            assert config1 is config2


class TestApplicationConfig:
    """Test ApplicationConfig model"""
    
    def test_environment_validation(self):
        """Test environment validation"""
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'production',
            'NOTION_TOKEN': 'secret_test_token',
            'DATABASE_ID': 'test_db_id',
            'TASKS_DATABASE_ID': 'test_tasks_db_id',
            'OPENAI_API_KEY': 'sk-test_key',
            'ANTHROPIC_API_KEY': 'test_anthropic_key'
        }):
            config = ConfigManager.load_config()
            assert config.environment == 'production'
            assert config.is_production() is True
            assert config.is_development() is False
    
    def test_default_values(self):
        """Test default configuration values"""
        with patch.dict(os.environ, {
            'NOTION_TOKEN': 'secret_test_token',
            'DATABASE_ID': 'test_db_id',
            'TASKS_DATABASE_ID': 'test_tasks_db_id',
            'OPENAI_API_KEY': 'sk-test_key',
            'ANTHROPIC_API_KEY': 'test_anthropic_key'
        }):
            config = ConfigManager.load_config()
            assert config.app_name == "Meeting Agent"
            assert config.version == "1.0.0"
            assert config.environment == "development"