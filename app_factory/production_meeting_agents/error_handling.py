"""
Enhanced Error Handling and Recovery for Production Meeting Agents.

This module provides comprehensive error handling capabilities specifically designed
for production meeting contexts, including:
- Intelligent error analysis and classification for manufacturing scenarios
- Multi-level recovery strategies focused on meeting efficiency
- Partial result presentation for timeouts during meetings
- Meeting-specific guidance and alternative suggestions

Key Components:
- ProductionMeetingErrorAnalyzer: Main error analysis engine for meeting contexts
- MeetingTimeoutHandler: Graceful timeout management for meeting scenarios
- MeetingPartialResultPresenter: Formats incomplete results for meeting use
- ProductionErrorContext: Structured error information with meeting context

Usage:
    analyzer = ProductionMeetingErrorAnalyzer()
    analysis = analyzer.analyze_error(error_context)
    # Returns comprehensive error analysis with meeting-focused recovery options
"""

import asyncio
import logging
import traceback
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, Union
from enum import Enum
from dataclasses import dataclass

from app_factory.shared.db_utils import days_ago


class MeetingErrorSeverity(Enum):
    """Error severity levels for production meeting contexts."""
    LOW = "low"              # Minor issues that don't impact meeting flow
    MEDIUM = "medium"        # Issues that may slow down meeting progress
    HIGH = "high"           # Issues that significantly impact meeting efficiency
    CRITICAL = "critical"   # Issues that prevent meeting from proceeding


class MeetingErrorCategory(Enum):
    """Categories of errors specific to production meeting scenarios."""
    DATABASE = "database"           # Database access issues
    AGENT = "agent"                # Agent processing issues
    TIMEOUT = "timeout"            # Meeting time constraint issues
    VALIDATION = "validation"      # Input validation issues
    VISUALIZATION = "visualization" # Chart/dashboard display issues
    CONFIGURATION = "configuration" # System configuration issues
    NETWORK = "network"            # Network connectivity issues
    PERMISSION = "permission"      # Access permission issues
    MEETING_CONTEXT = "meeting_context"  # Meeting-specific context issues
    UNKNOWN = "unknown"            # Unclassified errors


@dataclass
class ErrorContext:
    """Backward compatibility alias for ProductionErrorContext."""
    original_query: str
    error_message: str
    error_type: str
    timestamp: datetime
    execution_time: float

@dataclass
class ProductionErrorContext:
    """Context information for production meeting error analysis and recovery."""
    original_query: str
    error_message: str
    error_type: str
    timestamp: datetime
    execution_time: float
    meeting_type: str = 'daily'  # daily, weekly, monthly
    meeting_phase: str = 'analysis'  # briefing, analysis, discussion, wrap-up
    partial_results: Optional[Dict[str, Any]] = None
    stack_trace: Optional[str] = None
    agent_state: Optional[Dict[str, Any]] = None
    recovery_attempts: int = 0
    time_remaining: Optional[int] = None  # minutes remaining in meeting


@dataclass
class MeetingRecoveryAction:
    """Represents a recovery action that can be taken during meetings."""
    action_type: str
    description: str
    priority: int
    automated: bool
    time_estimate: int  # estimated time in seconds
    meeting_impact: str  # low, medium, high impact on meeting flow
    parameters: Dict[str, Any]


@dataclass
class MeetingErrorAnalysisResult:
    """Result of error analysis with meeting-focused recovery recommendations."""
    category: MeetingErrorCategory
    severity: MeetingErrorSeverity
    root_cause: str
    user_friendly_message: str
    technical_details: str
    recovery_actions: List[MeetingRecoveryAction]
    meeting_guidance: List[str]  # Meeting-specific guidance
    alternative_approaches: List[str]
    partial_results_available: bool
    meeting_impact_assessment: str
    suggested_meeting_adjustments: List[str]


class ProductionMeetingError(Exception):
    """Custom exception for production meeting agent errors."""
    pass


class ProductionMeetingErrorHandler:
    """Simple error handler for production meeting agents."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.error_analyzer = ProductionMeetingErrorAnalyzer()
    
    def handle_error(self, error: Exception, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Handle errors and return formatted error response."""
        error_context = ProductionErrorContext(
            original_query=context.get('query', '') if context else '',
            error_message=str(error),
            error_type=type(error).__name__,
            timestamp=datetime.now(),
            execution_time=0.0
        )
        
        analysis = self.error_analyzer.analyze_error(error_context)
        
        return {
            'success': False,
            'error': str(error),
            'error_type': analysis.category.value,
            'severity': analysis.severity.value,
            'user_message': analysis.user_friendly_message,
            'recovery_actions': [action.description for action in analysis.recovery_actions[:3]],
            'meeting_guidance': analysis.meeting_guidance,
            'alternatives': analysis.alternative_approaches[:3]
        }
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics."""
        return {
            'total_errors': 0,
            'error_categories': {},
            'recovery_success_rate': 0.0
        }


class ProductionMeetingErrorAnalyzer:
    """
    Intelligent error analyzer specifically designed for production meeting contexts.
    Provides meeting-focused error analysis, recovery mechanisms, and guidance.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.error_patterns = self._initialize_meeting_error_patterns()
        self.recovery_strategies = self._initialize_meeting_recovery_strategies()
        
    def analyze_error(self, error_context: ProductionErrorContext) -> MeetingErrorAnalysisResult:
        """
        Perform comprehensive error analysis with meeting context considerations.
        
        Args:
            error_context: Context information about the error including meeting details
            
        Returns:
            Comprehensive error analysis result with meeting-focused recommendations
        """
        try:
            # Classify the error with meeting context
            category = self._classify_meeting_error(error_context)
            severity = self._assess_meeting_severity(error_context, category)
            
            # Analyze root cause with meeting considerations
            root_cause = self._analyze_meeting_root_cause(error_context, category)
            
            # Generate meeting-appropriate user message
            user_message = self._generate_meeting_user_message(error_context, category, root_cause)
            
            # Generate meeting-focused recovery actions
            recovery_actions = self._generate_meeting_recovery_actions(error_context, category)
            
            # Generate meeting-specific guidance
            meeting_guidance = self._generate_meeting_guidance(error_context, category)
            
            # Generate alternative approaches for meetings
            alternatives = self._generate_meeting_alternatives(error_context, category)
            
            # Assess meeting impact
            meeting_impact = self._assess_meeting_impact(error_context, category, severity)
            
            # Suggest meeting adjustments
            meeting_adjustments = self._suggest_meeting_adjustments(error_context, category, severity)
            
            # Check for partial results
            partial_available = error_context.partial_results is not None
            
            return MeetingErrorAnalysisResult(
                category=category,
                severity=severity,
                root_cause=root_cause,
                user_friendly_message=user_message,
                technical_details=error_context.error_message,
                recovery_actions=recovery_actions,
                meeting_guidance=meeting_guidance,
                alternative_approaches=alternatives,
                partial_results_available=partial_available,
                meeting_impact_assessment=meeting_impact,
                suggested_meeting_adjustments=meeting_adjustments
            )
            
        except Exception as e:
            self.logger.error(f"Error during meeting error analysis: {e}")
            return self._create_meeting_fallback_analysis(error_context)
    
    def _classify_meeting_error(self, error_context: ProductionErrorContext) -> MeetingErrorCategory:
        """Classify the error with meeting context considerations."""
        error_msg = error_context.error_message.lower()
        error_type = error_context.error_type.lower()
        
        # Meeting context specific errors
        if error_context.meeting_phase == 'briefing' and 'timeout' in error_msg:
            return MeetingErrorCategory.MEETING_CONTEXT
        
        # Database errors (critical for production meetings)
        if any(pattern in error_msg for pattern in ['sqlite', 'database', 'no such table', 'no such column', 'syntax error']):
            return MeetingErrorCategory.DATABASE
        
        # Timeout errors (especially critical in meetings)
        if any(pattern in error_msg for pattern in ['timeout', 'timed out', 'asyncio.timeout']):
            return MeetingErrorCategory.TIMEOUT
        
        # Agent-specific errors
        if any(pattern in error_msg for pattern in ['agent', 'strands', 'model', 'llm']):
            return MeetingErrorCategory.AGENT
        
        # Validation errors
        if any(pattern in error_msg for pattern in ['validation', 'invalid', 'missing', 'required']):
            return MeetingErrorCategory.VALIDATION
        
        # Visualization errors (important for meeting dashboards)
        if any(pattern in error_msg for pattern in ['plotly', 'visualization', 'chart', 'graph', 'streamlit']):
            return MeetingErrorCategory.VISUALIZATION
        
        # Configuration errors
        if any(pattern in error_msg for pattern in ['config', 'configuration', 'setting']):
            return MeetingErrorCategory.CONFIGURATION
        
        # Network errors
        if any(pattern in error_msg for pattern in ['network', 'connection', 'http', 'api']):
            return MeetingErrorCategory.NETWORK
        
        # Permission errors
        if any(pattern in error_msg for pattern in ['permission', 'access', 'denied', 'unauthorized']):
            return MeetingErrorCategory.PERMISSION
        
        return MeetingErrorCategory.UNKNOWN
    
    def _assess_meeting_severity(self, error_context: ProductionErrorContext, category: MeetingErrorCategory) -> MeetingErrorSeverity:
        """Assess error severity with meeting time constraints in mind."""
        # Critical errors that stop the meeting
        if category in [MeetingErrorCategory.CONFIGURATION, MeetingErrorCategory.PERMISSION]:
            return MeetingErrorSeverity.CRITICAL
        
        # High severity for core meeting functionality
        if category in [MeetingErrorCategory.DATABASE, MeetingErrorCategory.MEETING_CONTEXT]:
            return MeetingErrorSeverity.HIGH
        
        # Consider meeting time constraints
        if error_context.time_remaining and error_context.time_remaining < 10:  # Less than 10 minutes
            if category == MeetingErrorCategory.TIMEOUT:
                return MeetingErrorSeverity.HIGH  # Timeouts are critical when time is short
            elif category == MeetingErrorCategory.AGENT:
                return MeetingErrorSeverity.HIGH  # Agent issues are critical in time-constrained meetings
        
        # Medium severity for partial functionality loss
        if category in [MeetingErrorCategory.TIMEOUT, MeetingErrorCategory.VISUALIZATION, MeetingErrorCategory.AGENT]:
            return MeetingErrorSeverity.MEDIUM
        
        # Low severity for minor issues
        return MeetingErrorSeverity.LOW
    
    def _analyze_meeting_root_cause(self, error_context: ProductionErrorContext, category: MeetingErrorCategory) -> str:
        """Analyze root cause with meeting context considerations."""
        error_msg = error_context.error_message.lower()
        
        if category == MeetingErrorCategory.DATABASE:
            if 'no such table' in error_msg:
                return "Production database table is missing or renamed - this may affect meeting data availability"
            elif 'no such column' in error_msg:
                return "Database schema has changed - column references need updating for meeting queries"
            elif 'syntax error' in error_msg:
                return "Production data query contains errors - preventing meeting analysis"
            elif 'locked' in error_msg:
                return "Production database is busy with other operations - may delay meeting analysis"
            else:
                return "Production database access issue - impacting meeting data retrieval"
        
        elif category == MeetingErrorCategory.TIMEOUT:
            if error_context.meeting_phase == 'briefing':
                return "Daily briefing generation is taking too long - may need to simplify analysis scope"
            elif error_context.execution_time > 60:
                return "Complex production analysis exceeded meeting time constraints"
            else:
                return "System performance issue causing delays during meeting"
        
        elif category == MeetingErrorCategory.AGENT:
            if 'model' in error_msg:
                return "AI analysis engine is unavailable - limiting meeting insights capability"
            elif 'strands' in error_msg:
                return "Agent framework integration issue - affecting meeting analysis tools"
            else:
                return "Meeting analysis agent failed - reducing available insights"
        
        elif category == MeetingErrorCategory.MEETING_CONTEXT:
            return "Meeting-specific configuration or timing issue affecting analysis flow"
        
        elif category == MeetingErrorCategory.VALIDATION:
            return "Meeting query parameters are invalid - check date ranges and filter criteria"
        
        elif category == MeetingErrorCategory.VISUALIZATION:
            return "Meeting dashboard visualization failed - data may still be available in text format"
        
        elif category == MeetingErrorCategory.CONFIGURATION:
            return "Production meeting system configuration needs attention"
        
        elif category == MeetingErrorCategory.NETWORK:
            return "Network connectivity issue affecting external production data sources"
        
        elif category == MeetingErrorCategory.PERMISSION:
            return "Insufficient access rights to production data needed for meeting analysis"
        
        else:
            return "Unknown issue occurred during meeting analysis"
    
    def _generate_meeting_user_message(self, error_context: ProductionErrorContext, category: MeetingErrorCategory, root_cause: str) -> str:
        """Generate user-friendly error messages appropriate for meeting contexts."""
        base_messages = {
            MeetingErrorCategory.DATABASE: "I'm having trouble accessing the production database for our meeting analysis.",
            MeetingErrorCategory.TIMEOUT: "The analysis is taking longer than our meeting schedule allows.",
            MeetingErrorCategory.AGENT: "I'm experiencing a technical issue that's limiting my analysis capabilities for this meeting.",
            MeetingErrorCategory.VALIDATION: "There's an issue with the meeting parameters or data filters.",
            MeetingErrorCategory.VISUALIZATION: "I had trouble creating the meeting dashboard visualization.",
            MeetingErrorCategory.CONFIGURATION: "There's a system configuration issue affecting our meeting tools.",
            MeetingErrorCategory.NETWORK: "I'm having connectivity issues that may affect external data access.",
            MeetingErrorCategory.PERMISSION: "I don't have the necessary access to complete this meeting analysis.",
            MeetingErrorCategory.MEETING_CONTEXT: "There's an issue with the meeting setup or timing configuration.",
            MeetingErrorCategory.UNKNOWN: "I encountered an unexpected issue during our meeting analysis."
        }
        
        base_message = base_messages.get(category, base_messages[MeetingErrorCategory.UNKNOWN])
        
        # Add meeting-specific context
        if error_context.meeting_phase == 'briefing':
            base_message += " This may affect our daily briefing preparation."
        elif error_context.time_remaining and error_context.time_remaining < 15:
            base_message += f" We have about {error_context.time_remaining} minutes remaining in our meeting."
        
        # Add recovery context
        if error_context.partial_results:
            base_message += " However, I do have some preliminary results we can review."
        elif category == MeetingErrorCategory.TIMEOUT:
            base_message += " Let me suggest a quicker approach to get the key information we need."
        
        return base_message
    
    def _generate_meeting_recovery_actions(self, error_context: ProductionErrorContext, category: MeetingErrorCategory) -> List[MeetingRecoveryAction]:
        """Generate meeting-focused recovery actions."""
        actions = []
        
        if category == MeetingErrorCategory.DATABASE:
            actions.extend([
                MeetingRecoveryAction(
                    action_type="quick_schema_check",
                    description="Quickly verify database structure for meeting queries",
                    priority=1,
                    automated=True,
                    time_estimate=10,
                    meeting_impact="low",
                    parameters={"tool": "get_database_schema", "quick_mode": True}
                ),
                MeetingRecoveryAction(
                    action_type="fallback_to_cached_data",
                    description="Use recent cached production data for meeting",
                    priority=2,
                    automated=True,
                    time_estimate=5,
                    meeting_impact="low",
                    parameters={"use_cache": True, "max_age_hours": 24}
                ),
                MeetingRecoveryAction(
                    action_type="simplified_meeting_query",
                    description="Use basic production queries for essential meeting metrics",
                    priority=3,
                    automated=True,
                    time_estimate=15,
                    meeting_impact="medium",
                    parameters={"query_type": "essential_metrics"}
                )
            ])
        
        elif category == MeetingErrorCategory.TIMEOUT:
            actions.extend([
                MeetingRecoveryAction(
                    action_type="present_partial_results",
                    description="Show available results and continue meeting",
                    priority=1,
                    automated=True,
                    time_estimate=2,
                    meeting_impact="low",
                    parameters={"show_partial": True}
                ),
                MeetingRecoveryAction(
                    action_type="quick_summary_mode",
                    description="Switch to rapid summary analysis for meeting efficiency",
                    priority=2,
                    automated=True,
                    time_estimate=30,
                    meeting_impact="medium",
                    parameters={"analysis_mode": "quick_summary"}
                ),
                MeetingRecoveryAction(
                    action_type="defer_detailed_analysis",
                    description="Schedule detailed analysis for after the meeting",
                    priority=3,
                    automated=False,
                    time_estimate=5,
                    meeting_impact="low",
                    parameters={"schedule_followup": True}
                )
            ])
        
        elif category == MeetingErrorCategory.AGENT:
            actions.extend([
                MeetingRecoveryAction(
                    action_type="fallback_to_basic_analysis",
                    description="Use simplified analysis without advanced AI features",
                    priority=1,
                    automated=True,
                    time_estimate=20,
                    meeting_impact="medium",
                    parameters={"analysis_level": "basic"}
                ),
                MeetingRecoveryAction(
                    action_type="direct_data_presentation",
                    description="Present raw production data with manual interpretation",
                    priority=2,
                    automated=True,
                    time_estimate=10,
                    meeting_impact="medium",
                    parameters={"format": "raw_data_tables"}
                ),
                MeetingRecoveryAction(
                    action_type="meeting_facilitator_mode",
                    description="Switch to manual meeting facilitation with basic data support",
                    priority=3,
                    automated=False,
                    time_estimate=0,
                    meeting_impact="high",
                    parameters={"manual_mode": True}
                )
            ])
        
        elif category == MeetingErrorCategory.VISUALIZATION:
            actions.extend([
                MeetingRecoveryAction(
                    action_type="table_format_fallback",
                    description="Present meeting data in table format instead of charts",
                    priority=1,
                    automated=True,
                    time_estimate=5,
                    meeting_impact="low",
                    parameters={"format": "tables"}
                ),
                MeetingRecoveryAction(
                    action_type="basic_charts_only",
                    description="Use simple chart types for meeting visualization",
                    priority=2,
                    automated=True,
                    time_estimate=10,
                    meeting_impact="low",
                    parameters={"chart_complexity": "basic"}
                )
            ])
        
        elif category == MeetingErrorCategory.MEETING_CONTEXT:
            actions.extend([
                MeetingRecoveryAction(
                    action_type="reset_meeting_context",
                    description="Reset meeting parameters to default configuration",
                    priority=1,
                    automated=True,
                    time_estimate=5,
                    meeting_impact="low",
                    parameters={"reset_to_defaults": True}
                ),
                MeetingRecoveryAction(
                    action_type="manual_meeting_setup",
                    description="Manually configure meeting parameters",
                    priority=2,
                    automated=False,
                    time_estimate=60,
                    meeting_impact="high",
                    parameters={"manual_setup": True}
                )
            ])
        
        else:
            # Generic meeting-appropriate recovery actions
            actions.extend([
                MeetingRecoveryAction(
                    action_type="quick_retry",
                    description="Quickly retry the operation",
                    priority=1,
                    automated=True,
                    time_estimate=10,
                    meeting_impact="low",
                    parameters={"max_retries": 1}
                ),
                MeetingRecoveryAction(
                    action_type="continue_meeting_without_feature",
                    description="Continue meeting without this specific analysis",
                    priority=2,
                    automated=False,
                    time_estimate=0,
                    meeting_impact="medium",
                    parameters={"skip_feature": True}
                )
            ])
        
        return sorted(actions, key=lambda x: (x.priority, x.time_estimate))
    
    def _generate_meeting_guidance(self, error_context: ProductionErrorContext, category: MeetingErrorCategory) -> List[str]:
        """Generate meeting-specific guidance for error situations."""
        guidance = []
        
        if category == MeetingErrorCategory.DATABASE:
            guidance.extend([
                "🏭 **Meeting Continuity**: We can proceed with cached production data while resolving database issues.",
                "📊 **Data Alternatives**: Consider using yesterday's production summary for trend analysis.",
                "⏰ **Time Management**: Database issues shouldn't delay critical meeting decisions."
            ])
        
        elif category == MeetingErrorCategory.TIMEOUT:
            guidance.extend([
                "⏱️ **Meeting Efficiency**: Focus on the most critical production issues first.",
                "🎯 **Priority Setting**: Identify must-discuss items vs. nice-to-have analysis.",
                "📋 **Action Items**: Document complex analysis needs for follow-up after the meeting."
            ])
        
        elif category == MeetingErrorCategory.AGENT:
            guidance.extend([
                "🤖 **Backup Plans**: Manual analysis methods can substitute for AI insights during meetings.",
                "👥 **Team Knowledge**: Leverage team expertise when automated analysis isn't available.",
                "📈 **Essential Metrics**: Focus on key performance indicators that don't require complex analysis."
            ])
        
        elif category == MeetingErrorCategory.VISUALIZATION:
            guidance.extend([
                "📊 **Alternative Formats**: Numbers and tables can be just as effective as charts in meetings.",
                "🗣️ **Verbal Summaries**: Sometimes discussing trends is more valuable than viewing charts.",
                "📋 **Meeting Notes**: Document visualization needs for post-meeting follow-up."
            ])
        
        elif category == MeetingErrorCategory.MEETING_CONTEXT:
            guidance.extend([
                "🔧 **Meeting Setup**: Verify meeting type and time range settings are correct.",
                "📅 **Schedule Flexibility**: Consider adjusting meeting scope if technical issues persist.",
                "🎯 **Focus Areas**: Prioritize the most critical production areas for discussion."
            ])
        
        else:
            guidance.extend([
                "🚀 **Meeting Momentum**: Don't let technical issues derail productive discussions.",
                "🤝 **Team Collaboration**: Use this as an opportunity for more interactive team analysis.",
                "📝 **Documentation**: Record technical issues for post-meeting resolution."
            ])
        
        return guidance
    
    def _generate_meeting_alternatives(self, error_context: ProductionErrorContext, category: MeetingErrorCategory) -> List[str]:
        """Generate meeting-appropriate alternative approaches."""
        alternatives = []
        query_lower = error_context.original_query.lower()
        
        # Meeting time-sensitive alternatives
        if error_context.time_remaining and error_context.time_remaining < 20:
            alternatives.extend([
                "Focus on the top 3 most critical production issues for today",
                "Review yesterday's key metrics and identify any immediate concerns",
                "Discuss known issues and their current status rather than discovering new ones"
            ])
        
        # Meeting phase-specific alternatives
        if error_context.meeting_phase == 'briefing':
            alternatives.extend([
                "Start with a verbal status update from team leads",
                "Review the production schedule and identify potential bottlenecks",
                "Focus on safety incidents and quality alerts first"
            ])
        elif error_context.meeting_phase == 'analysis':
            alternatives.extend([
                "Use manual calculation for key efficiency metrics",
                "Compare current performance to last week's results",
                "Focus on trend direction rather than precise calculations"
            ])
        
        # Category-specific meeting alternatives
        if category == MeetingErrorCategory.DATABASE:
            alternatives.extend([
                "Use the latest production report from the shift supervisor",
                "Review printed production logs if available",
                "Focus on verbal updates from work center leads"
            ])
        
        elif category == MeetingErrorCategory.TIMEOUT:
            alternatives.extend([
                "Break the analysis into smaller, focused questions",
                "Prioritize safety and quality issues over efficiency metrics",
                "Schedule a follow-up session for detailed analysis"
            ])
        
        # Domain-specific alternatives based on query content
        if any(term in query_lower for term in ['production', 'output', 'efficiency']):
            alternatives.extend([
                "Review production targets vs. actual output for key work centers",
                "Identify any equipment or staffing issues affecting today's production",
                "Check if any work orders are behind schedule"
            ])
        
        if any(term in query_lower for term in ['quality', 'defect', 'yield']):
            alternatives.extend([
                "Review any quality holds or customer complaints from the last 24 hours",
                "Check first-pass yield for critical products",
                "Discuss any process changes that might affect quality"
            ])
        
        if any(term in query_lower for term in ['equipment', 'machine', 'downtime']):
            alternatives.extend([
                "Review planned maintenance activities for today",
                "Check equipment status boards for any current issues",
                "Discuss any equipment performance concerns from the previous shift"
            ])
        
        if any(term in query_lower for term in ['inventory', 'stock', 'material']):
            alternatives.extend([
                "Review material shortage reports for today's production",
                "Check supplier delivery status for critical materials",
                "Identify any inventory issues that could affect this week's schedule"
            ])
        
        return alternatives[:6]  # Limit to top 6 alternatives for meeting efficiency
    
    def _assess_meeting_impact(self, error_context: ProductionErrorContext, category: MeetingErrorCategory, severity: MeetingErrorSeverity) -> str:
        """Assess the impact of the error on meeting effectiveness."""
        if severity == MeetingErrorSeverity.CRITICAL:
            return "High impact - may require rescheduling or switching to manual meeting format"
        elif severity == MeetingErrorSeverity.HIGH:
            if error_context.time_remaining and error_context.time_remaining < 15:
                return "Significant impact - recommend focusing on essential items only"
            else:
                return "Moderate impact - can work around with alternative approaches"
        elif severity == MeetingErrorSeverity.MEDIUM:
            return "Low to moderate impact - meeting can proceed with minor adjustments"
        else:
            return "Minimal impact - meeting can proceed normally with slight modifications"
    
    def _suggest_meeting_adjustments(self, error_context: ProductionErrorContext, category: MeetingErrorCategory, severity: MeetingErrorSeverity) -> List[str]:
        """Suggest specific adjustments to meeting flow based on error situation."""
        adjustments = []
        
        if severity in [MeetingErrorSeverity.CRITICAL, MeetingErrorSeverity.HIGH]:
            adjustments.extend([
                "Consider extending meeting by 10-15 minutes if schedule allows",
                "Focus on verbal updates and team discussion rather than data analysis",
                "Defer complex analysis to a follow-up session"
            ])
        
        if category == MeetingErrorCategory.TIMEOUT:
            adjustments.extend([
                "Switch to rapid-fire status updates from each area",
                "Use pre-prepared reports instead of live analysis",
                "Schedule detailed analysis for after the meeting"
            ])
        
        if category == MeetingErrorCategory.DATABASE:
            adjustments.extend([
                "Use manual data collection from work centers",
                "Focus on qualitative discussion of production issues",
                "Review trends from previous meetings instead of current data"
            ])
        
        if error_context.meeting_type == 'daily' and error_context.time_remaining and error_context.time_remaining < 10:
            adjustments.extend([
                "Limit discussion to safety incidents and critical quality issues",
                "Defer efficiency analysis to weekly meeting",
                "Focus on immediate action items only"
            ])
        
        return adjustments
    
    def _create_meeting_fallback_analysis(self, error_context: ProductionErrorContext) -> MeetingErrorAnalysisResult:
        """Create a basic error analysis when the main analysis fails."""
        return MeetingErrorAnalysisResult(
            category=MeetingErrorCategory.UNKNOWN,
            severity=MeetingErrorSeverity.MEDIUM,
            root_cause="Error analysis failed during meeting - unknown issue",
            user_friendly_message="I encountered an unexpected issue during our meeting analysis.",
            technical_details=error_context.error_message,
            recovery_actions=[
                MeetingRecoveryAction(
                    action_type="continue_meeting_manually",
                    description="Continue meeting with manual facilitation",
                    priority=1,
                    automated=False,
                    time_estimate=0,
                    meeting_impact="medium",
                    parameters={}
                )
            ],
            meeting_guidance=[
                "🛠️ Technical issues happen - the meeting can still be productive.",
                "👥 Use this as an opportunity for more team interaction and discussion."
            ],
            alternative_approaches=[
                "Proceed with verbal status updates from each area",
                "Focus on known issues and action item follow-up"
            ],
            partial_results_available=False,
            meeting_impact_assessment="Moderate impact - meeting can continue with manual facilitation",
            suggested_meeting_adjustments=[
                "Switch to discussion-based format",
                "Document technical issues for post-meeting resolution"
            ]
        )
    
    def _initialize_meeting_error_patterns(self) -> Dict[str, Any]:
        """Initialize error patterns specific to meeting contexts."""
        return {
            'database_patterns': [
                'no such table',
                'no such column', 
                'syntax error',
                'database is locked',
                'constraint failed',
                'production_data',
                'work_orders',
                'quality_data'
            ],
            'timeout_patterns': [
                'timeout',
                'timed out',
                'asyncio.timeout',
                'execution time exceeded',
                'meeting timeout',
                'briefing timeout'
            ],
            'agent_patterns': [
                'model error',
                'strands error',
                'agent failed',
                'llm error',
                'analysis failed',
                'meeting agent'
            ],
            'meeting_context_patterns': [
                'meeting configuration',
                'meeting type',
                'meeting phase',
                'briefing failed',
                'context error'
            ]
        }
    
    def _initialize_meeting_recovery_strategies(self) -> Dict[str, Any]:
        """Initialize recovery strategies optimized for meeting contexts."""
        return {
            'database': {
                'immediate': ['quick_schema_check', 'cached_data_fallback'],
                'fallback': ['simplified_queries', 'manual_data_entry'],
                'manual': ['verbal_updates', 'printed_reports']
            },
            'timeout': {
                'immediate': ['partial_results', 'quick_summary'],
                'fallback': ['defer_analysis', 'focus_priorities'],
                'manual': ['team_discussion', 'action_item_review']
            },
            'agent': {
                'immediate': ['basic_analysis', 'direct_data'],
                'fallback': ['manual_calculation', 'team_expertise'],
                'manual': ['facilitated_discussion', 'whiteboard_analysis']
            },
            'meeting_context': {
                'immediate': ['reset_context', 'default_settings'],
                'fallback': ['manual_setup', 'simplified_meeting'],
                'manual': ['traditional_meeting_format', 'paper_based']
            }
        }


class MeetingTimeoutHandler:
    """
    Specialized timeout handler optimized for production meeting scenarios.
    """
    
    def __init__(self, default_timeout: int = 120, quick_timeout: int = 30):
        self.default_timeout = default_timeout
        self.quick_timeout = quick_timeout
        self.logger = logging.getLogger(__name__)
    
    async def execute_with_meeting_timeout(
        self, 
        operation_func, 
        meeting_context: Dict[str, Any],
        *args, 
        timeout_override: Optional[int] = None,
        **kwargs
    ) -> Tuple[bool, Any, Optional[Dict]]:
        """
        Execute operation with meeting-appropriate timeout handling.
        
        Args:
            operation_func: The async function to execute
            meeting_context: Meeting context including time constraints
            *args: Arguments for the operation function
            timeout_override: Optional timeout override
            **kwargs: Keyword arguments for the operation function
            
        Returns:
            Tuple of (success, result, partial_results)
        """
        # Determine appropriate timeout based on meeting context
        timeout = self._determine_meeting_timeout(meeting_context, timeout_override)
        
        try:
            # Execute with meeting-appropriate timeout
            result = await asyncio.wait_for(
                operation_func(*args, **kwargs),
                timeout=timeout
            )
            return True, result, None
            
        except asyncio.TimeoutError:
            self.logger.warning(f"Meeting operation timed out after {timeout} seconds")
            
            # Collect meeting-appropriate partial results
            partial_results = await self._collect_meeting_partial_results(
                operation_func, meeting_context, args, kwargs
            )
            
            return False, None, partial_results
            
        except Exception as e:
            self.logger.error(f"Meeting operation failed: {e}")
            return False, str(e), None
    
    def _determine_meeting_timeout(self, meeting_context: Dict[str, Any], timeout_override: Optional[int]) -> int:
        """Determine appropriate timeout based on meeting context."""
        if timeout_override:
            return timeout_override
        
        meeting_type = meeting_context.get('meeting_type', 'daily')
        meeting_phase = meeting_context.get('meeting_phase', 'analysis')
        time_remaining = meeting_context.get('time_remaining')
        
        # Quick timeout for briefings
        if meeting_phase == 'briefing':
            return self.quick_timeout
        
        # Shorter timeout if meeting time is limited
        if time_remaining and time_remaining < 15:  # Less than 15 minutes
            return min(self.quick_timeout, time_remaining * 60 // 2)  # Half remaining time
        
        # Standard timeout for regular analysis
        return self.default_timeout
    
    async def _collect_meeting_partial_results(
        self, 
        operation_func, 
        meeting_context: Dict[str, Any],
        args, 
        kwargs
    ) -> Dict[str, Any]:
        """Collect partial results appropriate for meeting contexts."""
        partial_results = {
            'status': 'meeting_timeout',
            'message': 'Analysis timed out during meeting - partial results available',
            'timestamp': datetime.now().isoformat(),
            'meeting_context': meeting_context,
            'collected_data': {}
        }
        
        try:
            # Meeting-specific partial result collection
            if 'query' in kwargs:
                # Suggest a simplified query for quick results
                simplified_query = self._create_meeting_quick_query(kwargs['query'])
                partial_results['quick_alternative'] = simplified_query
            
            # Add meeting-appropriate suggestions
            partial_results['meeting_suggestions'] = [
                "Continue with verbal status updates",
                "Focus on critical issues only",
                "Schedule detailed analysis for after meeting"
            ]
            
        except Exception as e:
            self.logger.debug(f"Could not collect meeting partial results: {e}")
        
        return partial_results
    
    def _create_meeting_quick_query(self, original_query: str) -> str:
        """Create a quick version of a query suitable for meeting time constraints."""
        query_lower = original_query.lower()

        # Add aggressive limits for meeting efficiency
        if 'limit' not in query_lower:
            original_query += ' LIMIT 20'

        # Focus on recent data for meetings (use DB-agnostic date)
        if 'where' not in query_lower and any(term in query_lower for term in ['production', 'quality', 'equipment']):
            yesterday = days_ago(1)
            original_query += f" WHERE date >= '{yesterday}'"

        return original_query


class MeetingPartialResultPresenter:
    """
    Handles presentation of partial results optimized for meeting contexts.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def format_meeting_partial_results(
        self, 
        partial_data: Dict[str, Any], 
        original_query: str,
        meeting_context: Dict[str, Any],
        error_context: Optional[ProductionErrorContext] = None
    ) -> Dict[str, Any]:
        """
        Format partial results for meeting presentation.
        
        Args:
            partial_data: Partial results data
            original_query: Original user query
            meeting_context: Meeting context information
            error_context: Optional error context
            
        Returns:
            Formatted partial results optimized for meeting use
        """
        formatted_result = {
            'success': False,
            'partial_success': True,
            'original_query': original_query,
            'status': 'meeting_partial_results',
            'message': self._generate_meeting_partial_message(meeting_context),
            'partial_results': partial_data,
            'meeting_context': meeting_context,
            'timestamp': datetime.now().isoformat()
        }
        
        # Add meeting-specific guidance
        formatted_result['meeting_guidance'] = self._generate_partial_meeting_guidance(
            meeting_context, partial_data
        )
        
        # Add quick alternatives for meeting efficiency
        formatted_result['quick_alternatives'] = self._generate_meeting_quick_alternatives(
            original_query, meeting_context
        )
        
        # Add time management suggestions
        formatted_result['time_management'] = self._generate_time_management_suggestions(
            meeting_context
        )
        
        return formatted_result
    
    def _generate_meeting_partial_message(self, meeting_context: Dict[str, Any]) -> str:
        """Generate meeting-appropriate message for partial results."""
        meeting_type = meeting_context.get('meeting_type', 'daily')
        time_remaining = meeting_context.get('time_remaining')
        
        base_message = "I have some preliminary results for our meeting."
        
        if time_remaining and time_remaining < 10:
            base_message += f" With {time_remaining} minutes left, let's focus on the key findings."
        elif meeting_type == 'daily':
            base_message += " Here's what I found so far for our daily review."
        
        return base_message
    
    def _generate_partial_meeting_guidance(
        self, 
        meeting_context: Dict[str, Any], 
        partial_data: Dict[str, Any]
    ) -> List[str]:
        """Generate guidance for using partial results in meetings."""
        guidance = []
        
        if partial_data.get('collected_data'):
            guidance.append("✅ Use the available data to start the discussion")
        
        guidance.extend([
            "🎯 Focus on the most critical issues first",
            "👥 Engage the team for additional insights",
            "📋 Document items needing follow-up analysis"
        ])
        
        if meeting_context.get('time_remaining', 0) < 15:
            guidance.append("⏰ Prioritize immediate action items")
        
        return guidance
    
    def _generate_meeting_quick_alternatives(
        self, 
        original_query: str, 
        meeting_context: Dict[str, Any]
    ) -> List[str]:
        """Generate quick alternatives suitable for meeting time constraints."""
        alternatives = []
        query_lower = original_query.lower()
        
        # Quick alternatives based on query type
        if any(term in query_lower for term in ['production', 'output']):
            alternatives.extend([
                "Check yesterday's production summary",
                "Review current shift performance",
                "Identify any immediate bottlenecks"
            ])
        
        if any(term in query_lower for term in ['quality', 'defect']):
            alternatives.extend([
                "Review any quality alerts from last 24 hours",
                "Check first-pass yield for key products",
                "Discuss any customer complaints"
            ])
        
        if any(term in query_lower for term in ['equipment', 'downtime']):
            alternatives.extend([
                "Review equipment status board",
                "Check planned maintenance for today",
                "Identify any current equipment issues"
            ])
        
        return alternatives[:4]  # Limit for meeting efficiency
    
    def _generate_time_management_suggestions(self, meeting_context: Dict[str, Any]) -> List[str]:
        """Generate time management suggestions for meetings."""
        suggestions = []
        time_remaining = meeting_context.get('time_remaining', 30)
        
        if time_remaining < 10:
            suggestions.extend([
                "Focus on safety and quality issues only",
                "Defer detailed analysis to follow-up",
                "Identify immediate action items"
            ])
        elif time_remaining < 20:
            suggestions.extend([
                "Prioritize critical production issues",
                "Use rapid-fire status updates",
                "Schedule complex analysis for later"
            ])
        else:
            suggestions.extend([
                "Continue with planned meeting agenda",
                "Allow time for team discussion",
                "Document follow-up items"
            ])
        
        return suggestions

# Backward compatibility aliases
IntelligentErrorAnalyzer = ProductionMeetingErrorAnalyzer