"""
Error handling for MES Agents.

Provides IntelligentErrorAnalyzer for classifying and suggesting recovery
from database and agent errors.
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from enum import Enum
from dataclasses import dataclass


class ErrorSeverity(Enum):
    """Error severity levels for classification and handling."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Categories of errors for targeted handling."""
    DATABASE = "database"
    AGENT = "agent"
    TIMEOUT = "timeout"
    VALIDATION = "validation"
    VISUALIZATION = "visualization"
    CONFIGURATION = "configuration"
    NETWORK = "network"
    PERMISSION = "permission"
    UNKNOWN = "unknown"


@dataclass
class ErrorContext:
    """Context information for error analysis and recovery."""
    original_query: str
    error_message: str
    error_type: str
    timestamp: datetime
    execution_time: float
    partial_results: Optional[Dict[str, Any]] = None
    stack_trace: Optional[str] = None
    agent_state: Optional[Dict[str, Any]] = None
    recovery_attempts: int = 0


@dataclass
class RecoveryAction:
    """Represents a recovery action that can be taken."""
    action_type: str
    description: str
    priority: int
    automated: bool
    parameters: Dict[str, Any]


@dataclass
class ErrorAnalysisResult:
    """Result of error analysis with recovery recommendations."""
    category: ErrorCategory
    severity: ErrorSeverity
    root_cause: str
    user_friendly_message: str
    technical_details: str
    recovery_actions: List[RecoveryAction]
    educational_content: List[str]
    alternative_approaches: List[str]
    partial_results_available: bool


class IntelligentErrorAnalyzer:
    """
    Intelligent error analyzer that provides comprehensive error analysis,
    recovery mechanisms, and educational guidance.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.error_patterns = self._initialize_error_patterns()
        self.recovery_strategies = self._initialize_recovery_strategies()
        
    def analyze_error(self, error_context: ErrorContext) -> ErrorAnalysisResult:
        """
        Perform comprehensive error analysis and generate recovery recommendations.
        
        Args:
            error_context: Context information about the error
            
        Returns:
            Comprehensive error analysis result
        """
        try:
            # Classify the error
            category = self._classify_error(error_context)
            severity = self._assess_severity(error_context, category)
            
            # Analyze root cause
            root_cause = self._analyze_root_cause(error_context, category)
            
            # Generate user-friendly message
            user_message = self._generate_user_friendly_message(error_context, category, root_cause)
            
            # Generate recovery actions
            recovery_actions = self._generate_recovery_actions(error_context, category)
            
            # Generate educational content
            educational_content = self._generate_educational_content(error_context, category)
            
            # Generate alternative approaches
            alternatives = self._generate_alternative_approaches(error_context, category)
            
            # Check for partial results
            partial_available = error_context.partial_results is not None
            
            return ErrorAnalysisResult(
                category=category,
                severity=severity,
                root_cause=root_cause,
                user_friendly_message=user_message,
                technical_details=error_context.error_message,
                recovery_actions=recovery_actions,
                educational_content=educational_content,
                alternative_approaches=alternatives,
                partial_results_available=partial_available
            )
            
        except Exception as e:
            self.logger.error(f"Error during error analysis: {e}")
            return self._create_fallback_analysis(error_context)
    
    def _classify_error(self, error_context: ErrorContext) -> ErrorCategory:
        """Classify the error into appropriate category."""
        error_msg = error_context.error_message.lower()
        error_type = error_context.error_type.lower()
        
        # Database errors
        if any(pattern in error_msg for pattern in ['sqlite', 'database', 'no such table', 'no such column', 'syntax error']):
            return ErrorCategory.DATABASE
        
        # Timeout errors
        if any(pattern in error_msg for pattern in ['timeout', 'timed out', 'asyncio.timeout']):
            return ErrorCategory.TIMEOUT
        
        # Agent-specific errors
        if any(pattern in error_msg for pattern in ['agent', 'strands', 'model', 'llm']):
            return ErrorCategory.AGENT
        
        # Validation errors
        if any(pattern in error_msg for pattern in ['validation', 'invalid', 'missing', 'required']):
            return ErrorCategory.VALIDATION
        
        # Visualization errors
        if any(pattern in error_msg for pattern in ['plotly', 'visualization', 'chart', 'graph']):
            return ErrorCategory.VISUALIZATION
        
        # Configuration errors
        if any(pattern in error_msg for pattern in ['config', 'configuration', 'setting']):
            return ErrorCategory.CONFIGURATION
        
        # Network errors
        if any(pattern in error_msg for pattern in ['network', 'connection', 'http', 'api']):
            return ErrorCategory.NETWORK
        
        # Permission errors
        if any(pattern in error_msg for pattern in ['permission', 'access', 'denied', 'unauthorized']):
            return ErrorCategory.PERMISSION
        
        return ErrorCategory.UNKNOWN
    
    def _assess_severity(self, error_context: ErrorContext, category: ErrorCategory) -> ErrorSeverity:
        """Assess the severity of the error."""
        # Critical errors that prevent any functionality
        if category in [ErrorCategory.CONFIGURATION, ErrorCategory.PERMISSION]:
            return ErrorSeverity.CRITICAL
        
        # High severity for core functionality issues
        if category in [ErrorCategory.DATABASE, ErrorCategory.AGENT]:
            return ErrorSeverity.HIGH
        
        # Medium severity for partial functionality loss
        if category in [ErrorCategory.TIMEOUT, ErrorCategory.VISUALIZATION]:
            return ErrorSeverity.MEDIUM
        
        # Low severity for minor issues
        return ErrorSeverity.LOW
    
    def _analyze_root_cause(self, error_context: ErrorContext, category: ErrorCategory) -> str:
        """Analyze the root cause of the error."""
        error_msg = error_context.error_message.lower()
        
        if category == ErrorCategory.DATABASE:
            if 'no such table' in error_msg:
                return "Referenced table does not exist in the database"
            elif 'no such column' in error_msg:
                return "Referenced column does not exist in the specified table"
            elif 'syntax error' in error_msg:
                return "SQL query contains syntax errors"
            elif 'locked' in error_msg:
                return "Database is locked by another process"
            else:
                return "Database operation failed due to query or connection issues"
        
        elif category == ErrorCategory.TIMEOUT:
            if error_context.execution_time > 60:
                return "Query execution exceeded time limit due to complex analysis"
            else:
                return "Operation timed out due to system load or network issues"
        
        elif category == ErrorCategory.AGENT:
            if 'model' in error_msg:
                return "AI model is unavailable or misconfigured"
            elif 'strands' in error_msg:
                return "Strands SDK integration issue"
            else:
                return "Agent execution failed due to internal processing error"
        
        elif category == ErrorCategory.VALIDATION:
            return "Input validation failed - required parameters missing or invalid"
        
        elif category == ErrorCategory.VISUALIZATION:
            return "Data visualization generation failed due to data format or configuration issues"
        
        elif category == ErrorCategory.CONFIGURATION:
            return "System configuration is invalid or incomplete"
        
        elif category == ErrorCategory.NETWORK:
            return "Network connectivity issue preventing external service access"
        
        elif category == ErrorCategory.PERMISSION:
            return "Insufficient permissions to access required resources"
        
        else:
            return "Unknown error occurred during operation"
    
    def _generate_user_friendly_message(self, error_context: ErrorContext, category: ErrorCategory, root_cause: str) -> str:
        """Generate a user-friendly error message."""
        base_messages = {
            ErrorCategory.DATABASE: "I encountered an issue while accessing the manufacturing database.",
            ErrorCategory.TIMEOUT: "The analysis is taking longer than expected.",
            ErrorCategory.AGENT: "I'm experiencing a technical issue with my analysis capabilities.",
            ErrorCategory.VALIDATION: "There's an issue with the information provided for analysis.",
            ErrorCategory.VISUALIZATION: "I had trouble creating the requested visualization.",
            ErrorCategory.CONFIGURATION: "There's a system configuration issue that needs attention.",
            ErrorCategory.NETWORK: "I'm having trouble connecting to external services.",
            ErrorCategory.PERMISSION: "I don't have the necessary permissions to complete this request.",
            ErrorCategory.UNKNOWN: "I encountered an unexpected issue while processing your request."
        }
        
        base_message = base_messages.get(category, base_messages[ErrorCategory.UNKNOWN])
        
        # Add context-specific details
        if category == ErrorCategory.DATABASE:
            if 'no such table' in error_context.error_message.lower():
                base_message += " The table you're asking about doesn't exist in our database."
            elif 'no such column' in error_context.error_message.lower():
                base_message += " The column you're referencing isn't available in that table."
        
        elif category == ErrorCategory.TIMEOUT:
            if error_context.partial_results:
                base_message += " However, I was able to gather some preliminary results."
            else:
                base_message += " Let me suggest a simpler approach to get you the information you need."
        
        return base_message
    
    def _generate_recovery_actions(self, error_context: ErrorContext, category: ErrorCategory) -> List[RecoveryAction]:
        """Generate specific recovery actions based on error category."""
        actions = []
        
        if category == ErrorCategory.DATABASE:
            actions.extend([
                RecoveryAction(
                    action_type="schema_check",
                    description="Check database schema to verify table and column names",
                    priority=1,
                    automated=True,
                    parameters={"tool": "get_database_schema"}
                ),
                RecoveryAction(
                    action_type="query_simplification",
                    description="Simplify the query to use basic table operations",
                    priority=2,
                    automated=True,
                    parameters={"approach": "basic_select"}
                ),
                RecoveryAction(
                    action_type="manual_verification",
                    description="Manually verify the query syntax and table references",
                    priority=3,
                    automated=False,
                    parameters={}
                )
            ])
        
        elif category == ErrorCategory.TIMEOUT:
            actions.extend([
                RecoveryAction(
                    action_type="partial_results",
                    description="Present any partial results that were obtained",
                    priority=1,
                    automated=True,
                    parameters={"show_partial": True}
                ),
                RecoveryAction(
                    action_type="query_optimization",
                    description="Optimize the query to reduce execution time",
                    priority=2,
                    automated=True,
                    parameters={"add_limits": True, "simplify_joins": True}
                ),
                RecoveryAction(
                    action_type="incremental_analysis",
                    description="Break down the analysis into smaller, manageable steps",
                    priority=3,
                    automated=True,
                    parameters={"step_by_step": True}
                )
            ])
        
        elif category == ErrorCategory.AGENT:
            actions.extend([
                RecoveryAction(
                    action_type="model_fallback",
                    description="Try with a different AI model",
                    priority=1,
                    automated=True,
                    parameters={"fallback_model": True}
                ),
                RecoveryAction(
                    action_type="simplified_analysis",
                    description="Perform a simplified version of the analysis",
                    priority=2,
                    automated=True,
                    parameters={"reduce_complexity": True}
                ),
                RecoveryAction(
                    action_type="direct_query",
                    description="Execute a direct database query without agent processing",
                    priority=3,
                    automated=True,
                    parameters={"bypass_agent": True}
                )
            ])
        
        elif category == ErrorCategory.VISUALIZATION:
            actions.extend([
                RecoveryAction(
                    action_type="table_fallback",
                    description="Present results in table format instead of charts",
                    priority=1,
                    automated=True,
                    parameters={"format": "table"}
                ),
                RecoveryAction(
                    action_type="simple_chart",
                    description="Create a basic chart with minimal configuration",
                    priority=2,
                    automated=True,
                    parameters={"chart_type": "simple"}
                )
            ])
        
        else:
            # Generic recovery actions
            actions.extend([
                RecoveryAction(
                    action_type="retry",
                    description="Retry the operation with the same parameters",
                    priority=1,
                    automated=True,
                    parameters={"max_retries": 2}
                ),
                RecoveryAction(
                    action_type="alternative_approach",
                    description="Try an alternative approach to achieve the same goal",
                    priority=2,
                    automated=True,
                    parameters={}
                )
            ])
        
        return sorted(actions, key=lambda x: x.priority)
    
    def _generate_educational_content(self, error_context: ErrorContext, category: ErrorCategory) -> List[str]:
        """Generate educational content to help users understand and avoid similar errors."""
        educational_content = []
        
        if category == ErrorCategory.DATABASE:
            educational_content.extend([
                "💡 **Database Tips**: Use the schema tool to explore available tables and columns before writing queries.",
                "📚 **SQL Best Practices**: Start with simple SELECT statements and gradually add complexity.",
                "🔍 **Troubleshooting**: Check table names for typos - they're case-sensitive in some databases."
            ])
        
        elif category == ErrorCategory.TIMEOUT:
            educational_content.extend([
                "⏱️ **Performance Tips**: Large datasets may require more specific filters to reduce processing time.",
                "🎯 **Query Optimization**: Use WHERE clauses to limit data and LIMIT clauses for testing.",
                "📊 **Analysis Strategy**: Break complex questions into smaller, focused queries."
            ])
        
        elif category == ErrorCategory.AGENT:
            educational_content.extend([
                "🤖 **Agent Capabilities**: AI agents work best with clear, specific questions about manufacturing data.",
                "💭 **Query Formulation**: Provide context about what you want to analyze and why.",
                "🔄 **Iterative Approach**: Start with simple questions and build up to more complex analysis."
            ])
        
        elif category == ErrorCategory.VISUALIZATION:
            educational_content.extend([
                "📈 **Visualization Guidelines**: Charts work best with numeric data and clear categories.",
                "🎨 **Chart Selection**: The AI chooses chart types based on your data characteristics.",
                "📋 **Data Format**: Ensure your query returns data in a format suitable for visualization."
            ])
        
        else:
            educational_content.extend([
                "🛠️ **General Tips**: Try simpler queries first to test connectivity and data access.",
                "📖 **Learning Approach**: Each error is a learning opportunity to improve your analysis skills.",
                "🤝 **Getting Help**: Don't hesitate to ask for help with query formulation or data exploration."
            ])
        
        return educational_content
    
    def _generate_alternative_approaches(self, error_context: ErrorContext, category: ErrorCategory) -> List[str]:
        """Generate alternative approaches to achieve the user's goal."""
        alternatives = []
        query_lower = error_context.original_query.lower()
        
        if category == ErrorCategory.DATABASE:
            alternatives.extend([
                "Try exploring the database schema first to understand available data",
                "Start with a simple 'SELECT * FROM table_name LIMIT 10' to see the data structure",
                "Use the schema tool to find the correct table and column names"
            ])
        
        elif category == ErrorCategory.TIMEOUT:
            alternatives.extend([
                "Add date filters to limit the data range (e.g., 'last 30 days')",
                "Focus on a specific work center or product line first",
                "Ask for summary statistics instead of detailed records"
            ])
        
        # Domain-specific alternatives based on query content
        if any(term in query_lower for term in ['production', 'output', 'efficiency']):
            alternatives.extend([
                "Ask about production metrics for a specific time period",
                "Focus on one work center or production line at a time",
                "Request summary statistics like total output or average efficiency"
            ])
        
        if any(term in query_lower for term in ['quality', 'defect', 'yield']):
            alternatives.extend([
                "Analyze quality metrics for a specific product or time range",
                "Look at defect trends over the last month",
                "Compare quality metrics between different shifts or operators"
            ])
        
        if any(term in query_lower for term in ['equipment', 'machine', 'downtime']):
            alternatives.extend([
                "Check equipment status for specific machines",
                "Analyze downtime patterns for the last week",
                "Compare equipment performance across different work centers"
            ])
        
        if any(term in query_lower for term in ['inventory', 'stock', 'material']):
            alternatives.extend([
                "Check current stock levels for specific items",
                "Analyze inventory consumption patterns",
                "Look at supplier performance for key materials"
            ])
        
        # If no specific alternatives generated, provide generic ones
        if not alternatives:
            alternatives.extend([
                "Try breaking your question into smaller, more specific parts",
                "Start with basic data exploration to understand what's available",
                "Ask for help with query formulation if you're unsure about the approach"
            ])
        
        return alternatives[:5]  # Limit to top 5 alternatives
    
    def _create_fallback_analysis(self, error_context: ErrorContext) -> ErrorAnalysisResult:
        """Create a basic error analysis when the main analysis fails."""
        return ErrorAnalysisResult(
            category=ErrorCategory.UNKNOWN,
            severity=ErrorSeverity.MEDIUM,
            root_cause="Error analysis failed - unknown issue",
            user_friendly_message="I encountered an unexpected issue while processing your request.",
            technical_details=error_context.error_message,
            recovery_actions=[
                RecoveryAction(
                    action_type="retry",
                    description="Try the operation again",
                    priority=1,
                    automated=True,
                    parameters={}
                )
            ],
            educational_content=[
                "🛠️ Sometimes temporary issues resolve themselves with a retry.",
                "📞 If the problem persists, please contact system support."
            ],
            alternative_approaches=[
                "Try a simpler version of your question",
                "Check if the system is experiencing high load"
            ],
            partial_results_available=False
        )
    
    def _initialize_error_patterns(self) -> Dict[str, Any]:
        """Initialize common error patterns for pattern matching."""
        return {
            'database_patterns': [
                'no such table',
                'no such column', 
                'syntax error',
                'database is locked',
                'constraint failed'
            ],
            'timeout_patterns': [
                'timeout',
                'timed out',
                'asyncio.timeout',
                'execution time exceeded'
            ],
            'agent_patterns': [
                'model error',
                'strands error',
                'agent failed',
                'llm error'
            ]
        }
    
    def _initialize_recovery_strategies(self) -> Dict[str, Any]:
        """Initialize recovery strategies for different error types."""
        return {
            'database': {
                'immediate': ['schema_check', 'query_validation'],
                'fallback': ['simplified_query', 'table_exploration'],
                'manual': ['query_rewrite', 'data_verification']
            },
            'timeout': {
                'immediate': ['partial_results', 'query_optimization'],
                'fallback': ['incremental_analysis', 'simplified_approach'],
                'manual': ['manual_optimization', 'system_check']
            },
            'agent': {
                'immediate': ['model_fallback', 'simplified_analysis'],
                'fallback': ['direct_query', 'basic_processing'],
                'manual': ['configuration_check', 'system_restart']
            }
        }