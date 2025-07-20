"""
AI clients for text processing and analysis
"""

import json
from typing import List
from .config import OPENAI_CLIENT, ANTHROPIC_CLIENT


class AIClient:
    """Client for AI-powered text processing"""
    
    def __init__(self):
        self.openai_client = OPENAI_CLIENT
        self.anthropic_client = ANTHROPIC_CLIENT
    
    def summarize_transcript(self, transcript: str) -> str:
        """Use ChatGPT to turn transcript into structured notes"""
        system_prompt = (
            "Summarize the meeting transcript into structured notes. "
            "Use # for main title like Meeting Notes: Date. "
            "Use ## for sections like Attendees, Key Points, Decisions, Action Items. "
            "Use - for clean bullets without extra quotes, asterisks, or bold. "
            "List attendees as - Name (Role). "
            "For action items, use - Name: Task description. "
            "End with Meeting adjourned at time."
        )
        
        response = self.openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": transcript}
            ]
        )
        
        return response.choices[0].message.content
    
    def generate_brief_description(self, notes: str) -> str:
        """Generate a brief description from meeting notes"""
        response = self.openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system", 
                    "content": "Condense these notes into a 1-2 sentence brief description."
                },
                {"role": "user", "content": notes}
            ]
        )
        
        return response.choices[0].message.content
    
    def check_similarity(self, new_notes: str, past_meetings: List[dict], new_page_id: str) -> List[str]:
        """Check for similar meetings using Claude"""
        past_summaries = ""
        
        for meeting in past_meetings:
            past_id = meeting['id']
            if past_id == new_page_id:  # Skip self
                continue
            
            title = meeting['properties']['Title']['title'][0]['text']['content']
            
            # Get description safely
            desc = ''
            if 'Description' in meeting['properties'] and meeting['properties']['Description']['rich_text']:
                desc = meeting['properties']['Description']['rich_text'][0]['text']['content']
            
            # This would need to be passed from NotionClient
            full_notes = f"Title: {title}, Description: {desc}"
            past_summaries += f"ID: {past_id}, {full_notes}\n"
        
        if not past_summaries:
            return []
        
        system_prompt = (
            "Return only a JSON list of similar IDs, like [\"id1\", \"id2\"], or [] if none. "
            "Be sensitive to similarities in content, even if titles differ."
        )
        
        user_prompt = (
            f"Compare new notes to past meetings. "
            f"New: {new_notes}\n"
            f"Past: {past_summaries}"
        )
        
        try:
            response = self.anthropic_client.messages.create(
                model="claude-3-5-sonnet-20240620",
                max_tokens=200,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}]
            )
            
            response_text = response.content[0].text.strip()
            
            # Try to extract JSON from response
            import re
            json_match = re.search(r'\[.*?\]', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                similar_ids = json.loads(json_str)
                return similar_ids
            else:
                # Fallback: try parsing the entire response
                similar_ids = json.loads(response_text)
                return similar_ids
            
        except Exception as e:
            print(f"Claude similarity check error: {e}")
            return []
    
    def answer_question(self, question: str, all_notes: str) -> str:
        """Answer questions based on meeting notes"""
        system_prompt = (
            "Answer based on these meeting notes. "
            "If the question is about linking or grouping meetings, "
            "suggest similar meetings but do not attempt to modify the database."
        )
        
        user_prompt = f"Notes: {all_notes[:8000]}...\nQuestion: {question}"
        
        response = self.openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )
        
        return response.choices[0].message.content
    
    def suggest_tasks_from_meeting(self, notes: str, meeting_title: str) -> List[dict]:
        """Generate task suggestions based on meeting content"""
        system_prompt = (
            "Based on the meeting notes, suggest 3-5 relevant tasks that should be created. "
            "Return a JSON list of task objects with the following structure: "
            "{"
            "  \"title\": \"Task description\", "
            "  \"priority\": \"High|Medium|Low\", "
            "  \"suggested_due_date\": \"YYYY-MM-DD or relative like '1 week' or empty string\", "
            "  \"reason\": \"Why this task is needed based on the meeting\""
            "} "
            "Focus on follow-up actions, deliverables, preparations for next meeting, "
            "documentation needs, communication tasks, or process improvements mentioned. "
            "Only suggest realistic, actionable tasks that stem from the meeting content."
        )
        
        user_prompt = f"Meeting Title: {meeting_title}\n\nMeeting Notes:\n{notes}"
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            suggested_tasks = json.loads(response.choices[0].message.content)
            return suggested_tasks if isinstance(suggested_tasks, list) else []
            
        except Exception as e:
            print(f"Error generating task suggestions: {e}")
            return []