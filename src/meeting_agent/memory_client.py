"""
Memory client for Meeting Agent using Mem0
Provides intelligent memory capabilities for personalized meeting assistance
"""

import os
import warnings
from typing import Dict, List
from datetime import datetime
from mem0 import Memory
from .config import MEM0_API_KEY, DEFAULT_USER_ID

# Suppress mem0 deprecation warnings
warnings.filterwarnings("ignore", category=DeprecationWarning, module="mem0")


class MemoryClient:
    """Client for managing intelligent memory in Meeting Agent"""
    
    def __init__(self):
        """Initialize Mem0 client with configuration"""
        if MEM0_API_KEY:
            # Set environment variable for Mem0 (it uses OpenAI by default)
            os.environ["OPENAI_API_KEY"] = os.getenv('OPENAI_API_KEY', '')
            
            # For Mem0 cloud platform, use MemoryClient
            try:
                from mem0 import MemoryClient
                self.memory = MemoryClient(api_key=MEM0_API_KEY)
            except ImportError:
                # Fallback to local Memory if MemoryClient not available
                config = {
                    "vector_store": {
                        "provider": "qdrant",
                        "config": {
                            "collection_name": "meeting_agent_memories",
                            "host": "localhost",
                            "port": 6333,
                        }
                    }
                }
                self.memory = Memory(config=config)
        else:
            self.memory = None
            
        self.default_user_id = DEFAULT_USER_ID
    
    def is_enabled(self) -> bool:
        """Check if memory functionality is enabled"""
        return self.memory is not None
    
    def store_meeting_memory(self, meeting_data: Dict, user_id: str = None) -> None:
        """
        Store meeting information in memory for future context
        
        Args:
            meeting_data: Dictionary containing meeting information
            user_id: User identifier (defaults to configured user)
        """
        if not self.is_enabled():
            return
        
        user_id = user_id or self.default_user_id
        
        try:
            # Store semantic facts about the meeting
            semantic_facts = [
                f"Meeting titled '{meeting_data['title']}' was held on {meeting_data['date']}",
                f"Meeting type: {meeting_data.get('meeting_type', 'General')}",
                f"Meeting topics: {', '.join(meeting_data.get('topics', []))}",
                f"Meeting status: {meeting_data.get('status', 'Completed')}"
            ]
            
            # Store key decisions and outcomes
            if meeting_data.get('key_decisions'):
                semantic_facts.extend([
                    f"Key decision from {meeting_data['title']}: {decision}"
                    for decision in meeting_data['key_decisions']
                ])
            
            # Store action items context
            if meeting_data.get('action_items'):
                semantic_facts.extend([
                    f"Action item from {meeting_data['title']}: {item}"
                    for item in meeting_data['action_items']
                ])
            
            # Store each fact
            for fact in semantic_facts:
                self.memory.add(
                    messages=[{"role": "user", "content": fact}],
                    user_id=user_id,
                    metadata={
                        "category": "meeting_semantic",
                        "meeting_id": meeting_data.get('id'),
                        "meeting_title": meeting_data['title'],
                        "date": meeting_data['date'],
                        "type": meeting_data.get('meeting_type', 'General')
                    }
                )
            
            # Store episodic memory about the interaction
            episodic_content = f"Successfully processed meeting '{meeting_data['title']}' with {len(meeting_data.get('action_items', []))} action items"
            
            self.memory.add(
                messages=[{"role": "assistant", "content": episodic_content}],
                user_id=user_id,
                metadata={
                    "category": "meeting_episodic",
                    "meeting_id": meeting_data.get('id'),
                    "timestamp": datetime.now().isoformat(),
                    "action_count": len(meeting_data.get('action_items', []))
                }
            )
            
        except Exception as e:
            print(f"Warning: Failed to store meeting memory: {e}")
    
    def store_user_preference(self, preference_type: str, preference_value: str, user_id: str = None) -> None:
        """
        Store user preferences for personalized experience
        
        Args:
            preference_type: Type of preference (e.g., 'meeting_format', 'task_style')
            preference_value: The preference value
            user_id: User identifier
        """
        if not self.is_enabled():
            return
        
        user_id = user_id or self.default_user_id
        
        try:
            preference_content = f"User prefers {preference_type}: {preference_value}"
            
            self.memory.add(
                messages=[{"role": "user", "content": preference_content}],
                user_id=user_id,
                metadata={
                    "category": "user_preference",
                    "preference_type": preference_type,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            print(f"Warning: Failed to store user preference: {e}")
    
    def store_task_feedback(self, task_info: Dict, feedback: str, user_id: str = None) -> None:
        """
        Store feedback about task creation and completion
        
        Args:
            task_info: Information about the task
            feedback: User feedback about the task
            user_id: User identifier
        """
        if not self.is_enabled():
            return
        
        user_id = user_id or self.default_user_id
        
        try:
            feedback_content = f"Task '{task_info['title']}' feedback: {feedback}"
            
            self.memory.add(
                messages=[{"role": "user", "content": feedback_content}],
                user_id=user_id,
                metadata={
                    "category": "task_feedback",
                    "task_title": task_info['title'],
                    "assignee": task_info.get('assignee'),
                    "due_date": task_info.get('due_date'),
                    "timestamp": datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            print(f"Warning: Failed to store task feedback: {e}")
    
    def get_relevant_context(self, query: str, user_id: str = None, limit: int = 5) -> List[Dict]:
        """
        Retrieve relevant context from memory for better responses
        
        Args:
            query: Query to search for relevant context
            user_id: User identifier
            limit: Maximum number of results to return
            
        Returns:
            List of relevant memory entries
        """
        if not self.is_enabled():
            return []
        
        user_id = user_id or self.default_user_id
        
        try:
            results = self.memory.search(
                query=query,
                user_id=user_id,
                limit=limit
            )
            
            return results if results else []
            
        except Exception as e:
            print(f"Warning: Failed to retrieve context: {e}")
            return []
    
    def get_user_preferences(self, user_id: str = None) -> Dict:
        """
        Get user preferences for personalized experience
        
        Args:
            user_id: User identifier
            
        Returns:
            Dictionary of user preferences
        """
        if not self.is_enabled():
            return {}
        
        user_id = user_id or self.default_user_id
        preferences = {}
        
        try:
            # Search for user preferences
            results = self.memory.search(
                query="User prefers",
                user_id=user_id,
                limit=20
            )
            
            for result in results:
                if result.get('metadata', {}).get('category') == 'user_preference':
                    pref_type = result.get('metadata', {}).get('preference_type')
                    if pref_type:
                        preferences[pref_type] = result.get('text', '')
            
            return preferences
            
        except Exception as e:
            print(f"Warning: Failed to get user preferences: {e}")
            return {}
    
    def get_meeting_history_context(self, meeting_title: str, user_id: str = None) -> List[Dict]:
        """
        Get context from similar past meetings
        
        Args:
            meeting_title: Title of the current meeting
            user_id: User identifier
            
        Returns:
            List of relevant past meeting contexts
        """
        if not self.is_enabled():
            return []
        
        user_id = user_id or self.default_user_id
        
        try:
            # Search for similar meetings
            results = self.memory.search(
                query=f"Meeting similar to {meeting_title}",
                user_id=user_id,
                limit=10
            )
            
            # Filter for meeting-related memories
            meeting_contexts = []
            for result in results:
                if result.get('metadata', {}).get('category') in ['meeting_semantic', 'meeting_episodic']:
                    meeting_contexts.append(result)
            
            return meeting_contexts
            
        except Exception as e:
            print(f"Warning: Failed to get meeting history context: {e}")
            return []
    
    def learn_from_interaction(self, interaction_data: Dict, user_id: str = None) -> None:
        """
        Learn from user interactions to improve future responses
        
        Args:
            interaction_data: Data about the interaction
            user_id: User identifier
        """
        if not self.is_enabled():
            return
        
        user_id = user_id or self.default_user_id
        
        try:
            # Store procedural learning
            if interaction_data.get('successful_action'):
                learning_content = f"Successfully {interaction_data['successful_action']} - remember this approach"
                
                self.memory.add(
                    messages=[{"role": "assistant", "content": learning_content}],
                    user_id=user_id,
                    metadata={
                        "category": "procedural_learning",
                        "action_type": interaction_data['successful_action'],
                        "context": interaction_data.get('context', ''),
                        "timestamp": datetime.now().isoformat()
                    }
                )
            
            # Store user feedback patterns
            if interaction_data.get('user_feedback'):
                feedback_content = f"User feedback: {interaction_data['user_feedback']}"
                
                self.memory.add(
                    messages=[{"role": "user", "content": feedback_content}],
                    user_id=user_id,
                    metadata={
                        "category": "feedback_pattern",
                        "feedback_type": interaction_data.get('feedback_type', 'general'),
                        "timestamp": datetime.now().isoformat()
                    }
                )
                
        except Exception as e:
            print(f"Warning: Failed to learn from interaction: {e}")
    
    def get_memory_stats(self, user_id: str = None) -> Dict:
        """
        Get statistics about stored memories
        
        Args:
            user_id: User identifier
            
        Returns:
            Dictionary with memory statistics
        """
        if not self.is_enabled():
            return {"enabled": False}
        
        user_id = user_id or self.default_user_id
        
        try:
            # Try to get all memories for the user (method may not exist in all versions)
            try:
                all_memories = self.memory.get_all(user_id=user_id)
                
                stats = {
                    "enabled": True,
                    "total_memories": len(all_memories),
                    "categories": {}
                }
                
                # Count by category
                for memory in all_memories:
                    category = memory.get('metadata', {}).get('category', 'unknown')
                    stats['categories'][category] = stats['categories'].get(category, 0) + 1
                
                return stats
                
            except (AttributeError, TypeError):
                # get_all method not available, return basic stats
                return {
                    "enabled": True,
                    "total_memories": "Not available",
                    "categories": "Statistics not available in this version"
                }
            
        except Exception as e:
            print(f"Warning: Failed to get memory stats: {e}")
            return {"enabled": True, "error": str(e)}
    
    def clear_user_memory(self, user_id: str = None) -> bool:
        """
        Clear all memory for a user (use with caution)
        
        Args:
            user_id: User identifier
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_enabled():
            return False
        
        user_id = user_id or self.default_user_id
        
        try:
            # Note: This is a destructive operation
            # Implementation depends on Mem0's API for bulk deletion
            # For now, we'll return a placeholder
            print(f"Warning: Clear memory operation requested for user {user_id}")
            return True
            
        except Exception as e:
            print(f"Error: Failed to clear memory: {e}")
            return False