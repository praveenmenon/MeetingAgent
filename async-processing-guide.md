# Async Processing Guide

## Overview

The Meeting Agent now supports asynchronous processing for large transcripts and high-volume scenarios. This architecture uses Redis queues and background workers to handle time-intensive AI processing tasks without blocking the main CLI interface.

## Architecture

```
┌─────────────────┐    ┌───────────────┐    ┌─────────────────┐
│   CLI Client    │───▶│  Redis Queue  │───▶│ Background      │
│  (main.py)      │    │               │    │ Worker          │
│                 │    │               │    │ (worker.py)     │
└─────────────────┘    └───────────────┘    └─────────────────┘
         ▲                                            │
         │                                            ▼
         └──────────────────────────────────────────────
                    Results via Redis
```

## Features

### Intelligent Chunking
- **Speaker-based chunking**: Splits transcript at speaker boundaries
- **Time-based chunking**: Divides by time segments (configurable)
- **Context preservation**: Maintains overlap between chunks
- **Smart thresholds**: Auto-detects when chunking is needed

### Async Processing
- **Queue-based jobs**: Redis-backed job queue
- **Progress tracking**: Real-time status updates
- **Graceful fallback**: Falls back to sync processing if worker unavailable
- **Error handling**: Comprehensive error recovery

### Processing Modes

#### Sync Mode (Default)
- Direct API calls in CLI process
- Good for small-medium transcripts
- Immediate results
- Lower resource usage

#### Async Mode (Optional)
- Background worker processing
- Handles large transcripts efficiently
- Non-blocking CLI
- Better for high volume

## Setup

### Environment Variables

Add to your `config/.env`:

```bash
# Enable async processing (optional)
ENABLE_ASYNC_PROCESSING=true

# Redis connection (optional, defaults to localhost)
REDIS_URL=redis://localhost:6379
```

### Docker Setup

#### Standard Mode (Sync Only)
```bash
# Run with sync processing only
docker-compose up --build
```

#### Async Mode with Worker
```bash
# Run with async processing enabled
docker-compose --profile worker up --build

# Or set environment variable and run
ENABLE_ASYNC_PROCESSING=true docker-compose --profile worker up --build
```

### Manual Setup

#### 1. Start Redis
```bash
# Local Redis
redis-server

# Or with Docker
docker run -d -p 6379:6379 redis:7-alpine
```

#### 2. Start Worker (Terminal 1)
```bash
python worker.py
```

#### 3. Run Meeting Agent (Terminal 2)
```bash
# Enable async processing
export ENABLE_ASYNC_PROCESSING=true
python meeting_agent.py
```

## When Chunking Triggers

The system automatically chunks transcripts when:

- **Size > 8,000 characters** (roughly 2x normal API limit)
- **Speaker count > 10** (complex multi-person meetings)
- **Line count > 200** (long transcripts)

## Processing Flow

### Large Transcript Detection
```
📊 Large transcript detected (15,432 characters)
🔄 Estimated speakers: 8
📝 Estimated processing time: 45 seconds
```

### Async Processing
```
🚀 Submitting transcript for async processing...
📋 Job ID: abc123-def456-789
⏳ Waiting for processing to complete...
🔄 Processing transcript...
✅ Async processing completed in 42.3 seconds
📄 Processed as 4 chunks
```

### Chunking Output
```
📄 Large transcript detected, chunking...
📄 Created 4 chunks
🔄 Processing chunk 1/4
🔄 Processing chunk 2/4
🔄 Processing chunk 3/4
🔄 Processing chunk 4/4
```

## Monitoring

### Worker Logs
```bash
# Docker
docker-compose logs -f meeting-worker

# Local
# Check worker.py output
```

### Redis Monitoring
```bash
# Connect to Redis CLI
redis-cli

# Monitor queue
LLEN meeting_jobs

# Check job status
GET job_status:abc123-def456-789
```

## Performance Benefits

### Large Transcript Handling
- **Before**: Single API call with 20,000 character limit
- **After**: Chunked processing with unlimited size

### Volume Handling
- **Before**: Blocks CLI during processing
- **After**: Queue multiple transcripts, process in background

### Resource Usage
- **Before**: All processing in main process
- **After**: Distributed across workers, better CPU utilization

## Configuration

### Chunking Parameters
```python
# In chunking.py
chunker = TranscriptChunker(
    max_chunk_size=4000,    # Characters per chunk
    overlap_size=200        # Overlap between chunks
)
```

### Queue Settings
```python
# In queue_client.py
job_timeout = 3600          # 1 hour job TTL
poll_interval = 2           # Status check interval
```

## Troubleshooting

### Worker Not Starting
```bash
# Check Redis connection
redis-cli ping

# Check worker logs
docker-compose logs meeting-worker
```

### Jobs Stuck in Queue
```bash
# Clear queue
redis-cli DEL meeting_jobs

# Restart worker
docker-compose restart meeting-worker
```

### Fallback to Sync
If async processing fails, the system automatically falls back to synchronous processing:
```
❌ Async processing failed, falling back to sync processing...
```

## Scaling

### Multiple Workers
```bash
# Scale up workers
docker-compose --profile worker up --scale meeting-worker=3
```

### Load Balancing
- Redis handles job distribution automatically
- Workers pull jobs from shared queue
- No additional configuration needed

## Future Enhancements

- **Priority queues** for urgent transcripts
- **Batch processing** for multiple meetings
- **Web dashboard** for job monitoring
- **Webhook notifications** for completion
- **Auto-scaling** based on queue depth