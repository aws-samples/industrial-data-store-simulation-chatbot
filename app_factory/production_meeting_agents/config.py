"""
Configuration for Production Meeting Agents.
"""

from dataclasses import dataclass
from typing import Dict, List


# Geo (cross-region) inference profiles available on Bedrock.
SUPPORTED_MODELS: List[str] = [
    'us.anthropic.claude-sonnet-5',
    'us.anthropic.claude-haiku-4-5-20251001-v1:0',
    'us.anthropic.claude-sonnet-4-20250514-v1:0',
    'us.amazon.nova-lite-v1:0',
    'us.amazon.nova-pro-v1:0',
]

MODEL_DISPLAY_NAMES: Dict[str, str] = {
    'us.anthropic.claude-sonnet-5': 'Claude Sonnet 5 (Recommended)',
    'us.anthropic.claude-haiku-4-5-20251001-v1:0': 'Claude 4.5 Haiku (Fast)',
    'us.anthropic.claude-sonnet-4-20250514-v1:0': 'Claude Sonnet 4',
    'us.amazon.nova-lite-v1:0': 'Amazon Nova Lite (Fast)',
    'us.amazon.nova-pro-v1:0': 'Amazon Nova Pro (Balanced)',
}


@dataclass
class ProductionMeetingConfig:
    """Configuration for Production Meeting Agents."""

    agent_enabled: bool = True
    # Sonnet 5 for the daily briefing / executive summary: near-Opus quality on
    # analysis at Sonnet cost. Geo inference profile routes cross-region.
    default_model: str = 'us.anthropic.claude-sonnet-5'
    max_tokens: int = 4096
    timeout_seconds: int = 120

    # Meeting-specific configuration options
    meeting_focus: str = 'daily'  # 'daily', 'weekly', 'monthly'
    analysis_depth: str = 'standard'  # 'standard', 'comprehensive'
    enable_proactive_insights: bool = True

    # Agent specialization settings
    enable_production_agent: bool = True
    enable_quality_agent: bool = True
    enable_equipment_agent: bool = True
    enable_inventory_agent: bool = True

    # Meeting focus options
    MEETING_FOCUS_OPTIONS = {
        'daily': 'Daily Production Meeting',
        'weekly': 'Weekly Production Review',
        'monthly': 'Monthly Performance Analysis'
    }

    SUPPORTED_MODELS = SUPPORTED_MODELS

    @classmethod
    def get_model_display_names(cls) -> Dict[str, str]:
        return MODEL_DISPLAY_NAMES

    @classmethod
    def get_meeting_focus_display_names(cls) -> Dict[str, str]:
        return cls.MEETING_FOCUS_OPTIONS

    def is_agent_enabled(self, agent_type: str) -> bool:
        """Check if a specific agent type is enabled."""
        agent_settings = {
            'production': self.enable_production_agent,
            'quality': self.enable_quality_agent,
            'equipment': self.enable_equipment_agent,
            'inventory': self.enable_inventory_agent
        }
        return agent_settings.get(agent_type, False)


# Default configuration instance
default_config = ProductionMeetingConfig()
