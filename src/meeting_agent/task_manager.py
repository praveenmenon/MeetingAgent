"""
Task management functionality for Meeting Agent
"""

import re
from datetime import datetime
from typing import Dict, List, Optional

from .config import DEFAULT_ASSIGNEE


class TaskManager:
    """Handles task creation and management"""

    def __init__(self, notion_client, ai_client, ui, memory_client=None):
        self.notion_client = notion_client
        self.ai_client = ai_client
        self.ui = ui
        self.memory_client = memory_client

    def parse_date_from_question(self, question: str) -> Optional[str]:
        """
        Parse date from user question

        Args:
            question: User's question about creating tasks

        Returns:
            Date string in YYYY-MM-DD format if found, None otherwise
        """
        # Common date patterns
        date_patterns = [
            r"\b(\d{4}-\d{2}-\d{2})\b",  # YYYY-MM-DD
            r"\b(\d{4}/\d{2}/\d{2})\b",  # YYYY/MM/DD
            r"\b(\d{2}/\d{2}/\d{4})\b",  # MM/DD/YYYY
            r"\b(\d{2}-\d{2}-\d{4})\b",  # MM-DD-YYYY
            r"dated\s+(\d{4}-\d{2}-\d{2})",  # "dated 2025-07-17"
            r"due\s+(\d{4}-\d{2}-\d{2})",  # "due 2025-07-17"
            r"for\s+(\d{4}-\d{2}-\d{2})",  # "for 2025-07-17"
        ]

        for pattern in date_patterns:
            match = re.search(pattern, question, re.IGNORECASE)
            if match:
                date_str = match.group(1)

                # Try to parse and validate the date
                try:
                    # Handle different formats
                    if "/" in date_str:
                        if date_str.count("/") == 2:
                            parts = date_str.split("/")
                            if len(parts[0]) == 4:  # YYYY/MM/DD
                                parsed_date = datetime.strptime(date_str, "%Y/%m/%d")
                            else:  # MM/DD/YYYY
                                parsed_date = datetime.strptime(date_str, "%m/%d/%Y")
                    elif "-" in date_str:
                        parts = date_str.split("-")
                        if len(parts[0]) == 4:  # YYYY-MM-DD
                            parsed_date = datetime.strptime(date_str, "%Y-%m-%d")
                        else:  # MM-DD-YYYY
                            parsed_date = datetime.strptime(date_str, "%m-%d-%Y")
                    else:
                        continue

                    # Return in YYYY-MM-DD format
                    return parsed_date.strftime("%Y-%m-%d")

                except ValueError:
                    continue

        return None

    def parse_action_items_from_notes(self, notes: str) -> List[str]:
        """Parse action items from meeting notes"""
        action_items = []
        notes_lines = notes.split("\n")
        in_actions = False

        for line in notes_lines:
            line = line.strip()
            if "## Action Items" in line:
                in_actions = True
            elif in_actions and line.startswith("- "):
                action_items.append(line[2:].strip())
            elif in_actions and line.startswith("##"):
                break

        return action_items

    def create_tasks_from_action_items(
        self, action_items: List[str], meeting_id: str, default_due_date: str = None
    ) -> List[str]:
        """Create tasks from action items"""
        task_ids = []
        assignee_name = DEFAULT_ASSIGNEE

        for action in action_items:
            # Extract task description (ignore assignee names from notes)
            task_desc = action.split(":", 1)[1].strip() if ":" in action else action

            # Use default due date if provided, otherwise ask user
            if default_due_date:
                due_date = default_due_date
                print(f"Using default due date {default_due_date} for: {task_desc}")
            else:
                due_date = self.ui.get_task_due_date(task_desc)

            try:
                task_id = self.notion_client.create_task_page(
                    task_desc, assignee_name, due_date, meeting_id
                )
                task_ids.append(task_id)
                print(f"✓ Created task: {task_desc}")

                # Store task creation in memory
                if self.memory_client and self.memory_client.is_enabled():
                    task_info = {
                        "title": task_desc,
                        "assignee": assignee_name,
                        "due_date": due_date,
                        "meeting_id": meeting_id,
                    }
                    self.memory_client.store_task_feedback(
                        task_info, "Task created successfully from action item"
                    )
            except Exception as e:
                print(f"✗ Error creating task '{task_desc}': {e}")

        return task_ids

    def create_selected_action_items(
        self, action_items: List[str], meeting_id: str
    ) -> List[str]:
        """Create tasks from selected action items with user choice"""
        if not action_items:
            return []

        print(f"\nSelect which action items to create as tasks:")
        for i, action in enumerate(action_items, 1):
            print(f"{i}. {action}")

        while True:
            choice = input(
                "Select action items (comma-separated numbers, e.g., '1,3,4' or 'all'): "
            ).strip()

            if not choice:
                return []

            if choice.lower() == "all":
                selected_indices = list(range(len(action_items)))
                break

            try:
                selected_indices = []
                for num in choice.split(","):
                    num = int(num.strip()) - 1
                    if 0 <= num < len(action_items):
                        selected_indices.append(num)
                    else:
                        print(
                            f"Invalid number: {num + 1}. Please use numbers 1-{len(action_items)}."
                        )
                        break
                else:
                    break
            except ValueError:
                print("Invalid input. Please enter numbers separated by commas.")

        if not selected_indices:
            return []

        selected_actions = [action_items[i] for i in selected_indices]
        return self.create_tasks_from_action_items(selected_actions, meeting_id)

    def create_custom_tasks(self, meeting_id: str) -> List[str]:
        """Create custom tasks from user input"""
        task_ids = []
        assignee_name = DEFAULT_ASSIGNEE

        while True:
            task_input = self.ui.get_custom_task_input()

            if task_input["done"]:
                break

            try:
                task_id = self.notion_client.create_task_page(
                    task_input["description"],
                    assignee_name,
                    task_input["due_date"],
                    meeting_id,
                )
                task_ids.append(task_id)
                print(f"✓ Created task: {task_input['description']}")

                # Store task creation in memory
                if self.memory_client and self.memory_client.is_enabled():
                    task_info = {
                        "title": task_input["description"],
                        "assignee": assignee_name,
                        "due_date": task_input["due_date"],
                        "meeting_id": meeting_id,
                    }
                    self.memory_client.store_task_feedback(
                        task_info, "Task created successfully from custom input"
                    )
            except Exception as e:
                print(f"✗ Error creating task '{task_input['description']}': {e}")

        return task_ids

    def handle_task_creation(
        self,
        notes: str,
        meeting_id: str,
        meeting_title: str,
        original_question: str = None,
    ) -> None:
        """Handle the complete task creation workflow"""
        print(f"Adding tasks for meeting: {meeting_title}")

        # Parse date from the original question if provided
        default_due_date = None
        if original_question:
            default_due_date = self.parse_date_from_question(original_question)
            if default_due_date:
                print(f"📅 Found date in your request: {default_due_date}")

        # Parse action items from notes
        action_items = self.parse_action_items_from_notes(notes)
        task_ids = []

        # Process action items from notes
        if action_items:
            self.ui.display_action_items(action_items)

            if self.ui.should_create_from_actions(len(action_items)):
                task_ids.extend(
                    self.create_tasks_from_action_items(
                        action_items, meeting_id, default_due_date
                    )
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

    def suggest_and_create_tasks(
        self, notes: str, meeting_id: str, meeting_title: str
    ) -> None:
        """Suggest tasks based on meeting content and allow user to create them"""
        print("Analyzing meeting for task suggestions...")

        # Get suggested tasks from AI
        suggested_tasks = self.ai_client.suggest_tasks_from_meeting(
            notes, meeting_title
        )

        # Parse existing action items
        action_items = self.parse_action_items_from_notes(notes)

        # Display suggestions and options
        self.ui.display_task_suggestions(suggested_tasks, action_items)

        # Get user selection
        selected_options = self.ui.get_task_selection()

        if not selected_options:
            print("No options selected. Skipping task creation.")
            return

        task_ids = []

        # Create tasks from action items if selected
        if "action_items" in selected_options and action_items:
            print(f"\n📋 Creating tasks from action items:")
            for i, action in enumerate(action_items, 1):
                print(f"{i}. {action}")

            print(f"\nSelect which action items to create as tasks:")
            print("• Enter 'all' to create all action items")
            print("• Enter specific numbers (e.g., '1,3,4') to select some")
            print("• Press Enter to skip")

            choice = input("Your choice: ").strip().lower()

            if choice == "all":
                task_ids.extend(
                    self.create_tasks_from_action_items(action_items, meeting_id)
                )
            elif choice and choice != "":
                # Try to parse as numbers
                try:
                    selected_indices = []
                    for num in choice.split(","):
                        num = int(num.strip()) - 1
                        if 0 <= num < len(action_items):
                            selected_indices.append(num)
                        else:
                            print(
                                f"Invalid number: {num + 1}. Please use numbers 1-{len(action_items)}."
                            )
                            break
                    else:
                        if selected_indices:
                            selected_actions = [
                                action_items[i] for i in selected_indices
                            ]
                            task_ids.extend(
                                self.create_tasks_from_action_items(
                                    selected_actions, meeting_id
                                )
                            )
                        else:
                            print("No valid action items selected.")
                except ValueError:
                    print(
                        "Invalid input format. Please use 'all' or numbers like '1,3,4'."
                    )
            else:
                print("Skipping action items.")

        # Create tasks from AI suggestions if selected
        if "ai_suggestions" in selected_options and suggested_tasks:
            task_ids.extend(
                self.create_tasks_from_suggestions(suggested_tasks, meeting_id)
            )

        # Allow custom tasks if selected
        if "custom" in selected_options:
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

    def create_tasks_from_suggestions(
        self, suggested_tasks: List[Dict], meeting_id: str
    ) -> List[str]:
        """Create tasks from AI suggestions"""
        task_ids = []
        assignee_name = DEFAULT_ASSIGNEE

        for suggestion in suggested_tasks:
            task_desc = suggestion.get("title", "")
            priority = suggestion.get("priority", "Medium")
            suggested_due = suggestion.get("suggested_due_date", "")

            if not task_desc:
                continue

            # Ask user for due date, showing suggestion if available
            due_date = self.ui.get_task_due_date_with_suggestion(
                task_desc, suggested_due
            )

            try:
                task_id = self.notion_client.create_task_page(
                    task_desc, assignee_name, due_date, meeting_id, priority
                )
                task_ids.append(task_id)
                print(f"✓ Created task: {task_desc}")

                # Store task creation in memory
                if self.memory_client and self.memory_client.is_enabled():
                    task_info = {
                        "title": task_desc,
                        "assignee": assignee_name,
                        "due_date": due_date,
                        "priority": priority,
                        "meeting_id": meeting_id,
                    }
                    self.memory_client.store_task_feedback(
                        task_info, "Task created successfully from AI suggestion"
                    )
            except Exception as e:
                print(f"✗ Error creating task '{task_desc}': {e}")

        return task_ids

    def is_task_related_question(self, question: str) -> bool:
        """Check if the question is related to task creation"""
        task_keywords = [
            "add task",
            "create task",
            "add action",
            "task from action",
            "action items as task",
            "add these action",
            "create these task",
            "add them to task",
            "add to task",
            "make task",
            "turn into task",
            "convert to task",
            "task these",
            "task them",
            "add as task",
        ]

        return any(keyword in question.lower() for keyword in task_keywords)
