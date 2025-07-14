# Meeting Agent

AI-powered meeting transcription and task management with Notion integration.

## Overview

Meeting Agent is a Python application that transforms meeting transcripts into structured notes, automatically creates tasks from action items, and manages everything in your Notion workspace. It uses OpenAI's GPT models for transcript processing and Anthropic's Claude for similarity analysis.

## Features

- 🎯 **Transcript Processing**: Convert raw meeting transcripts into structured notes
- 📝 **Notion Integration**: Automatically create and organize meeting pages in Notion
- ✅ **Task Management**: Extract action items and create tasks with due dates
- 🔍 **Smart Similarity**: Find and link related meetings using AI
- 💬 **Q&A Mode**: Query your meeting history with natural language
- 🏷️ **Tagging System**: Organize meetings by type, topics, and status

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
│       └── task_manager.py      # Task creation and management
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

## Dependencies

- `openai` - OpenAI API client
- `anthropic` - Anthropic API client
- `requests` - HTTP requests for Notion API
- `python-dotenv` - Environment variable management

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