"""
Queue client for async processing
"""

import asyncio
import json
import uuid
from typing import Dict, Any, Optional
from datetime import datetime
import redis
from enum import Enum


class JobStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class QueueClient:
    """Redis-based queue client for async job processing"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis = redis.from_url(redis_url, decode_responses=True)
        self.job_queue = "meeting_jobs"
        self.status_prefix = "job_status:"
        self.result_prefix = "job_result:"
        
    def submit_job(self, job_type: str, data: Dict[str, Any]) -> str:
        """Submit a job to the queue and return job ID"""
        job_id = str(uuid.uuid4())
        
        job_payload = {
            "id": job_id,
            "type": job_type,
            "data": data,
            "created_at": datetime.now().isoformat(),
            "status": JobStatus.PENDING.value
        }
        
        # Add job to queue
        self.redis.lpush(self.job_queue, json.dumps(job_payload))
        
        # Set initial status
        self.redis.setex(
            f"{self.status_prefix}{job_id}",
            3600,  # 1 hour TTL
            JobStatus.PENDING.value
        )
        
        return job_id
    
    def get_job_status(self, job_id: str) -> Optional[str]:
        """Get current status of a job"""
        return self.redis.get(f"{self.status_prefix}{job_id}")
    
    def get_job_result(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get result of a completed job"""
        result_json = self.redis.get(f"{self.result_prefix}{job_id}")
        return json.loads(result_json) if result_json else None
    
    def update_job_status(self, job_id: str, status: JobStatus, result: Dict[str, Any] = None):
        """Update job status and optionally store result"""
        self.redis.setex(
            f"{self.status_prefix}{job_id}",
            3600,
            status.value
        )
        
        if result:
            self.redis.setex(
                f"{self.result_prefix}{job_id}",
                3600,
                json.dumps(result)
            )
    
    def wait_for_job(self, job_id: str, timeout: int = 300) -> Dict[str, Any]:
        """Wait for job completion with timeout"""
        start_time = datetime.now()
        
        while (datetime.now() - start_time).seconds < timeout:
            status = self.get_job_status(job_id)
            
            if status == JobStatus.COMPLETED.value:
                result = self.get_job_result(job_id)
                if result:
                    return result
            elif status == JobStatus.FAILED.value:
                result = self.get_job_result(job_id)
                raise Exception(f"Job failed: {result.get('error', 'Unknown error')}")
            
            await asyncio.sleep(1)
        
        raise TimeoutError(f"Job {job_id} did not complete within {timeout} seconds")


class AsyncProcessingMixin:
    """Mixin to add async processing capabilities to existing classes"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.queue_client = QueueClient()
        self.enable_async = False  # Feature flag
    
    def submit_transcript_processing(self, transcript: str, meeting_data: Dict[str, Any]) -> str:
        """Submit transcript processing as async job"""
        job_data = {
            "transcript": transcript,
            "meeting_data": meeting_data
        }
        return self.queue_client.submit_job("process_transcript", job_data)
    
    def submit_chunk_processing(self, chunks: list, meeting_data: Dict[str, Any]) -> str:
        """Submit chunked transcript processing as async job"""
        job_data = {
            "chunks": chunks,
            "meeting_data": meeting_data
        }
        return self.queue_client.submit_job("process_chunks", job_data)
    
    def check_job_progress(self, job_id: str) -> Dict[str, str]:
        """Check job progress with user-friendly messages"""
        status = self.queue_client.get_job_status(job_id)
        
        status_messages = {
            JobStatus.PENDING.value: "⏳ Job queued, waiting to start...",
            JobStatus.PROCESSING.value: "🔄 Processing transcript...",
            JobStatus.COMPLETED.value: "✅ Processing completed!",
            JobStatus.FAILED.value: "❌ Processing failed"
        }
        
        return {
            "status": status,
            "message": status_messages.get(status, "Unknown status")
        }