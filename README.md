# Meeting Agent

[![CI/CD Pipeline](https://github.com/yourusername/meeting-agent/workflows/CI%2FCD%20Pipeline/badge.svg)](https://github.com/yourusername/meeting-agent/actions)
[![Coverage](https://codecov.io/gh/yourusername/meeting-agent/branch/main/graph/badge.svg)](https://codecov.io/gh/yourusername/meeting-agent)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A production-ready, AI-powered meeting transcription and task management system that transforms meeting notes into actionable insights using OpenAI and Anthropic APIs, with intelligent Notion integration.

## 🚀 Features

### Core Functionality
- **AI-Powered Transcription**: Transform raw meeting transcripts into structured, professional notes
- **Smart Task Generation**: Automatically extract and create action items from meeting discussions
- **Notion Integration**: Seamlessly sync with your existing Notion workspace
- **Memory System**: Learn from previous meetings for better context and suggestions
- **Similarity Detection**: Find related meetings and group discussions automatically

### Advanced Capabilities
- **Async Processing**: Handle large transcripts with background workers
- **Rate Limiting**: Intelligent API quota management with exponential backoff
- **Chunking Algorithm**: Process meetings of any size with speaker-aware segmentation
- **Multi-Model Support**: Leverage both OpenAI and Anthropic models for optimal results
- **Real-time Monitoring**: Track API usage, queue status, and system health

### Production Features
- **Docker Support**: Containerized deployment with Redis backing
- **Configuration Management**: Environment-based configuration with validation
- **Comprehensive Logging**: Structured logging with multiple output formats
- **Error Recovery**: Graceful handling of API failures and network issues
- **Test Coverage**: Extensive unit and integration test suite

## 📦 Installation

### Quick Start with Docker
```bash
# Clone the repository
git clone https://github.com/yourusername/meeting-agent.git
cd meeting-agent

# Copy and configure environment
cp config/.env.example config/.env
# Edit config/.env with your API keys

# Run with Docker Compose
docker-compose up --build
```

### Local Development
```bash
# Install dependencies
pip install -e .[dev]

# Run tests
pytest

# Start the application
meeting-agent
```

## 🔧 Configuration

### Required Environment Variables
```bash
# Notion Integration
NOTION_TOKEN=secret_your_notion_token
DATABASE_ID=your_meetings_database_id
TASKS_DATABASE_ID=your_tasks_database_id

# AI Services
OPENAI_API_KEY=sk-your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key

# Optional: Memory & Async Processing
MEM0_API_KEY=your_mem0_key
REDIS_URL=redis://localhost:6379
ENABLE_ASYNC_PROCESSING=false
```

### Advanced Configuration
The system supports extensive configuration through environment variables:

- **AI Model Parameters**: Per-task temperature, max tokens, model selection
- **Rate Limiting**: Retry strategies, backoff timing, quota management  
- **Async Processing**: Queue sizes, worker timeouts, chunk parameters
- **Logging**: Levels, formats, file rotation, structured output

See [Configuration Guide](docs/guides/configuration.md) for complete details.

## 🎯 Usage

### Basic Workflow
1. **Start the Application**: Run `meeting-agent` or use Docker
2. **Paste Transcript**: Input your meeting transcript (supports multi-line)
3. **Review Generated Notes**: AI creates structured meeting notes
4. **Manage Tasks**: Create action items from identified tasks
5. **Sync with Notion**: Automatically updates your Notion databases

### Advanced Features

#### Async Processing for Large Meetings
```bash
# Enable async processing
export ENABLE_ASYNC_PROCESSING=true

# Start worker
meeting-worker

# Process large transcripts in background
meeting-agent
```

#### Rate Limit Monitoring
```bash
# Check current API status
meeting-monitor status

# Watch in real-time
meeting-monitor watch --interval 10

# Process queued requests
meeting-monitor process --max-requests 20
```

#### AI Configuration Management
```bash
# View current AI settings
meeting-config show

# Optimize for accuracy (legal/medical)
meeting-config update summarization temperature 0.1

# Enable creative task suggestions
meeting-config update task_suggestion temperature 0.8
```

## 🏗️ Architecture

```
┌─────────────────┐    ┌───────────────┐    ┌─────────────────┐
│   CLI Interface │───▶│  Rate Limiter │───▶│   AI Services   │
│                 │    │               │    │  OpenAI/Claude  │
└─────────────────┘    └───────────────┘    └─────────────────┘
         │                       │                      │
         ▼                       ▼                      ▼
┌─────────────────┐    ┌───────────────┐    ┌─────────────────┐
│ Notion Client   │    │ Redis Queue   │    │ Memory System   │
│                 │    │ (Async Jobs)  │    │ (Context/Learning)│
└─────────────────┘    └───────────────┘    └─────────────────┘
```

### Key Components

- **AI Client**: Multi-provider AI integration with intelligent routing
- **Rate Limiter**: Exponential backoff with jitter and request queuing
- **Task Manager**: Smart action item extraction and creation
- **Chunking System**: Speaker-aware transcript segmentation
- **Memory Client**: Context learning and meeting similarity detection
- **Configuration System**: Pydantic-based validation and management

## Project Structure

```
Meeting_Agent/
├── src/
│   └── meeting_agent/
│       ├── __init__.py          # Package initialization
│       ├── main.py              # Main application entry point
│       ├── config.py            # Configuration management
│       ├── notion_client.py     # Notion API client
│       ├── ai_client.py         # AI services (OpenAI, Claude)
│       ├── ui.py                # User interface helpers
│       ├── task_manager.py      # Task creation and management
│       └── memory_client.py     # Memory management with Mem0
├── config/
│   └── .env.example             # Environment variables template
├── docs/
│   └── API.md                   # API documentation
├── meeting_agent.py             # Main launcher script
├── requirements.txt             # Python dependencies
└── README.md                    # This file
```

## Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Meeting_Agent
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   cp config/.env.example .env
   # Edit .env with your API keys and database IDs
   ```

## Configuration

Create a `.env` file in the project root with the following variables:

```env
# Notion Configuration
NOTION_TOKEN=your_notion_integration_token
DATABASE_ID=your_meetings_database_id
TASKS_DATABASE_ID=your_tasks_database_id

# AI Services
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key

# Optional Settings
DEFAULT_ASSIGNEE=Your Name

# Memory Configuration (Optional)
MEM0_API_KEY=your_mem0_api_key
DEFAULT_USER_ID=your_unique_user_id
MEMORY_ENABLED=true
```

### Setting up Notion

1. **Create a Notion Integration**
   - Go to [Notion Developers](https://www.notion.so/my-integrations)
   - Create a new integration and copy the token

2. **Create Databases**
   - Create a "Meetings" database with these properties:
     - `Title` (Title)
     - `Date` (Date)
     - `Description` (Rich Text)
     - `Meeting Type` (Select)
     - `Topics` (Multi-select)
     - `Status` (Select)
     - `Linked Meetings` (Relation to self)
     - `Action Items` (Relation to Tasks database)

   - Create a "Tasks" database with these properties:
     - `Title` (Title)
     - `Assignee` (Multi-select)
     - `Due Date` (Date)
     - `Status` (Status)
     - `Linked Meeting` (Relation to Meetings database)

3. **Share databases with your integration**
   - Click "Share" on each database
   - Invite your integration

### Setting up Memory (Optional)

To enable intelligent memory features:

1. **Get Mem0 API Key**
   - Sign up at [Mem0.ai](https://mem0.ai)
   - Get your API key from the dashboard

2. **Configure Memory Settings**
   - Add `MEM0_API_KEY` to your `.env` file
   - Set `DEFAULT_USER_ID` to a unique identifier (e.g., your email)
   - Keep `MEMORY_ENABLED=true`

3. **Benefits of Memory**
   - Personalized meeting summaries
   - Better task suggestions based on history
   - Contextual Q&A responses
   - Learning from your preferences over time

## Usage

### Basic Usage

1. **Run the application**
   ```bash
   python meeting_agent.py
   ```

2. **Input meeting data**
   - Paste your meeting transcript
   - Enter a meeting title
   - The app will process and create a Notion page

3. **Organize your meeting**
   - Select meeting type, topics, and status
   - Review and link similar meetings if found

4. **Manage tasks**
   - Use the Q&A mode to create tasks
   - Type phrases like "add these action items as task"
   - Tasks are automatically assigned to you

### Q&A Mode

After creating a meeting, you can:

- Ask questions about your meeting history
- Create tasks from action items
- Search for specific topics or decisions

**Example queries:**
- "What decisions were made about the project timeline?"
- "Add these action items as tasks"
- "Show me meetings about budget planning"
- "memory stats" (if memory is enabled)

**Memory-Enhanced Features:**
- Personalized responses based on your meeting history
- Context-aware answers using past interactions
- Learning from your preferences and patterns

### Task Creation

The system can create tasks in two ways:

1. **From Action Items**: Automatically parsed from meeting notes
2. **Custom Tasks**: Manually entered during the Q&A session

Tasks are automatically:
- Assigned to you (configurable)
- Linked to the meeting
- Given appropriate status

## API Keys Required

- **OpenAI API Key**: For transcript processing and Q&A
- **Anthropic API Key**: For meeting similarity analysis
- **Notion Integration Token**: For database operations
- **Mem0 API Key** (Optional): For intelligent memory features

## Dependencies

- `openai` - OpenAI API client
- `anthropic` - Anthropic API client
- `requests` - HTTP requests for Notion API
- `python-dotenv` - Environment variable management
- `mem0ai` - Intelligent memory for AI agents

## Development

### Running Tests

```bash
python -m pytest tests/
```

### Code Style

The project follows PEP 8 style guidelines. Use `black` for formatting:

```bash
black src/
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Troubleshooting

### Common Issues

1. **"Cannot mention bots" error**
   - Ensure `Assignee` field in Tasks database is set to "Multi-select", not "People"

2. **"Status option does not exist" error**
   - The app will automatically use available status options
   - Check your Tasks database status field configuration

3. **"Invalid database ID" error**
   - Verify your database IDs in the `.env` file
   - Ensure your integration has access to the databases

### Debug Mode

Add debug prints by modifying the configuration:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Roadmap

- [ ] Web interface
- [ ] Batch processing of multiple meetings
- [ ] Integration with calendar apps
- [ ] Advanced meeting analytics
- [ ] Export functionality
- [ ] Mobile app

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Search existing issues on GitHub
3. Create a new issue with detailed information

## Author

**Praveen Menon**

## Acknowledgments

- OpenAI for GPT models
- Anthropic for Claude
- Notion for their excellent API
- The Python community for amazing libraries