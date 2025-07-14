"""
Main entry point for Meeting Agent
"""

from datetime import datetime
from .config import validate_config
from .notion_client import NotionClient
from .ai_client import AIClient
from .ui import UserInterface
from .task_manager import TaskManager


class MeetingAgent:
    """Main Meeting Agent application"""
    
    def __init__(self):
        # Validate configuration
        validate_config()
        
        # Initialize components
        self.notion_client = NotionClient()
        self.ai_client = AIClient()
        self.ui = UserInterface()
        self.task_manager = TaskManager(self.notion_client, self.ai_client, self.ui)
    
    def run(self):
        """Main application loop"""
        print("=== Meeting Agent ===")
        print("AI-powered meeting transcription and task management")
        print()
        
        # Get meeting input
        transcript = self.ui.get_user_input("Paste meeting transcript: ")
        title = self.ui.get_user_input("Meeting title: ")
        date = datetime.now().isoformat()[:10]
        
        # Process transcript
        print("Processing transcript...")
        notes = self.ai_client.summarize_transcript(transcript)
        brief_desc = self.ai_client.generate_brief_description(notes)
        
        print("Generated Brief Description:")
        print(brief_desc)
        print()
        print("Generated Notes:")
        print(notes)
        print()
        
        # Create Notion page
        print("Creating Notion page...")
        new_page_id = self.notion_client.create_meeting_page(title, date, brief_desc)
        self.notion_client.append_notes_to_page(new_page_id, notes)
        print(f"✓ Created Notion page: {new_page_id}")
        
        # Update meeting fields
        print("Updating meeting fields...")
        meeting_type = self.ui.prompt_for_select(self.notion_client, 'Meeting Type')
        tags = self.ui.prompt_for_select(self.notion_client, 'Topics', multi=True)
        status = self.ui.prompt_for_select(self.notion_client, 'Status')
        
        self.notion_client.update_meeting_fields(new_page_id, meeting_type, tags, status)
        print("✓ Updated meeting fields")
        
        # Check for similar meetings
        print("Checking for similar meetings...")
        past_meetings = self.notion_client.query_past_meetings()
        similar_ids = self.ai_client.check_similarity(notes, past_meetings, new_page_id)
        
        if similar_ids:
            # Get detailed information about similar meetings
            similar_meetings = [
                self.notion_client.get_meeting_details(sim_id) 
                for sim_id in similar_ids
            ]
            
            self.ui.display_similar_meetings(similar_meetings)
            
            # Handle user action
            while True:
                action = self.ui.get_similarity_action()
                
                if action == 'group':
                    self.notion_client.link_meetings(new_page_id, similar_ids)
                    print("✓ Meetings grouped successfully!")
                    break
                elif action.startswith('details '):
                    try:
                        detail_id = action.split(' ')[1]
                        if detail_id in similar_ids:
                            full_notes = self.notion_client.get_full_notes(detail_id)
                            print(f"Full notes for {detail_id}:")
                            print(full_notes)
                        else:
                            print("ID not in suggestions.")
                    except IndexError:
                        print("Invalid ID format. Use 'details <id>'")
                elif action == 'cancel':
                    print("Grouping cancelled.")
                    break
        else:
            print("No similar meetings found.")
        
        # Q&A Mode
        print()
        print("=== Q&A Mode ===")
        print("You can now ask questions about meetings or manage tasks.")
        print("Type 'exit' to quit.")
        
        while True:
            question = self.ui.get_user_input("Ask a question about meetings (or 'exit'): ")
            
            if question.lower() == 'exit':
                break
            
            # Check if it's a task-related question
            if self.task_manager.is_task_related_question(question):
                self.task_manager.handle_task_creation(notes, new_page_id, title)
            else:
                # Regular Q&A
                all_notes = self._get_all_meeting_notes(past_meetings)
                answer = self.ai_client.answer_question(question, all_notes)
                print("Answer:")
                print(answer)
                print()
        
        print("Thank you for using Meeting Agent!")
    
    def _get_all_meeting_notes(self, past_meetings):
        """Get all notes from past meetings for Q&A"""
        all_notes = ""
        for meeting in past_meetings:
            meeting_notes = self.notion_client.get_full_notes(meeting['id'])
            all_notes += meeting_notes + "\n"
        return all_notes


def main():
    """Entry point for the application"""
    try:
        agent = MeetingAgent()
        agent.run()
    except KeyboardInterrupt:
        print("\nApplication interrupted by user.")
    except Exception as e:
        print(f"An error occurred: {e}")
        print("Please check your configuration and try again.")


if __name__ == "__main__":
    main()