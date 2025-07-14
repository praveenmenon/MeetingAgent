"""
User interface helpers for Meeting Agent
"""

from typing import List, Optional


class UserInterface:
    """Helper class for user interactions"""
    
    def prompt_for_select(self, notion_client, property_name: str, multi: bool = False) -> Optional[str] or List[str]:
        """Prompt user to select from available options or add new ones"""
        options = notion_client.get_select_options(property_name)
        
        if not options:
            if multi:
                tags_input = input(f"Enter {property_name} separated by commas (add new): ").strip()
                return [tag.strip() for tag in tags_input.split(',') if tag.strip()]
            else:
                return input(f"Enter {property_name} (no options available, add new): ").strip() or None
        
        print(f"Options for {property_name}:")
        for i, opt in enumerate(options, 1):
            print(f"{i}. {opt}")
        print(f"{len(options)+1}. Add new option")
        
        if multi:
            selections = []
            while True:
                choice = input(f"Select number(s) for {property_name} (comma-separated, or 'done'): ").strip()
                if choice.lower() == 'done':
                    break
                
                try:
                    nums = [int(n.strip()) for n in choice.split(',')]
                    for num in nums:
                        if 1 <= num <= len(options):
                            selections.append(options[num-1])
                        elif num == len(options)+1:
                            new_opt = input("Enter new option: ").strip()
                            if new_opt:
                                selections.append(new_opt)
                except ValueError:
                    print("Invalid input. Please enter numbers separated by commas.")
            
            return selections
        else:
            choice = input(f"Select number for {property_name}: ").strip()
            try:
                num = int(choice)
                if 1 <= num <= len(options):
                    return options[num-1]
                elif num == len(options)+1:
                    new_opt = input("Enter new option: ").strip()
                    return new_opt if new_opt else None
            except ValueError:
                print("Invalid input. Please enter a number.")
            
            return None
    
    def display_similar_meetings(self, similar_meetings: List[dict]) -> None:
        """Display similar meetings to the user"""
        print("Possible similar meetings:")
        for meeting in similar_meetings:
            details = meeting
            desc_preview = details['description'][:100] + "..." if len(details['description']) > 100 else details['description']
            print(f"- ID: {details['id']}, Title: {details['title']}, Date: {details['date']}, Description: {desc_preview}")
    
    def get_similarity_action(self) -> str:
        """Get user action for handling similar meetings"""
        while True:
            action = input("What would you like to do? (group / details <id> / cancel): ").strip().lower()
            if action in ['group', 'cancel'] or action.startswith('details '):
                return action
            else:
                print("Invalid option. Try 'group', 'details <id>', or 'cancel'.")
    
    def display_task_creation_summary(self, task_count: int) -> None:
        """Display summary of task creation"""
        if task_count > 0:
            print(f"✓ Successfully created and linked {task_count} tasks to the meeting.")
        else:
            print("No tasks were created.")
    
    def get_task_due_date(self, task_desc: str) -> Optional[str]:
        """Get due date for a task"""
        due_date = input(f"Enter due date for '{task_desc}' (YYYY-MM-DD, or press Enter to skip): ").strip()
        return due_date if due_date else None
    
    def get_custom_task_input(self) -> dict:
        """Get custom task input from user"""
        task_desc = input("Enter task description (or 'done' to finish): ")
        if task_desc.lower() == 'done':
            return {'done': True}
        
        due_date = input("Enter due date (YYYY-MM-DD, or press Enter to skip): ").strip()
        return {
            'done': False,
            'description': task_desc,
            'due_date': due_date if due_date else None
        }
    
    def should_create_from_actions(self, action_count: int) -> bool:
        """Ask user if they want to create tasks from action items"""
        return input(f"Create tasks from these {action_count} action items? (y/n): ").lower() == 'y'
    
    def should_add_custom_tasks(self) -> bool:
        """Ask user if they want to add custom tasks"""
        return input("Do you want to add custom tasks? (y/n): ").lower() == 'y'
    
    def display_action_items(self, action_items: List[str]) -> None:
        """Display found action items"""
        print(f"Found {len(action_items)} action items in notes:")
        for i, action in enumerate(action_items, 1):
            print(f"{i}. {action}")
    
    def get_user_input(self, prompt: str) -> str:
        """Get user input with prompt"""
        return input(prompt)