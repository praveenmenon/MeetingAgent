# Rate Limiting & Retry Guide

## Overview

The Meeting Agent now includes comprehensive rate limiting, retry logic, and request queuing to handle API quotas gracefully. This system prevents failures when hitting OpenAI/Anthropic limits and automatically recovers when quotas reset.

## Features

### 🛡️ **Intelligent Retry Logic**
- **Exponential backoff**: Delays increase exponentially between retries
- **Jitter**: Randomization prevents thundering herd problems
- **Error type detection**: Different strategies for rate limits vs. server errors
- **Configurable limits**: Customize retry behavior per environment

### ⏳ **Request Queuing**
- **Automatic queuing**: Failed requests due to quotas are queued for retry
- **FIFO processing**: First-in, first-out request handling
- **Queue management**: Monitor and clear queues when needed
- **Background processing**: Queued requests processed when limits allow

### 📊 **Rate Limit Monitoring**
- **Real-time tracking**: Monitor quota usage across providers
- **Header parsing**: Extract limits from API response headers
- **Usage alerts**: Warnings when approaching quota limits
- **Status display**: Visual quota status with color indicators

## Rate Limiting Behavior

### **Error Detection & Classification**

The system detects and handles different error types:

```python
# Rate limiting (429 errors)
"rate limit", "too many requests", "429"
→ Wait 60s (configurable), then retry

# Quota exceeded 
"quota exceeded", "insufficient_quota", "billing"  
→ Wait 1 hour (configurable), queue request

# Server errors (5xx)
"500", "502", "503", "504", "internal server"
→ Exponential backoff retry

# Connection issues
"connection", "timeout", "network"
→ Exponential backoff retry

# Client errors (4xx except 429)
"400", "401", "403", "404", "invalid"
→ No retry (permanent failure)
```

### **Backoff Strategy**

```
Attempt 1: base_delay × 1       = 1.0s  + jitter
Attempt 2: base_delay × 2       = 2.0s  + jitter  
Attempt 3: base_delay × 4       = 4.0s  + jitter
Attempt 4: base_delay × 8       = 8.0s  + jitter
Attempt 5: base_delay × 16      = 16.0s + jitter
Max delay: 60s (configurable)
```

### **Request Queuing Flow**

```
API Request → Rate Limited? → Queue Request → Background Processing
     ↓              ↓              ↓                    ↓
   Success      Retry Logic    Store in Redis    Process When Ready
```

## Configuration

### **Environment Variables**

Add to your `.env` file:

```bash
# Basic retry configuration
RATE_LIMIT_MAX_RETRIES=5               # Maximum retry attempts
RATE_LIMIT_BASE_DELAY=1.0              # Base delay in seconds
RATE_LIMIT_MAX_DELAY=60.0              # Maximum delay cap
RATE_LIMIT_JITTER=true                 # Enable randomization

# Error-specific delays
RATE_LIMIT_RATE_LIMIT_DELAY=60.0       # 429 rate limit delay
RATE_LIMIT_QUOTA_EXCEEDED_DELAY=3600.0 # Quota exceeded delay (1 hour)

# Exponential backoff
RATE_LIMIT_EXPONENTIAL_BASE=2.0        # Backoff multiplier
```

### **Programmatic Configuration**

```python
from src.meeting_agent.rate_limiter import RetryConfig, configure_rate_limiter

config = RetryConfig(
    max_retries=3,
    base_delay=2.0,
    rate_limit_delay=120.0,  # 2 minutes for rate limits
    quota_exceeded_delay=1800.0,  # 30 minutes for quota
    jitter=True
)

configure_rate_limiter(config)
```

## Monitoring & Management

### **Built-in Status Check**

In the Meeting Agent Q&A mode:
```
Ask a question about meetings (or 'exit'): rate limits
```

Output shows:
- 🟢 Green: >50% quota remaining
- 🟡 Yellow: 20-50% quota remaining  
- 🔴 Red: <20% quota remaining
- ⏳ Queued requests count
- ⏸️ Backoff periods

### **Rate Limit Monitor CLI**

```bash
# Show current status
python rate_limit_monitor.py status

# Watch in real-time
python rate_limit_monitor.py watch --interval 10

# Process queued requests
python rate_limit_monitor.py process --max-requests 20

# Clear backoff periods
python rate_limit_monitor.py clear-backoff --provider openai

# Configure retry settings
python rate_limit_monitor.py configure --max-retries 3 --base-delay 2

# Export status for analysis
python rate_limit_monitor.py export rate_limits.json
```

### **Status Display Example**

```
🔄 API Rate Limit Status:

📡 OPENAI:
  Recent requests: 12/min
  Request quota: 🟢 4,847/5,000 (96.9%)
  Token quota: 🟡 847,231/1,000,000 (84.7%)
  Status: ✅ Ready

📡 ANTHROPIC:
  Recent requests: 3/min  
  Request quota: 🟢 47/50 (94.0%)
  Token quota: 🟢 89,234/100,000 (89.2%)
  Queued requests: ⏳ 2
  Status: ✅ Ready

✅ Processed 2 queued requests
```

## API Provider Specifics

### **OpenAI Rate Limits**

Headers parsed:
- `x-ratelimit-limit-requests`
- `x-ratelimit-remaining-requests`
- `x-ratelimit-limit-tokens`
- `x-ratelimit-remaining-tokens`
- `x-ratelimit-reset-requests`
- `x-ratelimit-reset-tokens`

Common limits:
- **Free tier**: 3 requests/min, 150,000 tokens/min
- **Pay-as-you-go**: 3,500 requests/min, 2,000,000 tokens/min
- **Usage tier based**: Increases with usage history

### **Anthropic Rate Limits**

Headers parsed:
- `anthropic-ratelimit-requests-limit`
- `anthropic-ratelimit-requests-remaining` 
- `anthropic-ratelimit-tokens-limit`
- `anthropic-ratelimit-tokens-remaining`
- `retry-after`

Common limits:
- **API tier 1**: 50 requests/min, 40,000 tokens/min
- **API tier 2**: 1,000 requests/min, 80,000 tokens/min
- **Higher tiers**: 5,000+ requests/min, 400,000+ tokens/min

## Error Handling Examples

### **Rate Limit Hit (429)**

```
⚠️  OpenAI request failed (attempt 1/5): Rate limit exceeded. Retrying in 62.3s
⚠️  OpenAI request failed (attempt 2/5): Rate limit exceeded. Retrying in 124.7s
✅  Request succeeded on attempt 3
```

### **Quota Exceeded**

```
❌ OpenAI request failed: Quota exceeded. Attempting to queue request
📋 Queued request for OpenAI (queue size: 1)
ℹ️  Will retry when quota resets or manually processed
```

### **Connection Issues**

```
⚠️  Anthropic request failed (attempt 1/5): Connection timeout. Retrying in 1.1s
⚠️  Anthropic request failed (attempt 2/5): Connection timeout. Retrying in 2.3s
✅  Request succeeded on attempt 3
```

## Best Practices

### 🎯 **Proactive Monitoring**
```bash
# Set up periodic monitoring
while true; do
  python rate_limit_monitor.py status
  sleep 300  # Check every 5 minutes
done
```

### ⚡ **Optimize Token Usage**
- Use appropriate `max_tokens` per task type
- Monitor token consumption patterns
- Consider model selection (GPT-4 vs GPT-3.5 vs Claude)

### 🔄 **Queue Management**
```bash
# Process queues during off-peak hours
python rate_limit_monitor.py process --max-requests 50

# Clear old queued requests if needed
python rate_limit_monitor.py clear-queues
```

### 📊 **Usage Analysis**
```bash
# Export regular status for trend analysis
python rate_limit_monitor.py export "status_$(date +%Y%m%d_%H%M).json"
```

## Production Deployment

### **Docker Compose Integration**

The rate limiting system works seamlessly with Docker:

```yaml
services:
  meeting-agent:
    environment:
      - RATE_LIMIT_MAX_RETRIES=3
      - RATE_LIMIT_BASE_DELAY=2.0
      - RATE_LIMIT_QUOTA_EXCEEDED_DELAY=1800
```

### **Monitoring Scripts**

```bash
# Health check script
#!/bin/bash
python rate_limit_monitor.py status | grep -q "Ready" || {
  echo "Rate limits exceeded, processing queue..."
  python rate_limit_monitor.py process --max-requests 10
}
```

### **Alerting Integration**

```bash
# Alert on low quotas (integrate with your monitoring)
python rate_limit_monitor.py export - | jq '.rate_limits.openai.remaining_requests' | {
  read remaining
  if [ "$remaining" -lt 100 ]; then
    # Send alert (Slack, email, etc.)
    echo "OpenAI quota low: $remaining requests remaining"
  fi
}
```

## Troubleshooting

### **High Queue Size**
```bash
# Check what's queued
python rate_limit_monitor.py status

# Process immediately if possible
python rate_limit_monitor.py process --max-requests 50

# Clear if queue is stale
python rate_limit_monitor.py clear-queues
```

### **Persistent Backoffs**
```bash
# Clear backoff periods
python rate_limit_monitor.py clear-backoff

# Check if quotas have reset
python rate_limit_monitor.py status
```

### **Request Failures**
- Check API keys are valid and have quota
- Verify network connectivity
- Review error logs for specific failure reasons
- Consider reducing request rate temporarily

### **Performance Impact**
- Retries add latency but ensure reliability
- Queue processing happens in background
- Monitor overall system performance
- Adjust retry configuration if needed

The rate limiting system provides robust handling of API quotas while maintaining application reliability and user experience.