"""
Production Meeting Agent Tools

Implements specialized agent tools for production meeting analysis using the
agent-as-tools pattern, following the same structure as mes_analysis_agent.py.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
from strands import Agent, tool
from .tools.database_tools import run_sqlite_query, get_database_schema, get_production_context
from .tools.visualization_tools import create_intelligent_visualization
from .config import ProductionMeetingConfig
from .error_handling import IntelligentErrorAnalyzer, ErrorContext

logger = logging.getLogger(__name__)

# Global configuration for agent tools
_config = ProductionMeetingConfig()
_error_analyzer = IntelligentErrorAnalyzer()


def _get_production_analysis_system_prompt() -> str:
    """Get the system prompt for the Production Analysis Agent."""
    return """You are a Production Analysis Agent for e-bike manufacturing daily meetings.

FOCUS: Work order completion, production throughput, bottleneck identification, and shift performance.

KEY METRICS TO ANALYZE:
- Work order completion rates and on-time delivery
- Production output vs targets by shift (Morning, Afternoon, Night)
- Bottlenecks: which work centers or products are behind
- Scrap rates and production efficiency

RESPONSE STYLE: Concise, data-driven insights with specific numbers. Highlight critical issues first. Include actionable recommendations for the production team."""


@tool
def production_analysis_tool(query: str) -> str:
    """
    Process production-related queries for daily meetings.
    
    Specialized agent tool focused on production performance analysis, bottleneck
    identification, and work order management for manufacturing daily meetings.
    
    Args:
        query: Production analysis question or request
        
    Returns:
        Production analysis results with insights and recommendations
    """
    try:
        logger.info(f"Production analysis tool processing query: {query[:100]}...")
        
        # Create the specialized production analysis agent
        production_agent = Agent(
            system_prompt=_get_production_analysis_system_prompt(),
            tools=[run_sqlite_query, get_database_schema, get_production_context, create_intelligent_visualization],
            model=_config.default_model
        )
        
        # Format the query for production analysis focus
        formatted_query = f"""Production meeting query: {query}

Use get_production_context() for timeframes, then run_sqlite_query() to get relevant data from WorkOrders, Machines, and related tables. Provide concise, actionable insights."""

        # Execute the production analysis
        response = production_agent(formatted_query)
        
        # Format the response for return
        if hasattr(response, 'content'):
            content = response.content
        elif isinstance(response, dict):
            content = response.get('content', str(response))
        else:
            content = str(response)
        
        logger.info("Production analysis completed successfully")
        return content
        
    except Exception as e:
        logger.error(f"Production analysis failed: {e}")
        return _handle_production_analysis_error(query, str(e))


def _get_quality_analysis_system_prompt() -> str:
    """Get the system prompt for the Quality Analysis Agent."""
    return """You are a Quality Analysis Agent for e-bike manufacturing daily meetings.

FOCUS: Defect rates, yield analysis, quality control results, and root cause identification.

KEY METRICS TO ANALYZE:
- Defect rates by product and work center
- Yield rates and first-pass quality
- Quality control pass/fail results
- Defect type patterns and trends

RESPONSE STYLE: Concise, data-driven insights with specific numbers. Flag critical quality issues requiring immediate action. Recommend corrective actions with clear ownership."""


@tool
def quality_analysis_tool(query: str) -> str:
    """
    Process quality-related queries for daily meetings.
    
    Specialized agent tool focused on quality metrics analysis, defect pattern
    recognition, and root cause identification for manufacturing daily meetings.
    
    Args:
        query: Quality analysis question or request
        
    Returns:
        Quality analysis results with defect patterns and recommendations
    """
    try:
        logger.info(f"Quality analysis tool processing query: {query[:100]}...")
        
        # Create the specialized quality analysis agent
        quality_agent = Agent(
            system_prompt=_get_quality_analysis_system_prompt(),
            tools=[run_sqlite_query, get_database_schema, get_production_context, create_intelligent_visualization],
            model=_config.default_model
        )
        
        # Format the query for quality analysis focus
        formatted_query = f"""Quality meeting query: {query}

Use get_production_context() for timeframes, then run_sqlite_query() to get relevant data from QualityControl and related tables. Provide concise, actionable insights."""

        # Execute the quality analysis
        response = quality_agent(formatted_query)
        
        # Format the response for return
        if hasattr(response, 'content'):
            content = response.content
        elif isinstance(response, dict):
            content = response.get('content', str(response))
        else:
            content = str(response)
        
        logger.info("Quality analysis completed successfully")
        return content
        
    except Exception as e:
        logger.error(f"Quality analysis failed: {e}")
        return _handle_quality_analysis_error(query, str(e))


def _get_equipment_analysis_system_prompt() -> str:
    """Get the system prompt for the Equipment Analysis Agent."""
    return """You are an Equipment Analysis Agent for e-bike manufacturing daily meetings.

FOCUS: OEE metrics (Availability, Performance, Quality), machine status, downtime analysis, and maintenance needs.

KEY METRICS TO ANALYZE:
- OEE scores by machine and work center
- Machine status: running, idle, maintenance, breakdown
- Downtime incidents and root causes
- Upcoming maintenance requirements

RESPONSE STYLE: Concise, data-driven insights with specific numbers. Prioritize machines with issues. Recommend maintenance actions with urgency levels."""


@tool
def equipment_analysis_tool(query: str) -> str:
    """
    Process equipment-related queries for daily meetings.
    
    Specialized agent tool focused on OEE metrics analysis, maintenance optimization,
    and downtime analysis for manufacturing daily meetings.
    
    Args:
        query: Equipment analysis question or request
        
    Returns:
        Equipment analysis results with OEE insights and maintenance recommendations
    """
    try:
        logger.info(f"Equipment analysis tool processing query: {query[:100]}...")
        
        # Create the specialized equipment analysis agent
        equipment_agent = Agent(
            system_prompt=_get_equipment_analysis_system_prompt(),
            tools=[run_sqlite_query, get_database_schema, get_production_context, create_intelligent_visualization],
            model=_config.default_model
        )
        
        # Format the query for equipment analysis focus
        formatted_query = f"""Equipment meeting query: {query}

Use get_production_context() for timeframes, then run_sqlite_query() to get relevant data from Machines, OEE, Downtimes tables. Provide concise, actionable insights."""

        # Execute the equipment analysis
        response = equipment_agent(formatted_query)
        
        # Format the response for return
        if hasattr(response, 'content'):
            content = response.content
        elif isinstance(response, dict):
            content = response.get('content', str(response))
        else:
            content = str(response)
        
        logger.info("Equipment analysis completed successfully")
        return content
        
    except Exception as e:
        logger.error(f"Equipment analysis failed: {e}")
        return _handle_equipment_analysis_error(query, str(e))


def _get_inventory_analysis_system_prompt() -> str:
    """Get the system prompt for the Inventory Analysis Agent."""
    return """You are an Inventory Analysis Agent for e-bike manufacturing daily meetings.

FOCUS: Stock levels, material shortages, reorder alerts, and consumption patterns.

KEY METRICS TO ANALYZE:
- Items below reorder level (critical shortages)
- Stock-outs impacting production
- Material consumption rates vs forecast
- Supplier delivery performance

RESPONSE STYLE: Concise, data-driven insights with specific numbers. Flag items needing immediate reorder. Identify materials at risk of causing production delays."""


@tool
def inventory_analysis_tool(query: str) -> str:
    """
    Process inventory-related queries for daily meetings.
    
    Specialized agent tool focused on inventory levels analysis, consumption patterns,
    and shortage predictions for manufacturing daily meetings.
    
    Args:
        query: Inventory analysis question or request
        
    Returns:
        Inventory analysis results with shortage predictions and recommendations
    """
    try:
        logger.info(f"Inventory analysis tool processing query: {query[:100]}...")
        
        # Create the specialized inventory analysis agent
        inventory_agent = Agent(
            system_prompt=_get_inventory_analysis_system_prompt(),
            tools=[run_sqlite_query, get_database_schema, get_production_context, create_intelligent_visualization],
            model=_config.default_model
        )
        
        # Format the query for inventory analysis focus
        formatted_query = f"""Inventory meeting query: {query}

Use get_production_context() for timeframes, then run_sqlite_query() to get relevant data from Inventory, Suppliers, MaterialConsumption tables. Provide concise, actionable insights."""

        # Execute the inventory analysis
        response = inventory_agent(formatted_query)
        
        # Format the response for return
        if hasattr(response, 'content'):
            content = response.content
        elif isinstance(response, dict):
            content = response.get('content', str(response))
        else:
            content = str(response)
        
        logger.info("Inventory analysis completed successfully")
        return content
        
    except Exception as e:
        logger.error(f"Inventory analysis failed: {e}")
        return _handle_inventory_analysis_error(query, str(e))


def _handle_production_analysis_error(query: str, error_message: str) -> str:
    """Handle production analysis errors with intelligent recovery."""
    logger.warning(f"Production analysis failed, providing error guidance: {error_message}")
    
    # Create error context
    error_context = ErrorContext(
        original_query=query,
        error_message=error_message,
        error_type='production_analysis_error',
        timestamp=datetime.now(),
        execution_time=0.0
    )
    
    # Analyze the error
    analysis = _error_analyzer.analyze_error(error_context)
    
    # Format helpful error response
    error_response = f"""I encountered an issue while analyzing your production query: "{query}"

**What happened**: {analysis.user_friendly_message}

**Production meeting impact**: Unable to complete production analysis - consider alternative approaches

**Suggestions for production analysis**:
1. Try asking about specific work orders or production metrics
2. Check current production status with simpler queries
3. Use get_production_context() for basic production meeting data

**Alternative production questions to try**:
• "What is the current production status for today?"
• "Which work orders are behind schedule?"
• "Show me production efficiency by work center"
"""
    
    return error_response


def _handle_quality_analysis_error(query: str, error_message: str) -> str:
    """Handle quality analysis errors with intelligent recovery."""
    logger.warning(f"Quality analysis failed, providing error guidance: {error_message}")
    
    error_response = f"""I encountered an issue while analyzing your quality query: "{query}"

**Quality meeting impact**: Unable to complete quality analysis - consider alternative approaches

**Suggestions for quality analysis**:
1. Try asking about specific quality metrics or defect rates
2. Check current quality status with simpler queries
3. Focus on specific products or quality control checkpoints

**Alternative quality questions to try**:
• "What is the current defect rate for today?"
• "Which products have quality issues?"
• "Show me quality control results by work center"
"""
    
    return error_response


def _handle_equipment_analysis_error(query: str, error_message: str) -> str:
    """Handle equipment analysis errors with intelligent recovery."""
    logger.warning(f"Equipment analysis failed, providing error guidance: {error_message}")
    
    error_response = f"""I encountered an issue while analyzing your equipment query: "{query}"

**Equipment meeting impact**: Unable to complete equipment analysis - consider alternative approaches

**Suggestions for equipment analysis**:
1. Try asking about specific machines or equipment status
2. Check current equipment performance with simpler queries
3. Focus on specific OEE metrics or maintenance schedules

**Alternative equipment questions to try**:
• "What is the current equipment status?"
• "Which machines need maintenance?"
• "Show me OEE performance by machine"
"""
    
    return error_response


def _handle_inventory_analysis_error(query: str, error_message: str) -> str:
    """Handle inventory analysis errors with intelligent recovery."""
    logger.warning(f"Inventory analysis failed, providing error guidance: {error_message}")
    
    error_response = f"""I encountered an issue while analyzing your inventory query: "{query}"

**Inventory meeting impact**: Unable to complete inventory analysis - consider alternative approaches

**Suggestions for inventory analysis**:
1. Try asking about specific materials or stock levels
2. Check current inventory status with simpler queries
3. Focus on specific suppliers or reorder alerts

**Alternative inventory questions to try**:
• "What materials are low in stock?"
• "Which items need reordering?"
• "Show me inventory levels by category"
"""
    
    return error_response


def _get_main_orchestrator_system_prompt() -> str:
    """Get the system prompt for the main Production Meeting Analysis orchestrator."""
    return """You are a Production Meeting Orchestrator for e-bike manufacturing. You coordinate specialized agents to provide comprehensive analysis for daily meetings.

TOOL ROUTING:
- Production questions (work orders, completion rates, bottlenecks) → production_analysis_tool
- Quality questions (defects, yield, quality control) → quality_analysis_tool
- Equipment questions (OEE, machines, downtime, maintenance) → equipment_analysis_tool
- Inventory questions (stock levels, shortages, materials) → inventory_analysis_tool
- Daily briefing / comprehensive status → Call ALL four tools, then synthesize

RESPONSE FORMAT:
For briefings, structure as:
1. **Critical Issues** (needs immediate action)
2. **Key Metrics** (numbers and trends)
3. **Recommendations** (specific actions)

Keep responses concise and meeting-ready. Lead with the most important findings."""


@tool
def production_meeting_analysis_tool(query: str) -> str:
    """
    Main production meeting analysis tool that orchestrates specialized agents.
    
    This orchestrator agent coordinates specialized manufacturing agents to provide
    comprehensive analysis for production meetings. It handles query routing,
    multi-domain analysis coordination, and daily briefing generation.
    
    Args:
        query: Production meeting analysis question or request
        
    Returns:
        Comprehensive analysis results for production meetings
    """
    try:
        logger.info(f"Production meeting orchestrator processing query: {query[:100]}...")
        
        # Create the main orchestrator agent with access to all specialized tools
        orchestrator_agent = Agent(
            system_prompt=_get_main_orchestrator_system_prompt(),
            tools=[
                production_analysis_tool,
                quality_analysis_tool, 
                equipment_analysis_tool,
                inventory_analysis_tool,
                run_sqlite_query,
                get_database_schema,
                get_production_context,
                create_intelligent_visualization
            ],
            model=_config.default_model
        )
        
        # Classify the query type for appropriate handling
        query_classification = _classify_meeting_query(query)
        
        # Format the query based on classification
        if query_classification['type'] == 'daily_briefing':
            formatted_query = _format_daily_briefing_query(query, query_classification)
        elif query_classification['type'] == 'multi_domain':
            formatted_query = _format_multi_domain_query(query, query_classification)
        else:
            formatted_query = _format_single_domain_query(query, query_classification)
        
        # Execute the orchestrated analysis
        logger.info(f"Executing {query_classification['type']} analysis with orchestrator agent")
        response = orchestrator_agent(formatted_query)
        
        # Format the response for return
        if hasattr(response, 'content'):
            content = response.content
        elif isinstance(response, dict):
            content = response.get('content', str(response))
        else:
            content = str(response)
        
        # Add orchestrator metadata
        orchestrated_response = _enhance_orchestrator_response(content, query, query_classification)
        
        logger.info("Production meeting orchestration completed successfully")
        return orchestrated_response
        
    except Exception as e:
        logger.error(f"Production meeting orchestration failed: {e}")
        return _handle_orchestrator_error(query, str(e))


def _classify_meeting_query(query: str) -> Dict[str, Any]:
    """
    Classify the type of meeting query to determine orchestration approach.
    
    Args:
        query: The input query string
        
    Returns:
        Dictionary with classification information
    """
    query_lower = query.lower().strip()
    
    # Daily briefing patterns
    daily_briefing_keywords = [
        'daily briefing', 'meeting summary', 'production status', 'overall status',
        'daily summary', 'meeting overview', 'production overview', 'daily report',
        'status update', 'comprehensive summary', 'full briefing'
    ]
    
    if any(keyword in query_lower for keyword in daily_briefing_keywords):
        return {
            'type': 'daily_briefing',
            'domains': ['production', 'quality', 'equipment', 'inventory'],
            'priority': 'high',
            'requires_all_agents': True
        }
    
    # Multi-domain analysis patterns
    domain_keywords = {
        'production': ['production', 'work order', 'manufacturing', 'output', 'throughput', 'completion'],
        'quality': ['quality', 'defect', 'yield', 'rework', 'inspection', 'control'],
        'equipment': ['equipment', 'machine', 'oee', 'downtime', 'maintenance', 'efficiency'],
        'inventory': ['inventory', 'stock', 'material', 'supply', 'shortage', 'reorder']
    }
    
    detected_domains = []
    for domain, keywords in domain_keywords.items():
        if any(keyword in query_lower for keyword in keywords):
            detected_domains.append(domain)
    
    if len(detected_domains) > 1:
        return {
            'type': 'multi_domain',
            'domains': detected_domains,
            'priority': 'medium',
            'requires_coordination': True
        }
    elif len(detected_domains) == 1:
        return {
            'type': 'single_domain',
            'domains': detected_domains,
            'primary_domain': detected_domains[0],
            'priority': 'medium',
            'requires_coordination': False
        }
    else:
        # General query - treat as multi-domain for comprehensive analysis
        return {
            'type': 'general',
            'domains': ['production', 'quality', 'equipment', 'inventory'],
            'priority': 'low',
            'requires_coordination': True
        }


def _format_daily_briefing_query(query: str, classification: Dict[str, Any]) -> str:
    """Format query for comprehensive daily briefing analysis."""
    return f"""Daily briefing request: {query}

Call all four specialized tools (production, quality, equipment, inventory) to gather comprehensive data, then synthesize into a meeting-ready briefing."""


def _format_multi_domain_query(query: str, classification: Dict[str, Any]) -> str:
    """Format query for multi-domain analysis coordination."""
    domains = classification['domains']
    return f"""Query: {query}

This involves {', '.join(domains)}. Call the relevant specialized tools and provide integrated insights."""


def _format_single_domain_query(query: str, classification: Dict[str, Any]) -> str:
    """Format query for focused single-domain analysis."""
    primary_domain = classification.get('primary_domain', 'general')
    return f"""Query: {query}

This is primarily a {primary_domain} question. Use the appropriate specialized tool and provide focused, actionable insights."""


def _enhance_orchestrator_response(content: str, original_query: str, classification: Dict[str, Any]) -> str:
    """Enhance the orchestrator response with minimal metadata."""
    # Keep it simple - just return the content with a timestamp
    # The LLM's response should stand on its own merit
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
    return f"{content}\n\n---\n*Analysis generated: {timestamp}*"


def _handle_orchestrator_error(query: str, error_message: str) -> str:
    """Handle orchestrator errors with intelligent recovery and meeting context."""
    logger.warning(f"Orchestrator analysis failed, providing error guidance: {error_message}")
    
    # Create error context
    error_context = ErrorContext(
        original_query=query,
        error_message=error_message,
        error_type='orchestrator_error',
        timestamp=datetime.now(),
        execution_time=0.0
    )
    
    # Analyze the error
    analysis = _error_analyzer.analyze_error(error_context)
    
    # Format comprehensive error response
    error_response = f"""# Production Meeting Analysis - Error Recovery

**Query**: "{query}"
**Issue**: {analysis.user_friendly_message}

## Meeting Impact
The comprehensive analysis could not be completed, but the meeting can proceed with alternative approaches.

## Recovery Options

### Immediate Actions
1. **Use Individual Agents**: Try specific domain analysis tools directly
   - `production_analysis_tool("your production question")`
   - `quality_analysis_tool("your quality question")`
   - `equipment_analysis_tool("your equipment question")`
   - `inventory_analysis_tool("your inventory question")`

2. **Get Basic Context**: Use `get_production_context()` for meeting-ready data

3. **Manual Analysis**: Use `run_sqlite_query()` for direct data access

### Alternative Meeting Questions
Try these simpler, focused questions:

**Production Focus**:
- "What is the current production status?"
- "Which work orders need attention?"
- "Show production efficiency trends"

**Quality Focus**:
- "What are today's quality issues?"
- "Show defect rates by product"
- "Which quality checks failed?"

**Equipment Focus**:
- "What equipment needs maintenance?"
- "Show machine efficiency status"
- "Which machines are down?"

**Inventory Focus**:
- "What materials are low in stock?"
- "Show inventory shortage alerts"
- "Which items need reordering?"

## Technical Details
- **Error Type**: Orchestrator coordination failure
- **Timestamp**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **Recovery Strategy**: Use individual specialized agents

The production meeting can continue with focused analysis using individual agent tools while this issue is resolved.
"""
    
    return error_response


# TODO: Implement actual agent class when implementing Strands SDK integration
class ProductionMeetingAgent:
    """
    Placeholder for the main production meeting agent class.
    
    This will be implemented in later tasks using Strands SDK Agent class.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the production meeting agent."""
        self.config = config or {}
        logger.info("ProductionMeetingAgent placeholder initialized")
    
    async def process_query(self, query: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Process a query using the agent tools.
        
        This will be implemented in later tasks with actual Strands SDK integration.
        """
        # Placeholder implementation
        result = production_meeting_analysis_tool(query)
        
        return {
            'success': True,
            'result': result,
            'timestamp': datetime.now().isoformat(),
            'context': context or {}
        }