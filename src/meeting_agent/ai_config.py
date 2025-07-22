"""
AI model configuration and parameter management
"""

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class TaskType(Enum):
    """Different AI task types with specific optimization needs"""

    SUMMARIZATION = "summarization"
    BRIEF_DESCRIPTION = "brief_description"
    SIMILARITY_CHECK = "similarity_check"
    TASK_SUGGESTION = "task_suggestion"
    QA_ANSWERING = "qa_answering"
    CHUNK_COMBINATION = "chunk_combination"
    CREATIVE_WRITING = "creative_writing"
    ANALYSIS = "analysis"


@dataclass
class ModelParams:
    """Model parameters for AI API calls"""

    temperature: float = 0.7
    max_tokens: int = 1000
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    model: Optional[str] = None

    def to_openai_dict(self, base_model: str = "gpt-4o-mini") -> Dict[str, Any]:
        """Convert to OpenAI API parameters"""
        params = {
            "model": self.model or base_model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "top_p": self.top_p,
            "frequency_penalty": self.frequency_penalty,
            "presence_penalty": self.presence_penalty,
        }
        return params

    def to_anthropic_dict(
        self, base_model: str = "claude-3-5-sonnet-20240620"
    ) -> Dict[str, Any]:
        """Convert to Anthropic API parameters"""
        params = {
            "model": self.model or base_model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            # Anthropic doesn't use top_p, frequency_penalty, presence_penalty in the same way
        }
        return params


class AIConfig:
    """Configuration manager for AI model parameters per task type"""

    def __init__(self):
        self.task_configs = self._load_default_configs()
        self._load_env_overrides()

    def _load_default_configs(self) -> Dict[TaskType, ModelParams]:
        """Load optimized default configurations for each task type"""
        return {
            # Conservative settings for factual summarization
            TaskType.SUMMARIZATION: ModelParams(
                temperature=0.3,  # Low creativity, high consistency
                max_tokens=2000,  # Longer outputs for comprehensive notes
                top_p=0.8,  # Focused vocabulary
                frequency_penalty=0.1,  # Reduce repetition
                presence_penalty=0.0,  # Allow repeated concepts
            ),
            # Very concise and focused
            TaskType.BRIEF_DESCRIPTION: ModelParams(
                temperature=0.2,  # Very conservative
                max_tokens=150,  # Short output
                top_p=0.7,  # Focused
                frequency_penalty=0.2,  # Avoid repetition in short text
                presence_penalty=0.1,
            ),
            # Analytical comparison task
            TaskType.SIMILARITY_CHECK: ModelParams(
                temperature=0.1,  # Minimal creativity, consistent analysis
                max_tokens=200,  # Brief JSON output
                top_p=0.6,  # Very focused
                frequency_penalty=0.0,  # Don't penalize structured output
                presence_penalty=0.0,
                model="claude-3-5-sonnet-20240620",  # Override to use Claude
            ),
            # Creative but practical task suggestions
            TaskType.TASK_SUGGESTION: ModelParams(
                temperature=0.6,  # Moderate creativity
                max_tokens=1500,  # Detailed task descriptions
                top_p=0.9,  # Allow diverse vocabulary
                frequency_penalty=0.1,  # Some variety in suggestions
                presence_penalty=0.2,  # Encourage new topics
            ),
            # Conversational Q&A
            TaskType.QA_ANSWERING: ModelParams(
                temperature=0.5,  # Balanced creativity
                max_tokens=1000,  # Detailed answers
                top_p=0.9,  # Natural conversation
                frequency_penalty=0.1,  # Avoid repetition
                presence_penalty=0.1,  # Encourage comprehensive answers
            ),
            # Coherent combination of multiple summaries
            TaskType.CHUNK_COMBINATION: ModelParams(
                temperature=0.4,  # Consistent combination style
                max_tokens=3000,  # Long combined output
                top_p=0.8,  # Focused vocabulary
                frequency_penalty=0.2,  # Reduce redundancy
                presence_penalty=0.0,  # Allow repeated important info
            ),
            # High creativity for creative tasks
            TaskType.CREATIVE_WRITING: ModelParams(
                temperature=0.8,  # High creativity
                max_tokens=2000,  # Longer creative outputs
                top_p=0.95,  # Diverse vocabulary
                frequency_penalty=0.3,  # Encourage variety
                presence_penalty=0.3,  # Explore new concepts
            ),
            # Analytical deep-dive
            TaskType.ANALYSIS: ModelParams(
                temperature=0.4,  # Balanced analysis
                max_tokens=2500,  # Detailed analysis
                top_p=0.85,  # Analytical vocabulary
                frequency_penalty=0.1,  # Some variety
                presence_penalty=0.15,  # Comprehensive coverage
            ),
        }

    def _load_env_overrides(self):
        """Load configuration overrides from environment variables"""
        for task_type in TaskType:
            task_prefix = f"AI_{task_type.value.upper()}"

            # Check for task-specific overrides
            if temp := os.getenv(f"{task_prefix}_TEMPERATURE"):
                self.task_configs[task_type].temperature = float(temp)

            if max_tokens := os.getenv(f"{task_prefix}_MAX_TOKENS"):
                self.task_configs[task_type].max_tokens = int(max_tokens)

            if top_p := os.getenv(f"{task_prefix}_TOP_P"):
                self.task_configs[task_type].top_p = float(top_p)

            if freq_penalty := os.getenv(f"{task_prefix}_FREQUENCY_PENALTY"):
                self.task_configs[task_type].frequency_penalty = float(freq_penalty)

            if pres_penalty := os.getenv(f"{task_prefix}_PRESENCE_PENALTY"):
                self.task_configs[task_type].presence_penalty = float(pres_penalty)

            if model := os.getenv(f"{task_prefix}_MODEL"):
                self.task_configs[task_type].model = model

    def get_params(self, task_type: TaskType) -> ModelParams:
        """Get model parameters for a specific task type"""
        return self.task_configs.get(
            task_type, self.task_configs[TaskType.SUMMARIZATION]
        )

    def get_openai_params(
        self, task_type: TaskType, base_model: str = "gpt-4o-mini"
    ) -> Dict[str, Any]:
        """Get OpenAI API parameters for a task"""
        params = self.get_params(task_type)
        return params.to_openai_dict(base_model)

    def get_anthropic_params(
        self, task_type: TaskType, base_model: str = "claude-3-5-sonnet-20240620"
    ) -> Dict[str, Any]:
        """Get Anthropic API parameters for a task"""
        params = self.get_params(task_type)
        return params.to_anthropic_dict(base_model)

    def update_task_config(self, task_type: TaskType, **kwargs):
        """Update configuration for a specific task type"""
        current_params = self.task_configs[task_type]

        for key, value in kwargs.items():
            if hasattr(current_params, key):
                setattr(current_params, key, value)

    def get_config_summary(self) -> Dict[str, Dict[str, Any]]:
        """Get a summary of all current configurations"""
        summary = {}
        for task_type, params in self.task_configs.items():
            summary[task_type.value] = {
                "temperature": params.temperature,
                "max_tokens": params.max_tokens,
                "top_p": params.top_p,
                "frequency_penalty": params.frequency_penalty,
                "presence_penalty": params.presence_penalty,
                "model": params.model or "default",
            }
        return summary

    def reset_to_defaults(self, task_type: Optional[TaskType] = None):
        """Reset configuration to defaults"""
        if task_type:
            self.task_configs[task_type] = self._load_default_configs()[task_type]
        else:
            self.task_configs = self._load_default_configs()

        # Reapply environment overrides
        self._load_env_overrides()


# Global configuration instance
ai_config = AIConfig()


def get_ai_config() -> AIConfig:
    """Get the global AI configuration instance"""
    return ai_config
