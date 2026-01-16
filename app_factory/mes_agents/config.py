"""
Configuration for MES Agents.
"""

from dataclasses import dataclass
from typing import Dict, List


@dataclass
class AgentConfig:
    """Configuration for MES Analysis Agent."""
    
    agent_enabled: bool = True
    default_model: str = 'us.anthropic.claude-haiku-4-5-20251001-v1:0'
    timeout_seconds: int = 120
    max_query_steps: int = 5
    enable_progress_updates: bool = True
    analysis_depth: str = 'standard'  # 'standard', 'comprehensive'
    
    # Supported models
    SUPPORTED_MODELS = [
        'us.amazon.nova-lite-v1:0',
        'us.amazon.nova-pro-v1:0',
        'us.anthropic.claude-haiku-4-5-20251001-v1:0',
        'us.anthropic.claude-3-7-sonnet-20250219-v1:0',
        'us.anthropic.claude-sonnet-4-20250514-v1:0',
        'us.anthropic.claude-haiku-4-5-20251001-v1:0'
    ]
    
    @classmethod
    def get_model_display_names(cls) -> Dict[str, str]:
        """Get user-friendly display names for models."""
        return {
            'us.amazon.nova-lite-v1:0': 'Amazon Nova Lite (Fast)',
            'us.amazon.nova-pro-v1:0': 'Amazon Nova Pro (Balanced)',
            'us.anthropic.claude-haiku-4-5-20251001-v1:0': 'Claude 3.5 Haiku (Fast)',
            'us.anthropic.claude-3-7-sonnet-20250219-v1:0': 'Claude 3.7 Sonnet (Advanced)',
            'us.anthropic.claude-sonnet-4-20250514-v1:0': 'Claude 4 Sonnet (Advanced)',
            'us.anthropic.claude-haiku-4-5-20251001-v1:0': 'Claude 4.5 Haiku (Recommended)'
        }


# Default configuration instance
default_config = AgentConfig()