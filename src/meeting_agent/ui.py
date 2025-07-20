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
        
        print(f"\nOptions for {property_name}:")
        for i, opt in enumerate(options, 1):
            print(f"{i}. {opt}")
        print(f"{len(options)+1}. Add new option")
        print()
        
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
        print("\nPossible similar meetings:")
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
            print(f"\n✓ Successfully created and linked {task_count} tasks to the meeting.")
        else:
            print("\nNo tasks were created.")
    
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
        print(f"\nFound {len(action_items)} action items in notes:")
        for i, action in enumerate(action_items, 1):
            print(f"{i}. {action}")
    
    def get_user_input(self, prompt: str) -> str:
        """Get user input with prompt"""
        print(prompt)
        print("(Type your content, then press Ctrl+D on Unix/Mac or Ctrl+Z on Windows to finish)")
        lines = []
        try:
            while True:
                line = input()
                lines.append(line)
        except EOFError:
            pass
        return '\n'.join(lines)
    
    def ask_to_add_tasks(self) -> bool:
        """Ask user if they want to add tasks to the meeting"""
        response = input("Would you like to add tasks based on this meeting? (y/n): ").lower()
        return response == 'y'
    
    def display_task_suggestions(self, suggested_tasks: List[dict], action_items: List[str]) -> None:
        """Display AI-suggested tasks and action items"""
        print("\n📋 Task Options:")
        
        option_num = 1
        available_options = []
        
        # Display action items if found
        if action_items:
            print(f"\n{option_num}. Action Items from meeting notes ({len(action_items)} items):")
            for i, action in enumerate(action_items, 1):
                print(f"   {i}. {action}")
            available_options.append(str(option_num))
            option_num += 1
        
        # Display AI suggestions
        if suggested_tasks:
            print(f"\n{option_num}. AI-suggested tasks based on meeting content ({len(suggested_tasks)} items):")
            for i, task in enumerate(suggested_tasks, 1):
                priority_indicator = "🔴" if task.get('priority') == 'High' else "🟡" if task.get('priority') == 'Medium' else "🟢"
                due_date = f" (suggested: {task.get('suggested_due_date', 'No suggestion')})" if task.get('suggested_due_date') else ""
                print(f"   {i}. {priority_indicator} {task.get('title', '')}{due_date}")
                if task.get('reason'):
                    print(f"      Reason: {task.get('reason', '')}")
            available_options.append(str(option_num))
            option_num += 1
        
        # Always show custom tasks option
        print(f"\n{option_num}. Add custom tasks manually")
        available_options.append(str(option_num))
        
        # Store available options for validation
        self._available_options = available_options
        self._has_action_items = bool(action_items)
        self._has_ai_suggestions = bool(suggested_tasks)
        
        if len(available_options) > 1:
            print(f"\nYou can select multiple options (e.g., '{','.join(available_options[:2])}' or '{available_options[0]},{available_options[-1]}')")
        else:
            print(f"\nSelect option {available_options[0]} or press Enter to skip")
    
    def get_task_selection(self) -> List[str]:
        """Get user's selection of which task options to use"""
        available_options = getattr(self, '_available_options', ['1'])
        has_action_items = getattr(self, '_has_action_items', False)
        has_ai_suggestions = getattr(self, '_has_ai_suggestions', False)
        
        while True:
            valid_options_str = ', '.join(available_options)
            choice = input(f"Select options ({valid_options_str}) or press Enter to skip: ").strip()
            
            if not choice:
                return []
            
            try:
                selections = []
                for num_str in choice.split(','):
                    num = int(num_str.strip())
                    
                    if str(num) not in available_options:
                        print(f"Invalid option: {num}. Please use {valid_options_str}.")
                        break
                    
                    # Map option number to selection type
                    option_index = 1
                    
                    if has_action_items and num == option_index:
                        selections.append('action_items')
                        continue
                    elif has_action_items:
                        option_index += 1
                    
                    if has_ai_suggestions and num == option_index:
                        selections.append('ai_suggestions')
                        continue
                    elif has_ai_suggestions:
                        option_index += 1
                    
                    # Custom tasks option (always last)
                    if num == option_index:
                        selections.append('custom')
                        continue
                else:
                    return selections
                    
            except ValueError:
                print(f"Invalid input. Please enter numbers separated by commas (e.g., '{available_options[0]}')")
    
    def get_task_due_date_with_suggestion(self, task_desc: str, suggested_due: str) -> Optional[str]:
        """Get due date for a task with AI suggestion"""
        if suggested_due:
            prompt = f"Due date for '{task_desc}' (suggested: {suggested_due}, or YYYY-MM-DD, or Enter to skip): "
        else:
            prompt = f"Due date for '{task_desc}' (YYYY-MM-DD, or Enter to skip): "
        
        due_date = input(prompt).strip()
        return due_date if due_date else None