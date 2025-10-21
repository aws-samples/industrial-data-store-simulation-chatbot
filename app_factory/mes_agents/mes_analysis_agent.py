"""
MES Analysis Agent using Strands Agent-as-Tools Pattern.

This module implements the MES analysis functionality using the Strands agent-as-tools pattern,
where the agent is wrapped as a tool that can be used by other systems.

Key Features:
- Agent-as-tools pattern for clean integration
- Multi-domain manufacturing expertise
- Intelligent error handling and recovery
- Educational guidance and suggestions
- Progress tracking and comprehensive analysis

Usage:
    result = mes_analysis_tool("Show me production efficiency trends")
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from strands import Agent, tool
from .tools.database_tools import run_sqlite_query, get_database_schema
from .tools.visualization_tools import create_intelligent_visualization
from .config import AgentConfig
from .error_handling import IntelligentErrorAnalyzer, ErrorContext, PartialResultPresenter

# Global configuration and error handling components
_config = AgentConfig()
_error_analyzer = IntelligentErrorAnalyzer()
_partial_presenter = PartialResultPresenter()
_progress_updates = []
_logger = logging.getLogger(__name__)


def _get_system_prompt() -> str:
    """Get the system prompt for the MES Analysis Agent."""
    return """You are a comprehensive Manufacturing Execution System (MES) Analysis Agent with deep expertise across all manufacturing domains. Your role is to provide intelligent, multi-step analysis of manufacturing data to help users understand production performance, quality issues, equipment efficiency, and inventory management.

## Your Expertise Areas:

### Production Analysis
- Work order performance and scheduling optimization
- Production efficiency metrics and trend analysis
- Bottleneck identification and capacity planning
- Throughput analysis and cycle time optimization
- Production planning and resource allocation

### Quality Analysis  
- Defect pattern recognition and root cause analysis
- Quality control metrics and yield optimization
- Statistical process control and capability analysis
- Cross-product quality correlation analysis
- Supplier quality performance assessment

### Equipment Analysis
- Overall Equipment Effectiveness (OEE) calculation and analysis
- Predictive maintenance recommendations
- Downtime analysis and prevention strategies
- Equipment performance trending
- Maintenance scheduling optimization

### Inventory Analysis
- Stock level optimization and reorder point calculation
- Consumption pattern analysis and demand forecasting
- Supplier performance and supply chain risk assessment
- Inventory turnover and carrying cost analysis
- Material requirements planning (MRP) support

### Multi-Domain Analysis
- Complex queries requiring data from multiple manufacturing areas
- Holistic manufacturing performance assessment
- Integrated recommendations across all domains
- Cross-functional impact analysis

## Your Capabilities:

1. **Intelligent Query Processing**: Break down complex questions into logical analysis steps
2. **Multi-Step Analysis**: Perform sophisticated reasoning requiring multiple database operations
3. **Data Correlation**: Connect information across different manufacturing domains
4. **Insight Generation**: Provide actionable recommendations based on data analysis
5. **Visualization Selection**: Choose appropriate charts and graphs for different data types
6. **Error Recovery**: Handle database issues and provide helpful guidance
7. **Educational Guidance**: Explain manufacturing concepts and suggest better queries

## Available Tools:

1. **run_sqlite_query**: Execute SQL queries on the MES database with intelligent error handling
2. **get_database_schema**: Retrieve database structure and table information
3. **create_intelligent_visualization**: Generate appropriate charts based on data characteristics

## Analysis Approach:

1. **Understand the Question**: Analyze what the user wants to know and identify the manufacturing domain(s) involved
2. **Plan the Analysis**: Break complex questions into logical steps and determine required data
3. **Execute Systematically**: Perform database queries and analysis in a logical sequence
4. **Synthesize Results**: Combine findings from multiple queries into comprehensive insights
5. **Provide Recommendations**: Offer actionable advice based on the analysis
6. **Suggest Follow-ups**: Recommend related analyses that might be valuable

## Communication Style:

- Be clear and professional in your explanations
- Provide context for manufacturing metrics and concepts
- Explain your reasoning for analysis choices
- Offer specific, actionable recommendations
- Suggest improvements and optimizations where appropriate
- Use appropriate manufacturing terminology while remaining accessible

Adjust your response depth based on the user's needs:
- **Standard**: Clear answers with key context and relevant metrics (default)
- **Comprehensive**: Full analysis with insights, recommendations, and visualizations

Always provide helpful, accurate information that matches the requested level of detail."""


@tool
def mes_analysis_tool(query: str) -> str:
    """
    Process and respond to manufacturing analysis queries using a specialized MES agent.
    
    This tool provides comprehensive analysis of Manufacturing Execution System (MES) data
    across all manufacturing domains including production, quality, equipment, and inventory.
    
    Args:
        query: The manufacturing analysis question or request
        
    Returns:
        Comprehensive analysis results with insights and recommendations
    """
    global _progress_updates, _logger
    
    try:
        _logger.info(f"Processing MES analysis query: {query[:100]}...")
        
        # Reset progress tracking
        _progress_updates = []
        _add_progress_update("Starting MES analysis...", "initializing")
        
        # Create the MES analysis agent
        _add_progress_update("Initializing MES analysis agent...", "planning")
        
        mes_agent = Agent(
            system_prompt=_get_system_prompt(),
            tools=[run_sqlite_query, get_database_schema, create_intelligent_visualization],
            model=_config.default_model
        )
        
        # Format the query based on analysis depth
        if _config.analysis_depth == "standard":
            formatted_query = f"""Answer this manufacturing question: "{query}"

1. Use the database tools to get the requested information
2. Provide a clear, direct answer with key context
3. Include relevant metrics or data points
4. Keep the response focused and practical

Avoid extensive analysis unless specifically requested."""
            
        else:  # comprehensive
            formatted_query = f"""Please analyze this manufacturing query comprehensively: "{query}"

Follow these steps:
1. Identify the manufacturing domain(s) involved (production, quality, equipment, inventory)
2. Determine what data is needed and plan your analysis approach
3. Execute the necessary database queries and analysis
4. Synthesize findings and provide insights
5. Offer actionable recommendations and suggest follow-up analyses

Use the available tools to access database information and create appropriate visualizations. Provide clear explanations of your reasoning throughout the analysis."""

        _add_progress_update("Executing comprehensive analysis...", "executing")
        
        # Execute the analysis
        response = mes_agent(formatted_query)
        
        _add_progress_update("Analysis complete!", "completed")
        
        # Format the response for return
        if hasattr(response, 'content'):
            content = response.content
        elif isinstance(response, dict):
            content = response.get('content', str(response))
        else:
            content = str(response)
        
        _logger.info("MES analysis completed successfully")
        return content
        
    except Exception as e:
        _logger.error(f"MES analysis failed: {e}")
        return _handle_analysis_error(query, str(e))


def _add_progress_update(message: str, status: str):
    """Add a progress update for tracking."""
    global _progress_updates
    
    if _config.enable_progress_updates:
        _progress_updates.append({
            'step': len(_progress_updates) + 1,
            'message': message,
            'status': status,
            'timestamp': datetime.now().isoformat()
        })


def _handle_analysis_error(query: str, error_message: str) -> str:
    """Handle analysis errors with intelligent recovery."""
    global _error_analyzer, _logger
    
    _logger.warning(f"Analysis failed, providing error guidance: {error_message}")
    
    # Create error context
    error_context = ErrorContext(
        original_query=query,
        error_message=error_message,
        error_type='analysis_error',
        timestamp=datetime.now(),
        execution_time=0.0
    )
    
    # Analyze the error
    analysis = _error_analyzer.analyze_error(error_context)
    
    # Format helpful error response
    error_response = f"""I encountered an issue while analyzing your manufacturing query: "{query}"

**What happened**: {analysis.user_friendly_message}

**Root cause**: {analysis.root_cause}

**Suggestions to try**:
"""
    
    for i, action in enumerate(analysis.recovery_actions[:3], 1):
        error_response += f"\n{i}. {action.description}"
    
    if analysis.alternative_approaches:
        error_response += "\n\n**Alternative approaches**:"
        for approach in analysis.alternative_approaches[:3]:
            error_response += f"\n• {approach}"
    
    if analysis.educational_content:
        error_response += "\n\n**Tips for better queries**:"
        for tip in analysis.educational_content[:2]:
            error_response += f"\n• {tip}"
    
    return error_response


def get_progress_updates() -> List[Dict[str, Any]]:
    """Get current progress updates for UI display."""
    return _progress_updates.copy()


def update_config(config: AgentConfig):
    """Update the global configuration."""
    global _config
    _config = config


# Legacy class for backward compatibility
class MESAnalysisAgent:
    """
    Legacy MES Analysis Agent class for backward compatibility.
    
    This class provides the same interface as before but uses the new agent-as-tools pattern internally.
    """
    
    def __init__(self, config: AgentConfig):
        """Initialize with configuration."""
        global _config
        _config = config
        self.config = config
        self.logger = logging.getLogger(__name__)
        
    async def analyze(self, query: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Main analysis method using the agent-as-tools pattern.
        
        Args:
            query: User query string
            context: Optional context from previous interactions
            
        Returns:
            Dictionary containing comprehensive analysis results
        """
        start_time = datetime.now()
        
        try:
            # Use the agent-as-tool for analysis
            analysis_result = mes_analysis_tool(query)
            
            # Calculate execution time
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            
            return {
                'success': True,
                'agent_type': 'MES Analysis Agent',
                'query': query,
                'analysis': analysis_result,
                'progress_updates': get_progress_updates(),
                'timestamp': datetime.now().isoformat(),
                'execution_time': execution_time,
                'capabilities_used': ['mes_analysis_tool', 'run_sqlite_query', 'get_database_schema', 'create_intelligent_visualization'],
                'follow_up_suggestions': self._generate_follow_up_suggestions(analysis_result, query)
            }
            
        except Exception as e:
            self.logger.error(f"Analysis failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'query': query,
                'user_friendly_message': 'I encountered an issue while processing your request.',
                'suggestions': [
                    'Try a simpler, more specific question',
                    'Check if your query references valid data',
                    'Use the database schema tool to explore available data'
                ],
                'timestamp': datetime.now().isoformat()
            }
    
    def get_agent_info(self) -> Dict[str, Any]:
        """Get agent information and capabilities."""
        return {
            'name': 'MES Analysis Agent',
            'version': '2.0.0',
            'pattern': 'agent-as-tools',
            'capabilities': [
                'Production Analysis',
                'Quality Analysis', 
                'Equipment Analysis',
                'Inventory Analysis',
                'Multi-Domain Analysis',
                'Intelligent Visualization',
                'Multi-Step Reasoning',
                'Error Recovery',
                'Query Refinement',
                'Educational Feedback'
            ],
            'tools': [
                'run_sqlite_query',
                'get_database_schema',
                'create_intelligent_visualization'
            ],
            'config': {
                'analysis_depth': self.config.analysis_depth,
                'timeout_seconds': self.config.timeout_seconds,
                'progress_updates_enabled': self.config.enable_progress_updates
            }
        }
    
    def get_progress_updates(self) -> List[Dict[str, Any]]:
        """Get current progress updates for UI display."""
        return get_progress_updates()
    
    def _generate_follow_up_suggestions(self, analysis_content: str, original_query: str) -> List[str]:
        """Generate intelligent follow-up suggestions based on the analysis."""
        suggestions = []
        
        query_lower = original_query.lower()
        content_lower = analysis_content.lower() if analysis_content else ""
        
        # Domain-specific intelligent suggestions
        if any(term in query_lower for term in ['production', 'work order', 'schedule', 'output']):
            suggestions.extend([
                "What quality issues occurred during peak production periods?",
                "Which machines had the most downtime affecting production?",
                "How do inventory levels correlate with production delays?"
            ])
        
        if any(term in query_lower for term in ['quality', 'defect', 'yield', 'inspection']):
            suggestions.extend([
                "Which suppliers contribute most to quality issues?",
                "How does equipment maintenance affect quality metrics?",
                "What production parameters correlate with defect rates?"
            ])
        
        if any(term in query_lower for term in ['equipment', 'machine', 'oee', 'downtime']):
            suggestions.extend([
                "What is the financial impact of equipment downtime?",
                "How does preventive maintenance affect OEE scores?",
                "Which work centers have the most equipment issues?"
            ])
        
        if any(term in query_lower for term in ['inventory', 'stock', 'material', 'supplier']):
            suggestions.extend([
                "Which items are most frequently out of stock?",
                "How do supplier lead times affect production schedules?",
                "What is the optimal reorder point for critical materials?"
            ])
        
        # Remove duplicates and limit to top suggestions
        unique_suggestions = list(dict.fromkeys(suggestions))
        return unique_suggestions[:4]