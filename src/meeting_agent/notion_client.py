"""
Notion API client for handling database operations
"""

import requests
import json
from typing import List, Dict, Optional
from .config import NOTION_HEADERS, DATABASE_ID, TASKS_DATABASE_ID, DEFAULT_ASSIGNEE


class NotionClient:
    """Client for interacting with Notion API"""
    
    def __init__(self):
        self.headers = NOTION_HEADERS
        self.database_id = DATABASE_ID
        self.tasks_database_id = TASKS_DATABASE_ID
    
    def get_database_properties(self, database_id: str = None) -> Dict:
        """Get properties of a Notion database"""
        db_id = database_id or self.database_id
        response = requests.get(
            f"https://api.notion.com/v1/databases/{db_id}", 
            headers=self.headers
        )
        
        if response.status_code == 200:
            return response.json()["properties"]
        else:
            raise ValueError(f"Error fetching DB properties: {response.text}")
    
    def get_select_options(self, property_name: str) -> List[str]:
        """Get select options for a property"""
        props = self.get_database_properties()
        
        if property_name in props:
            prop = props[property_name]
            if prop['type'] in ['select', 'multi_select']:
                return [opt['name'] for opt in prop[prop['type']]['options']]
        
        return []
    
    def get_available_status_options(self) -> List[str]:
        """Get available status options from tasks database"""
        props = self.get_database_properties(self.tasks_database_id)
        
        if "Status" in props:
            status_prop = props["Status"]
            if status_prop["type"] == "status":
                return [opt["name"] for opt in status_prop["status"]["options"]]
            elif status_prop["type"] == "select":
                return [opt["name"] for opt in status_prop["select"]["options"]]
        
        return []
    
    def create_meeting_page(self, title: str, date: str, description: str) -> str:
        """Create a new meeting page in Notion"""
        data = {
            "parent": {"database_id": self.database_id},
            "properties": {
                "Title": {"title": [{"text": {"content": title}}]},
                "Date": {"date": {"start": date}},
                "Description": {"rich_text": [{"text": {"content": description}}]},
                "Linked Meetings": {"relation": []}
            }
        }
        
        response = requests.post(
            "https://api.notion.com/v1/pages", 
            headers=self.headers, 
            json=data
        )
        
        if response.status_code == 200:
            return response.json()["id"]
        else:
            raise ValueError(f"Error creating page: {response.text}")
    
    def append_notes_to_page(self, page_id: str, notes: str) -> None:
        """Append formatted notes to a Notion page"""
        blocks = self._parse_notes_to_blocks(notes)
        data = {"children": blocks}
        
        response = requests.patch(
            f"https://api.notion.com/v1/blocks/{page_id}/children", 
            headers=self.headers, 
            json=data
        )
        
        if response.status_code != 200:
            raise ValueError(f"Error appending blocks: {response.text}")
    
    def create_task_page(self, task_desc: str, assignee_name: str, due_date: Optional[str], meeting_id: str, priority: Optional[str] = None) -> str:
        """Create a new task page in Notion"""
        # Get available status options and choose appropriate one
        available_statuses = self.get_available_status_options()
        default_status = self._choose_default_status(available_statuses)
        
        properties = {
            "Title": {"title": [{"text": {"content": task_desc}}]},
            "Assignee": {"multi_select": [{"name": assignee_name}]},
            "Status": {"status": {"name": default_status}},
            "Linked Meeting": {"relation": [{"id": meeting_id}]}
        }
        
        # Only add due date if provided
        if due_date:
            properties["Due Date"] = {"date": {"start": due_date}}
        
        # Only add priority if provided
        if priority:
            properties["Priority"] = {"select": {"name": priority}}
        
        data = {
            "parent": {"database_id": self.tasks_database_id},
            "properties": properties
        }
        
        response = requests.post(
            "https://api.notion.com/v1/pages", 
            headers=self.headers, 
            json=data
        )
        
        if response.status_code == 200:
            return response.json()["id"]
        else:
            raise ValueError(f"Error creating task: {response.text}")
    
    def link_actions_to_meeting(self, meeting_id: str, task_ids: List[str]) -> None:
        """Link action items (tasks) to a meeting"""
        # Get current relations
        current_page = requests.get(
            f"https://api.notion.com/v1/pages/{meeting_id}", 
            headers=self.headers
        ).json()
        
        # Check if Action Items property exists and get current relations
        try:
            current_relations = current_page['properties']['Action Items']['relation']
        except KeyError:
            # If Action Items property doesn't exist, start with empty relations
            current_relations = []
        
        updated_relations = current_relations + [{"id": task_id} for task_id in task_ids]
        
        patch_data = {
            "properties": {
                "Action Items": {"relation": updated_relations}
            }
        }
        
        response = requests.patch(
            f"https://api.notion.com/v1/pages/{meeting_id}", 
            headers=self.headers, 
            json=patch_data
        )
        
        if response.status_code != 200:
            raise ValueError(f"Error linking tasks: {response.text}")
    
    def query_past_meetings(self) -> List[Dict]:
        """Query past meetings from the database"""
        data = {"page_size": 100}
        response = requests.post(
            f"https://api.notion.com/v1/databases/{self.database_id}/query", 
            headers=self.headers, 
            json=data
        )
        
        if response.status_code == 200:
            return response.json()["results"]
        else:
            return []
    
    def get_full_notes(self, page_id: str) -> str:
        """Get full notes content from a page"""
        all_notes = ""
        blocks_response = requests.get(
            f"https://api.notion.com/v1/blocks/{page_id}/children?page_size=100", 
            headers=self.headers
        )
        
        if blocks_response.status_code == 200:
            blocks = blocks_response.json().get('results', [])
            for block in blocks:
                block_type = block['type']
                if 'rich_text' in block.get(block_type, {}):
                    text_parts = [
                        rt.get('text', {}).get('content', '') 
                        for rt in block[block_type]['rich_text']
                    ]
                    all_notes += " ".join(text_parts) + "\n"
        
        return all_notes
    
    def get_meeting_details(self, page_id: str) -> Dict:
        """Get meeting details from a page"""
        page_response = requests.get(
            f"https://api.notion.com/v1/pages/{page_id}", 
            headers=self.headers
        )
        
        if page_response.status_code == 200:
            props = page_response.json()['properties']
            title = props['Title']['title'][0]['text']['content']
            
            # Handle different date property types
            date_prop = props.get('Date', {})
            if date_prop.get('type') == 'date':
                date = date_prop.get('date', {}).get('start', 'Unknown')
            elif date_prop.get('type') == 'created_time':
                date = date_prop.get('created_time', 'Unknown')
            else:
                date = 'Unknown'
            
            # Get description
            desc_prop = props.get('Description', {})
            desc = 'No description'
            if desc_prop.get('rich_text'):
                desc = desc_prop['rich_text'][0]['text']['content']
            
            return {
                "id": page_id, 
                "title": title, 
                "date": date, 
                "description": desc
            }
        
        return {
            "id": page_id, 
            "title": "Unknown", 
            "date": "Unknown", 
            "description": "Unknown"
        }
    
    def update_meeting_fields(self, page_id: str, meeting_type: str, tags: List[str], status: str) -> None:
        """Update meeting fields like type, topics, and status"""
        patch_data = {
            "properties": {
                "Meeting Type": {"select": {"name": meeting_type}} if meeting_type else {"select": None},
                "Topics": {"multi_select": [{"name": tag.strip()} for tag in tags if tag.strip()]},
                "Status": {"select": {"name": status}} if status else {"select": {"name": "Open"}}
            }
        }
        
        response = requests.patch(
            f"https://api.notion.com/v1/pages/{page_id}", 
            headers=self.headers, 
            json=patch_data
        )
        
        if response.status_code != 200:
            raise ValueError(f"Error updating fields: {response.text}")
    
    def link_meetings(self, new_page_id: str, similar_ids: List[str]) -> None:
        """Link similar meetings together"""
        for sim_id in similar_ids:
            # Link new page to similar page
            current_relations_new = requests.get(
                f"https://api.notion.com/v1/pages/{new_page_id}", 
                headers=self.headers
            ).json()['properties']['Linked Meetings']['relation']
            
            updated_relations_new = current_relations_new + [{"id": sim_id}]
            patch_data = {"properties": {"Linked Meetings": {"relation": updated_relations_new}}}
            requests.patch(
                f"https://api.notion.com/v1/pages/{new_page_id}", 
                headers=self.headers, 
                json=patch_data
            )
            
            # Link similar page to new page
            current_relations_sim = requests.get(
                f"https://api.notion.com/v1/pages/{sim_id}", 
                headers=self.headers
            ).json()['properties']['Linked Meetings']['relation']
            
            updated_relations_sim = current_relations_sim + [{"id": new_page_id}]
            patch_data = {"properties": {"Linked Meetings": {"relation": updated_relations_sim}}}
            requests.patch(
                f"https://api.notion.com/v1/pages/{sim_id}", 
                headers=self.headers, 
                json=patch_data
            )
    
    def _parse_notes_to_blocks(self, notes: str) -> List[Dict]:
        """Parse notes text into Notion blocks"""
        # Strip any unwanted formatting
        notes = notes.replace('**', '').replace('*', '')
        blocks = []
        lines = notes.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if line.startswith('### '):
                blocks.append({
                    "object": "block", 
                    "type": "heading_3", 
                    "heading_3": {"rich_text": [{"type": "text", "text": {"content": line[4:]}}]}
                })
            elif line.startswith('## '):
                blocks.append({
                    "object": "block", 
                    "type": "heading_2", 
                    "heading_2": {"rich_text": [{"type": "text", "text": {"content": line[3:]}}]}
                })
            elif line.startswith('# '):
                blocks.append({
                    "object": "block", 
                    "type": "heading_1", 
                    "heading_1": {"rich_text": [{"type": "text", "text": {"content": line[2:]}}]}
                })
            elif line.startswith('- '):
                blocks.append({
                    "object": "block", 
                    "type": "bulleted_list_item", 
                    "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": line[2:]}}]}
                })
            else:
                blocks.append({
                    "object": "block", 
                    "type": "paragraph", 
                    "paragraph": {"rich_text": [{"type": "text", "text": {"content": line}}]}
                })
        
        return blocks
    
    def _choose_default_status(self, available_statuses: List[str]) -> str:
        """Choose the best default status from available options"""
        preferred_statuses = ["To Do", "Not Started", "Todo", "Open", "New", "Pending"]
        
        for preferred in preferred_statuses:
            if preferred in available_statuses:
                return preferred
        
        if available_statuses:
            return available_statuses[0]  # Use first available option
        
        return "To Do"  # Fallback, will create new option if needed