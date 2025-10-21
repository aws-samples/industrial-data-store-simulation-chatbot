"""
Production Meeting Agents Module

This module provides intelligent agent-powered analysis for production meetings,
replacing direct Bedrock calls with Strands SDK agents while maintaining
the existing dashboard structure.
"""

from .agent_manager import ProductionMeetingAgentManager
from .config import ProductionMeetingConfig

__all__ = [
    'ProductionMeetingAgentManager',
    'ProductionMeetingConfig',
]