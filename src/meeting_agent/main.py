"""
Main entry point for Meeting Agent
"""

from datetime import datetime
from .config import validate_config
from .notion_client import NotionClient
from .ai_client import AIClient
from .ui import UserInterface
from .task_manager import TaskManager
from .memory_client import MemoryClient
from .queue_client import AsyncProcessingMixin
from .chunking import TranscriptChunker
import os
import time


class MeetingAgent(AsyncProcessingMixin):
    """Main Meeting Agent application with async processing capabilities"""
    
    def __init__(self):
        # Validate configuration
        validate_config()
        
        # Initialize components
        self.notion_client = NotionClient()
        self.ai_client = AIClient()
        self.ui = UserInterface()
        self.memory_client = MemoryClient()
        self.task_manager = TaskManager(self.notion_client, self.ai_client, self.ui, self.memory_client)
        self.chunker = TranscriptChunker()
        
        # Initialize async processing
        super().__init__()
        self.enable_async = os.getenv('ENABLE_ASYNC_PROCESSING', 'false').lower() == 'true'
    
    def run(self):
        """Main application loop"""
        print("=== Meeting Agent ===")
        print("AI-powered meeting transcription and task management")
        
        # Display memory status
        if self.memory_client.is_enabled():
            print("🧠 Memory: Enabled")
        else:
            print("🧠 Memory: Disabled (add MEM0_API_KEY to enable)")
        print()
        
        # Get meeting input
        transcript = self.ui.get_user_input("Paste meeting transcript: ")
        title = self.ui.get_user_input("Meeting title: ")
        date = datetime.now().isoformat()[:10]
        
        # Check transcript size and processing mode
        transcript_size = len(transcript)
        should_chunk = self.chunker.should_chunk(transcript)
        
        if should_chunk:
            print(f"\n📊 Large transcript detected ({transcript_size:,} characters)")
            print(f"🔄 Estimated speakers: {self.chunker._count_speakers(transcript)}")
            print(f"📝 Estimated processing time: {self._estimate_processing_time(transcript_size)} seconds")
        
        # Process transcript (sync or async)
        if self.enable_async and should_chunk:
            notes, brief_desc = self._process_transcript_async(transcript, title, date)
        else:
            print("\nProcessing transcript...")
            notes, brief_desc = self._process_transcript_sync(transcript)
        
        print("\nGenerated Brief Description:")
        print(brief_desc)
        print()
        print("Generated Notes:")
        print(notes)
        print()
        
        # Create Notion page
        print("\nCreating Notion page...")
        new_page_id = self.notion_client.create_meeting_page(title, date, brief_desc)
        self.notion_client.append_notes_to_page(new_page_id, notes)
        print(f"✓ Created Notion page: {new_page_id}")
        
        # Update meeting fields
        print("\nUpdating meeting fields...")
        meeting_type = self.ui.prompt_for_select(self.notion_client, 'Meeting Type')
        tags = self.ui.prompt_for_select(self.notion_client, 'Topics', multi=True)
        status = self.ui.prompt_for_select(self.notion_client, 'Status')
        
        self.notion_client.update_meeting_fields(new_page_id, meeting_type, tags, status)
        print("✓ Updated meeting fields")
        
        # Store meeting in memory for future context
        if self.memory_client.is_enabled():
            print("\nStoring meeting in memory...")
            # Extract action items for memory storage
            action_items = self.task_manager.parse_action_items_from_notes(notes)
            
            meeting_data = {
                'id': new_page_id,
                'title': title,
                'date': date,
                'meeting_type': meeting_type,
                'topics': tags,
                'status': status,
                'action_items': action_items,
                'notes': notes,
                'brief_description': brief_desc
            }
            
            self.memory_client.store_meeting_memory(meeting_data)
            print("✓ Meeting stored in memory")
        
        # Check for similar meetings
        print("\nChecking for similar meetings...")
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
                            print(f"\nFull notes for {detail_id}:")
                            print(full_notes)
                            print()
                        else:
                            print("ID not in suggestions.")
                    except IndexError:
                        print("Invalid ID format. Use 'details <id>'")
                elif action == 'cancel':
                    print("Grouping cancelled.")
                    break
        else:
            print("No similar meetings found.")
        
        # Task suggestion after meeting creation
        print("\n=== Task Management ===")
        should_suggest_tasks = self.ui.ask_to_add_tasks()
        if should_suggest_tasks:
            self.task_manager.suggest_and_create_tasks(notes, new_page_id, title)
        
        # Q&A Mode
        print()
        print("=== Q&A Mode ===")
        print("You can now ask questions about meetings or manage tasks.")
        print("Type 'exit' to quit.")
        if self.memory_client.is_enabled():
            print("Type 'memory stats' to see memory information.")
        print("Type 'rate limits' to check API quota status.")
        
        while True:
            question = self.ui.get_user_input("Ask a question about meetings (or 'exit'): ")
            
            if question.lower() == 'exit':
                break
            
            # Check for memory stats command
            if question.lower() == 'memory stats' and self.memory_client.is_enabled():
                stats = self.memory_client.get_memory_stats()
                print("\nMemory Statistics:")
                print(f"- Total memories: {stats.get('total_memories', 0)}")
                print("- Categories:")
                for category, count in stats.get('categories', {}).items():
                    print(f"  • {category}: {count}")
                print()
                continue
            
            # Check for rate limits command
            if question.lower() == 'rate limits':
                self._display_rate_limit_status()
                continue
            
            # Check if it's a task-related question
            if self.task_manager.is_task_related_question(question):
                self.task_manager.handle_task_creation(notes, new_page_id, title, question)
            else:
                # Regular Q&A with memory enhancement
                all_notes = self._get_all_meeting_notes(past_meetings)
                
                # Get relevant context from memory if available
                memory_context = ""
                if self.memory_client.is_enabled():
                    relevant_memories = self.memory_client.get_relevant_context(question, limit=3)
                    if relevant_memories:
                        memory_context = "\n\nRelevant context from memory:\n"
                        for memory in relevant_memories:
                            memory_context += f"- {memory.get('text', '')}\n"
                
                enhanced_context = all_notes + memory_context
                answer = self.ai_client.answer_question(question, enhanced_context)
                print("\nAnswer:")
                print(answer)
                print()
                
                # Store this interaction in memory for learning
                if self.memory_client.is_enabled():
                    interaction_data = {
                        'question': question,
                        'answer': answer,
                        'context': 'q_and_a',
                        'successful_action': 'answered_question'
                    }
                    self.memory_client.learn_from_interaction(interaction_data)
        
        print("\nThank you for using Meeting Agent!")
    
    def _process_transcript_sync(self, transcript: str) -> tuple:
        """Process transcript synchronously (original method)"""
        notes = self.ai_client.summarize_transcript(transcript)
        brief_desc = self.ai_client.generate_brief_description(notes)
        return notes, brief_desc
    
    def _process_transcript_async(self, transcript: str, title: str, date: str) -> tuple:
        """Process transcript asynchronously using worker queue"""
        print("\n🚀 Submitting transcript for async processing...")
        
        meeting_data = {
            'title': title,
            'date': date
        }
        
        # Submit job to queue
        job_id = self.submit_transcript_processing(transcript, meeting_data)
        print(f"📋 Job ID: {job_id}")
        
        # Poll for completion with progress updates
        print("⏳ Waiting for processing to complete...")
        start_time = time.time()
        
        while True:
            progress = self.check_job_progress(job_id)
            print(f"\r{progress['message']}", end='', flush=True)
            
            if progress['status'] in ['completed', 'failed']:
                print()  # New line
                break
            
            time.sleep(2)
        
        if progress['status'] == 'failed':
            print("❌ Async processing failed, falling back to sync processing...")
            return self._process_transcript_sync(transcript)
        
        # Get results
        result = self.queue_client.get_job_result(job_id)
        processing_time = time.time() - start_time
        
        print(f"✅ Async processing completed in {processing_time:.1f} seconds")
        if result.get('chunked'):
            print(f"📄 Processed as {result['chunk_count']} chunks")
        
        return result['notes'], result['brief_description']
    
    def _estimate_processing_time(self, transcript_size: int) -> int:
        """Estimate processing time based on transcript size"""
        # Rough estimates: ~1 second per 1000 characters
        base_time = transcript_size // 1000
        return max(10, min(base_time, 180))  # Between 10 and 180 seconds
    
    def _display_rate_limit_status(self):
        """Display current rate limit status"""
        status = self.ai_client.get_rate_limit_status()
        
        print("\n🔄 API Rate Limit Status:")
        
        for provider_name, provider_status in status.items():
            print(f"\n📡 {provider_name.upper()}:")
            print(f"  Recent requests: {provider_status['requests_last_minute']}/min")
            
            if provider_status['limit_requests']:
                remaining_pct = (provider_status['remaining_requests'] / provider_status['limit_requests']) * 100
                status_emoji = "🟢" if remaining_pct > 50 else "🟡" if remaining_pct > 20 else "🔴"
                print(f"  Request quota: {status_emoji} {provider_status['remaining_requests']}/{provider_status['limit_requests']} ({remaining_pct:.1f}%)")
            
            if provider_status['limit_tokens']:
                remaining_pct = (provider_status['remaining_tokens'] / provider_status['limit_tokens']) * 100
                status_emoji = "🟢" if remaining_pct > 50 else "🟡" if remaining_pct > 20 else "🔴"
                print(f"  Token quota: {status_emoji} {provider_status['remaining_tokens']:,}/{provider_status['limit_tokens']:,} ({remaining_pct:.1f}%)")
            
            if provider_status['queue_size'] > 0:
                print(f"  Queued requests: ⏳ {provider_status['queue_size']}")
            
            if provider_status['backoff_until'] > time.time():
                wait_time = provider_status['backoff_until'] - time.time()
                print(f"  Backoff status: ⏸️ {wait_time:.1f}s remaining")
            else:
                print(f"  Status: ✅ Ready")
        
        # Process any queued requests
        processed = self.ai_client.process_queued_requests(5)
        total_processed = processed['openai_processed'] + processed['anthropic_processed']
        
        if total_processed > 0:
            print(f"\n✅ Processed {total_processed} queued requests")
        
        print()
    
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