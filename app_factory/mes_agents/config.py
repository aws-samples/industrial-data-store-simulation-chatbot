"""Configuration for MES Agents."""

from dataclasses import dataclass, field
from typing import Dict, List


# Model catalog — geo (cross-region) inference profiles on Bedrock.
SUPPORTED_MODELS: List[str] = [
    'us.anthropic.claude-sonnet-5',
    'us.anthropic.claude-haiku-4-5-20251001-v1:0',
    'us.anthropic.claude-sonnet-4-20250514-v1:0',
    'us.amazon.nova-lite-v1:0',
    'us.amazon.nova-pro-v1:0',
]

MODEL_DISPLAY_NAMES: Dict[str, str] = {
    'us.anthropic.claude-sonnet-5': 'Claude Sonnet 5 (Advanced)',
    'us.anthropic.claude-haiku-4-5-20251001-v1:0': 'Claude 4.5 Haiku (Fast, Recommended)',
    'us.anthropic.claude-sonnet-4-20250514-v1:0': 'Claude Sonnet 4',
    'us.amazon.nova-lite-v1:0': 'Amazon Nova Lite (Fast)',
    'us.amazon.nova-pro-v1:0': 'Amazon Nova Pro (Balanced)',
}


@dataclass
class AgentConfig:
    """Configuration for MES Analysis Agent."""

    agent_enabled: bool = True
    default_model: str = 'us.anthropic.claude-haiku-4-5-20251001-v1:0'
    timeout_seconds: int = 120
    max_tokens: int = 4096
    analysis_depth: str = 'standard'  # 'standard', 'comprehensive'

    @classmethod
    def get_model_display_names(cls) -> Dict[str, str]:
        return MODEL_DISPLAY_NAMES


# Default configuration instance
default_config = AgentConfig()
