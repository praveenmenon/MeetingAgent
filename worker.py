"""
Async worker for processing meeting transcripts
"""

import asyncio
import json
import traceback
from typing import Dict, Any, List
import redis
from src.meeting_agent.ai_client import AIClient
from src.meeting_agent.notion_client import NotionClient
from src.meeting_agent.memory_client import MemoryClient
from src.meeting_agent.chunking import TranscriptChunker
from src.meeting_agent.queue_client import QueueClient, JobStatus
from src.meeting_agent.ai_config import get_ai_config, TaskType
from src.meeting_agent.rate_limiter import get_rate_limiter, APIProvider


class MeetingWorker:
    """Async worker for processing meeting transcripts"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.queue_client = QueueClient(redis_url)
        self.ai_client = AIClient()
        self.notion_client = NotionClient()
        self.memory_client = MemoryClient()
        self.chunker = TranscriptChunker()
        self.ai_config = get_ai_config()
        
        self.redis = redis.from_url(redis_url, decode_responses=True)
        self.job_queue = "meeting_jobs"
        
        # Job handlers
        self.handlers = {
            "process_transcript": self.process_transcript,
            "process_chunks": self.process_chunks,
            "similarity_check": self.similarity_check,
            "task_generation": self.task_generation
        }
    
    async def start_worker(self):
        """Start the worker loop"""
        print("🚀 Meeting Agent Worker started")
        print("Waiting for jobs...")
        
        while True:
            try:
                # Blocking pop from queue (with timeout)
                job_data = self.redis.brpop(self.job_queue, timeout=5)
                
                if job_data:
                    _, job_json = job_data
                    job = json.loads(job_json)
                    
                    print(f"📋 Processing job {job['id']} ({job['type']})")
                    await self.process_job(job)
                    
            except KeyboardInterrupt:
                print("\n🛑 Worker stopped by user")
                break
            except Exception as e:
                print(f"❌ Worker error: {e}")
                traceback.print_exc()
                await asyncio.sleep(1)
    
    async def process_job(self, job: Dict[str, Any]):
        """Process a single job"""
        job_id = job['id']
        job_type = job['type']
        job_data = job['data']
        
        try:
            # Update status to processing
            self.queue_client.update_job_status(job_id, JobStatus.PROCESSING)
            
            # Get handler
            handler = self.handlers.get(job_type)
            if not handler:
                raise ValueError(f"Unknown job type: {job_type}")
            
            # Execute handler
            result = await handler(job_data)
            
            # Update status to completed
            self.queue_client.update_job_status(job_id, JobStatus.COMPLETED, result)
            print(f"✅ Completed job {job_id}")
            
        except Exception as e:
            error_result = {
                "error": str(e),
                "traceback": traceback.format_exc()
            }
            self.queue_client.update_job_status(job_id, JobStatus.FAILED, error_result)
            print(f"❌ Failed job {job_id}: {e}")
    
    async def process_transcript(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a full transcript"""
        transcript = data['transcript']
        meeting_data = data['meeting_data']
        
        # Check if chunking is needed
        if self.chunker.should_chunk(transcript):
            print(f"📄 Large transcript detected, chunking...")
            return await self.process_large_transcript(transcript, meeting_data)
        else:
            print(f"📄 Processing standard transcript...")
            return await self.process_standard_transcript(transcript, meeting_data)
    
    async def process_standard_transcript(self, transcript: str, meeting_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a standard-sized transcript"""
        # Generate notes
        notes = self.ai_client.summarize_transcript(transcript)
        brief_desc = self.ai_client.generate_brief_description(notes)
        
        return {
            "type": "standard",
            "notes": notes,
            "brief_description": brief_desc,
            "chunked": False
        }
    
    async def process_large_transcript(self, transcript: str, meeting_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a large transcript using chunking"""
        # Chunk the transcript
        chunks = self.chunker.chunk_by_speakers(transcript)
        print(f"📄 Created {len(chunks)} chunks")
        
        # Process each chunk
        chunk_summaries = []
        for i, chunk in enumerate(chunks):
            print(f"🔄 Processing chunk {i+1}/{len(chunks)}")
            
            chunk_notes = self.ai_client.summarize_transcript(chunk['text'])
            chunk_summaries.append({
                'id': chunk['id'],
                'notes': chunk_notes,
                'metadata': {
                    'size': chunk['size'],
                    'speaker_count': chunk.get('speaker_count', 0)
                }
            })
        
        # Combine chunk summaries into final notes
        combined_notes = await self.combine_chunk_summaries(chunk_summaries)
        brief_desc = self.ai_client.generate_brief_description(combined_notes)
        
        return {
            "type": "chunked",
            "notes": combined_notes,
            "brief_description": brief_desc,
            "chunked": True,
            "chunk_count": len(chunks),
            "chunk_summaries": chunk_summaries
        }
    
    async def combine_chunk_summaries(self, chunk_summaries: List[Dict[str, Any]]) -> str:
        """Combine multiple chunk summaries into coherent notes"""
        combined_text = "\n\n".join([
            f"## Segment {summary['id']}\n{summary['notes']}" 
            for summary in chunk_summaries
        ])
        
        # Use AI to create coherent combined summary with optimized parameters
        system_prompt = (
            "Combine these meeting segment summaries into a single, coherent set of meeting notes. "
            "Merge duplicate information, organize chronologically, and maintain all important details. "
            "Use standard meeting note format with sections like Attendees, Key Points, Decisions, Action Items."
        )
        
        # Get optimized parameters for chunk combination
        api_params = self.ai_config.get_openai_params(TaskType.CHUNK_COMBINATION)
        
        # Use rate limiter for the request
        rate_limiter = get_rate_limiter()
        response = rate_limiter.execute_with_retry_sync(
            APIProvider.OPENAI,
            self.ai_client.openai_client.chat.completions.create,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": combined_text}
            ],
            **api_params
        )
        
        return response.choices[0].message.content
    
    async def process_chunks(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process pre-chunked transcript data"""
        chunks = data['chunks']
        meeting_data = data['meeting_data']
        
        # Process each chunk
        chunk_summaries = []
        for chunk in chunks:
            notes = self.ai_client.summarize_transcript(chunk['text'])
            chunk_summaries.append({
                'id': chunk['id'],
                'notes': notes,
                'metadata': chunk.get('metadata', {})
            })
        
        # Combine summaries
        combined_notes = await self.combine_chunk_summaries(chunk_summaries)
        brief_desc = self.ai_client.generate_brief_description(combined_notes)
        
        return {
            "type": "pre_chunked",
            "notes": combined_notes,
            "brief_description": brief_desc,
            "chunk_summaries": chunk_summaries
        }
    
    async def similarity_check(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Async similarity checking"""
        notes = data['notes']
        past_meetings = data['past_meetings']
        new_page_id = data['new_page_id']
        
        similar_ids = self.ai_client.check_similarity(notes, past_meetings, new_page_id)
        
        return {
            "similar_ids": similar_ids,
            "count": len(similar_ids)
        }
    
    async def task_generation(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Async task generation"""
        notes = data['notes']
        meeting_title = data['meeting_title']
        
        suggested_tasks = self.ai_client.suggest_tasks_from_meeting(notes, meeting_title)
        
        return {
            "suggested_tasks": suggested_tasks,
            "count": len(suggested_tasks)
        }


async def main():
    """Main worker entry point"""
    worker = MeetingWorker()
    await worker.start_worker()


if __name__ == "__main__":
    asyncio.run(main())