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
    
    missing_vars = [var for var, value in required_vars.items() if not value]
    
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    return True