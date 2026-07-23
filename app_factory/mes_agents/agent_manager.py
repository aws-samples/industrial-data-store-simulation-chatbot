"""
Thin session-level agent manager for the MES Chat UI.

The manager no longer holds a global agent; instead it provides factory methods
for creating per-session agents and helper utilities consumed by the Streamlit UI.
"""

from .config import AgentConfig, default_config, SUPPORTED_MODELS, MODEL_DISPLAY_NAMES
from .mes_analysis_agent import create_agent

__all__ = [
    "create_agent",
    "AgentConfig",
    "default_config",
    "SUPPORTED_MODELS",
    "MODEL_DISPLAY_NAMES",
]
