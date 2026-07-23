"""MES Agents package — Strands Agents SDK powered manufacturing analysis."""

from .config import AgentConfig, default_config, SUPPORTED_MODELS, MODEL_DISPLAY_NAMES
from .mes_analysis_agent import create_agent
from .tools import run_sqlite_query, get_database_schema, create_intelligent_visualization

__version__ = "2.0.0"

__all__ = [
    "AgentConfig",
    "default_config",
    "create_agent",
    "SUPPORTED_MODELS",
    "MODEL_DISPLAY_NAMES",
    "run_sqlite_query",
    "get_database_schema",
    "create_intelligent_visualization",
]
