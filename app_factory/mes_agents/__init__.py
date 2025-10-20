"""
MES Agents module for Strands-based manufacturing analysis.

This module provides intelligent agents and tools for comprehensive
manufacturing execution system (MES) data analysis using the Strands SDK.
"""

from .agent_manager import MESAgentManager
from .config import AgentConfig, default_config
from .tools import run_sqlite_query, get_database_schema, create_intelligent_visualization

__version__ = "1.0.0"

__all__ = [
    "MESAgentManager",
    "AgentConfig", 
    "default_config",
    "run_sqlite_query",
    "get_database_schema",
    "create_intelligent_visualization"
]