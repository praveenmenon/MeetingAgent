# API Documentation

## Overview

This document describes the internal API structure of the Meeting Agent application.

## Core Components

### NotionClient

The `NotionClient` class handles all interactions with the Notion API.

#### Methods

- `get_database_properties(database_id)`: Get properties of a Notion database
- `get_select_options(property_name)`: Get select options for a property
- `create_meeting_page(title, date, description)`: Create a new meeting page
- `append_notes_to_page(page_id, notes)`: Append formatted notes to a page
- `create_task_page(task_desc, assignee_name, due_date, meeting_id)`: Create a new task
- `link_actions_to_meeting(meeting_id, task_ids)`: Link tasks to a meeting
- `query_past_meetings()`: Query past meetings from the database
- `get_full_notes(page_id)`: Get full notes content from a page
- `update_meeting_fields(page_id, meeting_type, tags, status)`: Update meeting fields
- `link_meetings(new_page_id, similar_ids)`: Link similar meetings together

### AIClient

The `AIClient` class handles AI-powered text processing.

#### Methods

- `summarize_transcript(transcript)`: Convert transcript to structured notes
- `generate_brief_description(notes)`: Generate brief description from notes
- `check_similarity(new_notes, past_meetings, new_page_id)`: Find similar meetings
- `answer_question(question, all_notes)`: Answer questions based on notes

### TaskManager

The `TaskManager` class handles task creation and management.

#### Methods

- `parse_action_items_from_notes(notes)`: Parse action items from notes
- `create_tasks_from_action_items(action_items, meeting_id)`: Create tasks from action items
- `create_custom_tasks(meeting_id)`: Create custom tasks from user input
- `handle_task_creation(notes, meeting_id, meeting_title)`: Handle complete task workflow
- `is_task_related_question(question)`: Check if question is task-related

### UserInterface

The `UserInterface` class handles user interactions.

#### Methods

- `prompt_for_select(notion_client, property_name, multi)`: Prompt for select options
- `display_similar_meetings(similar_meetings)`: Display similar meetings
- `get_similarity_action()`: Get user action for similar meetings
- `get_task_due_date(task_desc)`: Get due date for a task
- `get_custom_task_input()`: Get custom task input
- `should_create_from_actions(action_count)`: Ask about creating tasks from actions
- `should_add_custom_tasks()`: Ask about adding custom tasks

## Error Handling

### Common Exceptions

- `ValueError`: Raised when API calls fail or invalid data is provided
- `KeyError`: Raised when required fields are missing
- `ConnectionError`: Raised when API is unreachable

### Best Practices

1. Always validate configuration before making API calls
2. Handle API rate limits gracefully
3. Provide meaningful error messages to users
4. Log errors for debugging purposes

## Configuration

### Environment Variables

All configuration is managed through environment variables:

- `NOTION_TOKEN`: Notion integration token
- `DATABASE_ID`: Meetings database ID
- `TASKS_DATABASE_ID`: Tasks database ID
- `OPENAI_API_KEY`: OpenAI API key
- `ANTHROPIC_API_KEY`: Anthropic API key
- `DEFAULT_ASSIGNEE`: Default task assignee name

### Validation

The `validate_config()` function ensures all required variables are present.

## Data Flow

1. User provides meeting transcript and title
2. AI processes transcript into structured notes
3. Notion page is created with meeting data
4. User updates meeting fields (type, topics, status)
5. AI checks for similar meetings
6. User can group similar meetings
7. Q&A mode allows task creation and queries

## API Limits

### Notion API

- Rate limit: 3 requests per second
- Page size limit: 100 items per query
- Block limit: 100 blocks per append operation

### OpenAI API

- Rate limits vary by model and plan
- Token limits: 4096 tokens for GPT-4o-mini

### Anthropic API

- Rate limits vary by model and plan
- Token limits: 200,000 tokens for Claude-3-5-sonnet