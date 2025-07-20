"""
Configuration management for Meeting Agent
"""

import os
from dotenv import load_dotenv
from openai import OpenAI
from anthropic import Anthropic

# Load environment variables
load_dotenv()

# Notion Configuration
NOTION_TOKEN = os.getenv('NOTION_TOKEN')
DATABASE_ID = os.getenv('DATABASE_ID')
TASKS_DATABASE_ID = os.getenv('TASKS_DATABASE_ID')
DEFAULT_ASSIGNEE = os.getenv('DEFAULT_ASSIGNEE', 'Me')

# API Clients
OPENAI_CLIENT = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
ANTHROPIC_CLIENT = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

# Memory Configuration
MEM0_API_KEY = os.getenv('MEM0_API_KEY')
DEFAULT_USER_ID = os.getenv('DEFAULT_USER_ID', 'default_user')
MEMORY_ENABLED = os.getenv('MEMORY_ENABLED', 'true').lower() == 'true'

# Notion API Headers
NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

def validate_config():
    """Validate that all required configuration is present"""
    required_vars = {
        'NOTION_TOKEN': NOTION_TOKEN,
        'DATABASE_ID': DATABASE_ID,
        'TASKS_DATABASE_ID': TASKS_DATABASE_ID,
        'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY'),
        'ANTHROPIC_API_KEY': os.getenv('ANTHROPIC_API_KEY')
    }
    
    # Optional memory configuration
    optional_vars = {
        'MEM0_API_KEY': MEM0_API_KEY
    }
    
    missing_vars = [var for var, value in required_vars.items() if not value]
    
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    # Warn about optional variables
    missing_optional = [var for var, value in optional_vars.items() if not value]
    if missing_optional:
        print(f"Warning: Optional environment variables not set: {', '.join(missing_optional)}")
        print("Memory features will be disabled without MEM0_API_KEY")
    
    return True