"""
Configuration for Production Meeting Agents.
"""

from dataclasses import dataclass
from typing import Dict, List


@dataclass
class ProductionMeetingConfig:
    """Configuration for Production Meeting Agents."""
    
    agent_enabled: bool = True
    default_model: str = 'us.anthropic.claude-haiku-4-5-20251001-v1:0'
    timeout_seconds: int = 120
    max_query_steps: int = 5
    enable_progress_updates: bool = True
    
    # Meeting-specific configuration options
    meeting_focus: str = 'daily'  # 'daily', 'weekly', 'monthly'
    analysis_depth: str = 'standard'  # 'standard', 'comprehensive'
    enable_proactive_insights: bool = True
    visualization_theme: str = 'streamlit_default'
    
    # Agent specialization settings
    enable_production_agent: bool = True
    enable_quality_agent: bool = True
    enable_equipment_agent: bool = True
    enable_inventory_agent: bool = True
    
    # Meeting efficiency settings
    quick_briefing_timeout: int = 30  # seconds for quick daily briefings
    detailed_analysis_timeout: int = 180  # seconds for comprehensive analysis
    max_concurrent_agents: int = 3
    
    # Supported models
    SUPPORTED_MODELS = [
        'us.amazon.nova-lite-v1:0',
        'us.amazon.nova-pro-v1:0',
        'us.anthropic.claude-3-5-haiku-20241022-v1:0',
        'us.anthropic.claude-3-7-sonnet-20250219-v1:0',
        'us.anthropic.claude-sonnet-4-20250514-v1:0',
        'us.anthropic.claude-haiku-4-5-20251001-v1:0'
    ]
    
    # Meeting focus options
    MEETING_FOCUS_OPTIONS = {
        'daily': 'Daily Production Meeting',
        'weekly': 'Weekly Production Review',
        'monthly': 'Monthly Performance Analysis'
    }
    
    # Analysis depth options
    ANALYSIS_DEPTH_OPTIONS = {
        'standard': 'Standard Analysis (Quick insights)',
        'comprehensive': 'Comprehensive Analysis (Detailed investigation)'
    }
    
    @classmethod
    def get_model_display_names(cls) -> Dict[str, str]:
        """Get user-friendly display names for models."""
        return {
            'us.amazon.nova-lite-v1:0': 'Amazon Nova Lite (Fast)',
            'us.amazon.nova-pro-v1:0': 'Amazon Nova Pro (Balanced)',
            'us.anthropic.claude-3-5-haiku-20241022-v1:0': 'Claude 3.5 Haiku (Fast)',
            'us.anthropic.claude-3-7-sonnet-20250219-v1:0': 'Claude 3.7 Sonnet (Advanced)',
            'us.anthropic.claude-sonnet-4-20250514-v1:0': 'Claude 4 Sonnet (Advanced)',
            'us.anthropic.claude-haiku-4-5-20251001-v1:0': 'Claude 4.5 Haiku (Recommended)'
        }
    
    @classmethod
    def get_meeting_focus_display_names(cls) -> Dict[str, str]:
        """Get user-friendly display names for meeting focus options."""
        return cls.MEETING_FOCUS_OPTIONS
    
    @classmethod
    def get_analysis_depth_display_names(cls) -> Dict[str, str]:
        """Get user-friendly display names for analysis depth options."""
        return cls.ANALYSIS_DEPTH_OPTIONS
    
    def get_timeout_for_analysis_type(self, analysis_type: str = 'standard') -> int:
        """Get appropriate timeout based on analysis type."""
        if analysis_type == 'quick_briefing':
            return self.quick_briefing_timeout
        elif analysis_type == 'comprehensive':
            return self.detailed_analysis_timeout
        else:
            return self.timeout_seconds
    
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