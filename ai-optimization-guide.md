# AI Model Optimization Guide

## Overview

The Meeting Agent now supports per-task AI model parameter optimization. Different AI tasks (summarization, Q&A, task generation) have different requirements for creativity, accuracy, and output style. This system allows fine-tuning of model parameters for each task type.

## Task Types & Optimizations

### 📝 Summarization (`SUMMARIZATION`)
**Goal**: Accurate, consistent meeting notes  
**Optimized for**: Factual accuracy, consistency, comprehensive coverage

**Default Parameters**:
- `temperature`: 0.3 (low creativity)
- `max_tokens`: 2000 (longer outputs)
- `top_p`: 0.8 (focused vocabulary)
- `frequency_penalty`: 0.1 (reduce repetition)

**Use Cases**: Meeting notes, action items, decisions

### 📄 Brief Description (`BRIEF_DESCRIPTION`)
**Goal**: Concise, focused summaries  
**Optimized for**: Brevity, clarity, essential information

**Default Parameters**:
- `temperature`: 0.2 (very conservative)
- `max_tokens`: 150 (short output)
- `top_p`: 0.7 (focused)
- `frequency_penalty`: 0.2 (avoid repetition)

**Use Cases**: Notion page descriptions, email subject lines

### 🔍 Similarity Check (`SIMILARITY_CHECK`)
**Goal**: Consistent analytical comparison  
**Optimized for**: Reliability, structured output

**Default Parameters**:
- `temperature`: 0.1 (minimal creativity)
- `max_tokens`: 200 (brief JSON)
- `model`: Claude (override to Anthropic)

**Use Cases**: Finding related meetings, duplicate detection

### ✅ Task Suggestion (`TASK_SUGGESTION`)
**Goal**: Creative but practical task ideas  
**Optimized for**: Useful suggestions, variety

**Default Parameters**:
- `temperature`: 0.6 (moderate creativity)
- `max_tokens`: 1500 (detailed suggestions)
- `presence_penalty`: 0.2 (explore new topics)

**Use Cases**: Action item generation, follow-up tasks

### 💬 Q&A Answering (`QA_ANSWERING`)
**Goal**: Helpful, conversational responses  
**Optimized for**: Natural conversation, comprehensive answers

**Default Parameters**:
- `temperature`: 0.5 (balanced)
- `max_tokens`: 1000 (detailed answers)
- `top_p`: 0.9 (natural language)

**Use Cases**: User questions, information retrieval

### 🔗 Chunk Combination (`CHUNK_COMBINATION`)
**Goal**: Coherent combination of multiple summaries  
**Optimized for**: Consistency, redundancy reduction

**Default Parameters**:
- `temperature`: 0.4 (consistent style)
- `max_tokens`: 3000 (long combined output)
- `frequency_penalty`: 0.2 (reduce redundancy)

**Use Cases**: Large transcript processing, multi-part meetings

## Configuration Methods

### 1. Environment Variables
Set in your `.env` file:
```bash
# Format: AI_{TASK_TYPE}_{PARAMETER}
AI_SUMMARIZATION_TEMPERATURE=0.2
AI_SUMMARIZATION_MAX_TOKENS=2500
AI_SUMMARIZATION_MODEL=gpt-4o

AI_QA_ANSWERING_TEMPERATURE=0.7
AI_TASK_SUGGESTION_CREATIVITY=0.8
```

### 2. Configuration Manager CLI
```bash
# Show current configuration
python ai_config_manager.py show

# Show specific task
python ai_config_manager.py show --task summarization

# Update parameters
python ai_config_manager.py update summarization temperature 0.2
python ai_config_manager.py update qa_answering max_tokens 1200

# Reset to defaults
python ai_config_manager.py reset --task summarization
python ai_config_manager.py reset  # Reset all

# Export/import configurations
python ai_config_manager.py export my_config.json
python ai_config_manager.py import optimized_config.json
```

### 3. Programmatic Updates
```python
from src.meeting_agent.ai_config import get_ai_config, TaskType

config = get_ai_config()

# Update specific task
config.update_task_config(
    TaskType.SUMMARIZATION,
    temperature=0.2,
    max_tokens=2500
)

# Get current parameters
params = config.get_params(TaskType.QA_ANSWERING)
```

## Parameter Guide

### Temperature (0.0 - 2.0)
**Controls creativity and randomness**
- `0.0-0.3`: Very consistent, factual (summaries, analysis)
- `0.3-0.7`: Balanced (general use)
- `0.7-1.0`: Creative, varied (brainstorming, creative writing)
- `1.0+`: Highly creative, unpredictable

### Max Tokens
**Controls output length**
- `50-200`: Brief responses (descriptions, status)
- `200-1000`: Standard responses (summaries, answers)
- `1000-3000`: Long responses (detailed analysis, combined chunks)
- `3000+`: Very long outputs (comprehensive reports)

### Top P (0.0 - 1.0)
**Controls vocabulary diversity**
- `0.1-0.6`: Focused, precise vocabulary
- `0.6-0.8`: Balanced vocabulary
- `0.8-1.0`: Diverse, natural vocabulary

### Frequency Penalty (0.0 - 2.0)
**Reduces repetition of words/phrases**
- `0.0`: No penalty
- `0.1-0.3`: Light penalty (recommended)
- `0.5+`: Strong penalty (may affect quality)

### Presence Penalty (0.0 - 2.0)
**Encourages new topics/concepts**
- `0.0`: No encouragement
- `0.1-0.3`: Light encouragement
- `0.5+`: Strong encouragement (may lose focus)

## Optimization Scenarios

### 🏢 Corporate/Legal/Medical
**Requirements**: High accuracy, consistency, compliance
```bash
AI_SUMMARIZATION_TEMPERATURE=0.1
AI_SUMMARIZATION_TOP_P=0.6
AI_BRIEF_DESCRIPTION_TEMPERATURE=0.1
AI_QA_ANSWERING_TEMPERATURE=0.3
```

### 🚀 Startup/Creative
**Requirements**: Innovation, creative suggestions, brainstorming
```bash
AI_TASK_SUGGESTION_TEMPERATURE=0.8
AI_TASK_SUGGESTION_PRESENCE_PENALTY=0.3
AI_CREATIVE_WRITING_TEMPERATURE=0.9
AI_QA_ANSWERING_TEMPERATURE=0.6
```

### 📊 Data/Research
**Requirements**: Analytical accuracy, structured output
```bash
AI_ANALYSIS_TEMPERATURE=0.4
AI_ANALYSIS_MAX_TOKENS=2500
AI_SIMILARITY_CHECK_TEMPERATURE=0.1
AI_SUMMARIZATION_FREQUENCY_PENALTY=0.2
```

### 🎓 Educational/Training
**Requirements**: Clear explanations, comprehensive coverage
```bash
AI_QA_ANSWERING_TEMPERATURE=0.5
AI_QA_ANSWERING_MAX_TOKENS=1500
AI_SUMMARIZATION_MAX_TOKENS=2500
AI_TASK_SUGGESTION_TEMPERATURE=0.5
```

## Model Selection

### OpenAI Models
```bash
# High-end reasoning
AI_SUMMARIZATION_MODEL=gpt-4o
AI_ANALYSIS_MODEL=gpt-4o

# Cost-effective
AI_BRIEF_DESCRIPTION_MODEL=gpt-4o-mini
AI_TASK_SUGGESTION_MODEL=gpt-4o-mini

# Legacy
AI_QA_ANSWERING_MODEL=gpt-3.5-turbo
```

### Anthropic Models
```bash
# Best reasoning
AI_SIMILARITY_CHECK_MODEL=claude-3-5-sonnet-20240620
AI_ANALYSIS_MODEL=claude-3-5-sonnet-20240620

# Balanced
AI_SUMMARIZATION_MODEL=claude-3-5-haiku-20241022
```

## Performance Testing

### A/B Testing Setup
1. Export current config: `python ai_config_manager.py export baseline.json`
2. Create test config with modified parameters
3. Process same transcript with both configs
4. Compare output quality, consistency, cost

### Quality Metrics
- **Accuracy**: Fact checking against original transcript
- **Completeness**: Coverage of key information
- **Consistency**: Similar outputs for similar inputs
- **Relevance**: Appropriateness for intended use
- **Cost**: Token usage and API costs

### Monitoring
```python
# Track token usage by task type
from src.meeting_agent.ai_config import get_ai_config

config = get_ai_config()
params = config.get_params(TaskType.SUMMARIZATION)
print(f"Max tokens for summarization: {params.max_tokens}")
```

## Best Practices

### 🎯 Start Conservative
- Begin with low temperature (0.2-0.4)
- Gradually increase if output is too rigid
- Monitor for consistency issues

### 📊 Monitor Token Usage
- Higher max_tokens = higher costs
- Set appropriate limits for each task
- Use brief descriptions for cost control

### 🔄 Iterative Optimization
- Test one parameter at a time
- Keep baseline configuration for comparison
- Document changes and results

### 🎛️ Use Task-Specific Settings
- Don't use one-size-fits-all parameters
- Optimize for specific use cases
- Consider audience and requirements

### 📈 Regular Review
- Periodically review configurations
- Update based on user feedback
- Test new models as they become available

## Troubleshooting

### Output Too Repetitive
- Increase `frequency_penalty` (0.1-0.3)
- Slightly increase `temperature`
- Check `top_p` setting

### Output Too Creative/Inconsistent
- Decrease `temperature` (0.1-0.4)
- Decrease `top_p` (0.6-0.8)
- Reduce `presence_penalty`

### Output Too Brief
- Increase `max_tokens`
- Check prompt engineering
- Reduce `frequency_penalty`

### High API Costs
- Reduce `max_tokens` where appropriate
- Use more cost-effective models
- Optimize prompts for conciseness

## Configuration Templates

Ready-to-use configuration files are available:
- `configs/conservative.json` - High accuracy, low creativity
- `configs/balanced.json` - Standard business use
- `configs/creative.json` - Innovation and brainstorming
- `configs/analytical.json` - Research and analysis