"""
Task management functionality for Meeting Agent
"""

import re
from typing import List, Dict, Optional
from .config import DEFAULT_ASSIGNEE


class TaskManager:
    """Handles task creation and management"""
    
    def __init__(self, notion_client, ai_client, ui):
        self.notion_client = notion_client
        self.ai_client = ai_client
        self.ui = ui
    
    def parse_action_items_from_notes(self, notes: str) -> List[str]:
        """Parse action items from meeting notes"""
        action_items = []
        notes_lines = notes.split('\n')
        in_actions = False
        
        for line in notes_lines:
            line = line.strip()
            if '## Action Items' in line:
                in_actions = True
            elif in_actions and line.startswith('- '):
                action_items.append(line[2:].strip())
            elif in_actions and line.startswith('##'):
                break
        
        return action_items
    
    def create_tasks_from_action_items(self, action_items: List[str], meeting_id: str) -> List[str]:
        """Create tasks from action items"""
        task_ids = []
        assignee_name = DEFAULT_ASSIGNEE
        
        for action in action_items:
            # Extract task description (ignore assignee names from notes)
            task_desc = action.split(':', 1)[1].strip() if ':' in action else action
            
            # Get due date from user
            due_date = self.ui.get_task_due_date(task_desc)
            
            try:
                task_id = self.notion_client.create_task_page(
                    task_desc, assignee_name, due_date, meeting_id
                )
                task_ids.append(task_id)
                print(f"✓ Created task: {task_desc}")
            except Exception as e:
                print(f"✗ Error creating task '{task_desc}': {e}")
        
        return task_ids
    
    def create_custom_tasks(self, meeting_id: str) -> List[str]:
        """Create custom tasks from user input"""
        task_ids = []
        assignee_name = DEFAULT_ASSIGNEE
        
        while True:
            task_input = self.ui.get_custom_task_input()
            
            if task_input['done']:
                break
            
            try:
                task_id = self.notion_client.create_task_page(
                    task_input['description'], 
                    assignee_name, 
                    task_input['due_date'], 
                    meeting_id
                )
                task_ids.append(task_id)
                print(f"✓ Created task: {task_input['description']}")
            except Exception as e:
                print(f"✗ Error creating task '{task_input['description']}': {e}")
        
        return task_ids
    
    def handle_task_creation(self, notes: str, meeting_id: str, meeting_title: str) -> None:
        """Handle the complete task creation workflow"""
        print(f"Adding tasks for meeting: {meeting_title}")
        
        # Parse action items from notes
        action_items = self.parse_action_items_from_notes(notes)
        task_ids = []
        
        # Process action items from notes
        if action_items:
            self.ui.display_action_items(action_items)
            
            if self.ui.should_create_from_actions(len(action_items)):
                task_ids.extend(
                    self.create_tasks_from_action_items(action_items, meeting_id)
                )
        else:
            print("No action items found in meeting notes.")
        
        # Option to add custom tasks
        if self.ui.should_add_custom_tasks():
            task_ids.extend(self.create_custom_tasks(meeting_id))
        
        # Link tasks to meeting
        if task_ids:
            try:
                self.notion_client.link_actions_to_meeting(meeting_id, task_ids)
                self.ui.display_task_creation_summary(len(task_ids))
            except Exception as e:
                print(f"✗ Error linking tasks to meeting: {e}")
        else:
            print("No tasks were created.")
    
    def is_task_related_question(self, question: str) -> bool:
        """Check if the question is related to task creation"""
        task_keywords = [
            "add task", "create task", "add action", "task from action",
            "action items as task", "add these action", "create these task"
        ]
        
        return any(keyword in question.lower() for keyword in task_keywords)