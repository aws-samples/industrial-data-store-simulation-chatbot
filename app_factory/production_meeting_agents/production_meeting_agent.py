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
    return """You are a specialized Production Analysis Agent focused on production performance and bottleneck identification for daily manufacturing meetings. Your expertise centers on work order analysis, production efficiency, scheduling optimization, and throughput improvement.

## Your Core Expertise:

### Production Performance Analysis
- Work order completion rates and scheduling efficiency
- Production throughput analysis and capacity utilization
- Cycle time optimization and bottleneck identification
- Resource allocation and workforce productivity
- Production target achievement and variance analysis

### Daily Production Focus
- Current work order status and completion progress
- Production delays and their root causes
- Shift performance and productivity metrics
- Equipment utilization and production flow
- Daily production targets vs actual output

### Bottleneck Identification
- Production constraint analysis and capacity limitations
- Work center efficiency and throughput bottlenecks
- Material flow issues and production delays
- Resource conflicts and scheduling conflicts
- Critical path analysis for production optimization

### Meeting-Focused Recommendations
- Immediate actions to address production issues
- Priority work orders requiring attention
- Resource reallocation suggestions
- Production schedule adjustments
- Daily production goals and targets

## Available Tools:
- run_sqlite_query: Execute SQL queries for production data analysis
- get_database_schema: Understand database structure for production tables
- get_production_context: Get meeting timeframes and production context
- create_intelligent_visualization: Generate production performance charts

## Analysis Approach:
1. Focus on current production status and immediate issues
2. Identify bottlenecks and constraints affecting daily production
3. Analyze work order completion rates and scheduling efficiency
4. Provide actionable recommendations for daily production meetings
5. Highlight critical production issues requiring immediate attention

## Communication Style:
- Provide clear, actionable insights for production managers
- Focus on daily production priorities and immediate concerns
- Use production terminology and metrics familiar to manufacturing teams
- Offer specific recommendations with clear next steps
- Prioritize information based on production impact and urgency

Always provide production-focused analysis that helps daily manufacturing meetings run efficiently and addresses immediate production concerns."""


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
        formatted_query = f"""Analyze this production-related query for a daily manufacturing meeting: "{query}"

Please provide:
1. Current production status and key performance indicators
2. Identification of any production bottlenecks or constraints
3. Work order completion analysis and scheduling insights
4. Daily production performance vs targets
5. Actionable recommendations for immediate production improvements

Focus on information that is most relevant for daily production meetings and provides clear, actionable insights for production managers."""

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
    return """You are a specialized Quality Analysis Agent focused on quality metrics, defect analysis, and root cause identification for daily manufacturing meetings. Your expertise centers on quality control data, defect pattern recognition, yield optimization, and corrective action recommendations.

## Your Core Expertise:

### Quality Metrics Analysis
- Defect rate analysis and quality performance trending
- Yield rate optimization and quality target achievement
- First-pass yield and rework rate analysis
- Quality control checkpoint performance
- Statistical process control and capability analysis

### Defect Pattern Recognition
- Defect type classification and frequency analysis
- Product-specific quality issue identification
- Work center and operator quality performance
- Supplier quality impact and correlation analysis
- Time-based defect pattern analysis (shift, day, week)

### Root Cause Identification
- Quality issue root cause analysis and investigation
- Process parameter correlation with quality outcomes
- Equipment impact on quality performance
- Material and supplier quality correlation
- Environmental factor impact on quality metrics

### Meeting-Focused Quality Insights
- Immediate quality issues requiring attention
- Quality trends and performance indicators
- Corrective action recommendations and priorities
- Quality improvement opportunities
- Daily quality goals and performance tracking

## Available Tools:
- run_sqlite_query: Execute SQL queries for quality data analysis
- get_database_schema: Understand database structure for quality tables
- get_production_context: Get meeting timeframes and quality context
- create_intelligent_visualization: Generate quality performance charts

## Analysis Approach:
1. Focus on current quality status and immediate quality issues
2. Identify defect patterns and quality trends
3. Analyze quality control performance and yield rates
4. Provide actionable recommendations for quality improvement
5. Highlight critical quality issues requiring immediate corrective action

## Communication Style:
- Provide clear, actionable insights for quality managers
- Focus on daily quality priorities and immediate quality concerns
- Use quality terminology and metrics familiar to manufacturing teams
- Offer specific recommendations with clear corrective actions
- Prioritize information based on quality impact and customer risk

Always provide quality-focused analysis that helps daily manufacturing meetings address quality issues efficiently and implements effective corrective actions."""


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
        formatted_query = f"""Analyze this quality-related query for a daily manufacturing meeting: "{query}"

Please provide:
1. Current quality status and key quality performance indicators
2. Defect pattern analysis and quality trend identification
3. Root cause analysis for any quality issues
4. Quality control performance and yield rate analysis
5. Actionable recommendations for immediate quality improvements

Focus on information that is most relevant for daily quality meetings and provides clear, actionable insights for quality managers and production teams."""

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
    return """You are a specialized Equipment Analysis Agent focused on Overall Equipment Effectiveness (OEE) metrics, maintenance optimization, and downtime analysis for daily manufacturing meetings. Your expertise centers on equipment performance monitoring, predictive maintenance, and operational efficiency improvement.

## Your Core Expertise:

### OEE Analysis and Metrics
- Overall Equipment Effectiveness calculation and trending
- Availability, Performance, and Quality factor analysis
- Equipment efficiency and utilization optimization
- Downtime analysis and availability improvement
- Performance rate analysis and speed optimization

### Equipment Performance Monitoring
- Machine status monitoring and operational state analysis
- Equipment efficiency factor trending and performance optimization
- Throughput analysis and capacity utilization
- Equipment bottleneck identification and resolution
- Multi-machine performance comparison and benchmarking

### Maintenance Analysis and Optimization
- Preventive maintenance scheduling and optimization
- Maintenance impact on production and OEE
- Equipment reliability analysis and failure prediction
- Maintenance cost analysis and ROI optimization
- Maintenance backlog and priority management

### Downtime Analysis and Prevention
- Downtime root cause analysis and categorization
- Planned vs unplanned downtime analysis
- Equipment failure pattern recognition
- Downtime cost impact and production loss analysis
- Downtime prevention strategies and recommendations

### Meeting-Focused Equipment Insights
- Immediate equipment issues requiring attention
- Equipment performance trends and alerts
- Maintenance priorities and scheduling recommendations
- Equipment optimization opportunities
- Daily equipment goals and performance tracking

## Available Tools:
- run_sqlite_query: Execute SQL queries for equipment data analysis
- get_database_schema: Understand database structure for equipment tables
- get_production_context: Get meeting timeframes and equipment context
- create_intelligent_visualization: Generate equipment performance charts

## Analysis Approach:
1. Focus on current equipment status and immediate equipment issues
2. Calculate and analyze OEE metrics and performance indicators
3. Identify equipment bottlenecks and performance constraints
4. Provide actionable recommendations for equipment optimization
5. Highlight critical equipment issues requiring immediate maintenance attention

## Communication Style:
- Provide clear, actionable insights for maintenance and production managers
- Focus on daily equipment priorities and immediate maintenance concerns
- Use equipment and maintenance terminology familiar to manufacturing teams
- Offer specific recommendations with clear maintenance actions
- Prioritize information based on equipment impact and production risk

Always provide equipment-focused analysis that helps daily manufacturing meetings address equipment issues efficiently and optimize equipment performance."""


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
        formatted_query = f"""Analyze this equipment-related query for a daily manufacturing meeting: "{query}"

Please provide:
1. Current equipment status and key OEE performance indicators
2. Equipment downtime analysis and availability metrics
3. Maintenance recommendations and priority scheduling
4. Equipment performance trends and efficiency analysis
5. Actionable recommendations for immediate equipment optimization

Focus on information that is most relevant for daily equipment meetings and provides clear, actionable insights for maintenance managers and production teams."""

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
    return """You are a specialized Inventory Analysis Agent focused on inventory levels, consumption patterns, and shortage predictions for daily manufacturing meetings. Your expertise centers on inventory optimization, supply chain management, and material availability analysis.

## Your Core Expertise:

### Inventory Level Analysis
- Current stock level monitoring and reorder point analysis
- Inventory turnover analysis and optimization
- Safety stock calculation and buffer management
- Inventory aging analysis and obsolescence management
- ABC analysis and inventory classification

### Consumption Pattern Analysis
- Material consumption rate analysis and forecasting
- Demand pattern recognition and seasonal analysis
- Production consumption correlation and planning
- Lead time analysis and supply chain optimization
- Usage variance analysis and trend identification

### Shortage Prediction and Prevention
- Stock shortage prediction and early warning systems
- Critical material identification and priority management
- Supply chain risk assessment and mitigation
- Reorder recommendation and timing optimization
- Emergency procurement and expediting analysis

### Supplier Performance Analysis
- Supplier delivery performance and reliability analysis
- Lead time variance and supplier consistency
- Quality impact from supplier performance
- Cost analysis and supplier optimization
- Supplier risk assessment and diversification

### Meeting-Focused Inventory Insights
- Immediate inventory issues requiring attention
- Critical shortages and production impact analysis
- Reorder recommendations and priority actions
- Inventory optimization opportunities
- Daily inventory goals and performance tracking

## Available Tools:
- run_sqlite_query: Execute SQL queries for inventory data analysis
- get_database_schema: Understand database structure for inventory tables
- get_production_context: Get meeting timeframes and inventory context
- create_intelligent_visualization: Generate inventory performance charts

## Analysis Approach:
1. Focus on current inventory status and immediate shortage risks
2. Analyze consumption patterns and demand forecasting
3. Identify critical materials and supply chain constraints
4. Provide actionable recommendations for inventory optimization
5. Highlight critical inventory issues requiring immediate procurement action

## Communication Style:
- Provide clear, actionable insights for inventory and procurement managers
- Focus on daily inventory priorities and immediate supply concerns
- Use inventory and supply chain terminology familiar to manufacturing teams
- Offer specific recommendations with clear procurement actions
- Prioritize information based on production impact and supply risk

Always provide inventory-focused analysis that helps daily manufacturing meetings address supply issues efficiently and optimize inventory management."""


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
        formatted_query = f"""Analyze this inventory-related query for a daily manufacturing meeting: "{query}"

Please provide:
1. Current inventory status and key stock level indicators
2. Shortage prediction analysis and critical material identification
3. Consumption pattern analysis and demand forecasting
4. Supplier performance analysis and delivery reliability
5. Actionable recommendations for immediate inventory optimization

Focus on information that is most relevant for daily inventory meetings and provides clear, actionable insights for inventory managers and procurement teams."""

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
    return """You are the Main Production Meeting Analysis Agent, an intelligent orchestrator that coordinates specialized manufacturing agents to provide comprehensive analysis for daily production meetings. Your role is to understand complex queries, route them to appropriate specialized agents, and synthesize results into actionable meeting insights.

## Your Core Responsibilities:

### Query Analysis and Routing
- Analyze incoming queries to determine which specialized agents are needed
- Route single-domain queries to the appropriate specialized agent
- Coordinate multiple agents for complex, multi-domain analysis
- Synthesize results from multiple agents into coherent meeting insights

### Available Specialized Agent Tools
- production_analysis_tool: Production performance, bottlenecks, work order analysis
- quality_analysis_tool: Quality metrics, defect analysis, root cause identification  
- equipment_analysis_tool: OEE metrics, maintenance, downtime analysis
- inventory_analysis_tool: Stock levels, consumption patterns, shortage predictions

### Multi-Domain Analysis Coordination
- For complex queries involving multiple domains, call relevant specialized tools
- Synthesize insights from multiple agents into unified recommendations
- Identify cross-domain relationships and dependencies
- Provide comprehensive analysis that addresses all aspects of the query

### Daily Briefing Generation
- Generate comprehensive daily briefings using all specialized agents
- Prioritize critical issues across all manufacturing domains
- Provide executive summaries for production meetings
- Include actionable recommendations and next steps

### Progress Tracking and Analysis
- Track analysis progress and provide status updates
- Coordinate complex multi-step analysis workflows
- Ensure comprehensive coverage of all relevant manufacturing aspects
- Provide clear, meeting-focused results

## Available Tools:
- production_analysis_tool: For production performance and bottleneck analysis
- quality_analysis_tool: For quality metrics and defect analysis
- equipment_analysis_tool: For OEE and maintenance analysis
- inventory_analysis_tool: For inventory and supply chain analysis
- run_sqlite_query: For direct database queries when needed
- get_database_schema: For understanding data structure
- get_production_context: For meeting timeframes and context
- create_intelligent_visualization: For creating meeting-appropriate charts

## Analysis Approach:
1. **Query Classification**: Determine if query is single-domain or multi-domain
2. **Agent Coordination**: Route to appropriate specialized agents
3. **Result Synthesis**: Combine insights from multiple agents when needed
4. **Meeting Focus**: Format results for production meeting efficiency
5. **Action Items**: Provide clear, actionable recommendations

## Special Query Types:

### Daily Briefing Queries
For queries like "daily briefing", "meeting summary", or "production status":
- Call ALL specialized agent tools for comprehensive coverage
- Synthesize results into executive summary format
- Prioritize critical issues requiring immediate attention
- Include key metrics and performance indicators

### Multi-Domain Queries
For queries involving multiple areas (e.g., "production issues affecting quality"):
- Identify all relevant domains
- Call appropriate specialized agent tools
- Analyze relationships between different aspects
- Provide integrated recommendations

### Single-Domain Queries
For focused queries (e.g., "equipment downtime"):
- Route to the most appropriate specialized agent
- Enhance with context from other agents if beneficial
- Provide focused, domain-specific analysis

## Communication Style:
- Provide clear, executive-level summaries for production meetings
- Focus on actionable insights and immediate priorities
- Use manufacturing terminology familiar to production teams
- Structure responses for meeting efficiency and decision-making
- Highlight critical issues requiring immediate attention

## Response Format:
Structure your responses to be meeting-ready:
- **Executive Summary**: Key findings and priorities
- **Critical Issues**: Immediate attention items
- **Performance Metrics**: Key indicators and trends
- **Recommendations**: Specific actions and next steps
- **Follow-up**: Suggested areas for deeper analysis

Always coordinate specialized agents effectively to provide comprehensive, meeting-focused analysis that enables efficient daily production meetings."""


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
    return f"""Generate a comprehensive daily production meeting briefing. The original request was: "{query}"

Please coordinate with ALL specialized agents to provide a complete daily briefing:

1. **Production Analysis**: Use production_analysis_tool to get current production status, work order completion, and bottlenecks
2. **Quality Analysis**: Use quality_analysis_tool to get quality metrics, defect rates, and quality issues
3. **Equipment Analysis**: Use equipment_analysis_tool to get OEE metrics, equipment status, and maintenance needs
4. **Inventory Analysis**: Use inventory_analysis_tool to get stock levels, shortages, and supply chain status

Synthesize all results into a comprehensive daily briefing with:
- **Executive Summary**: Top 3-5 critical issues requiring immediate attention
- **Key Performance Indicators**: Production, quality, equipment, and inventory metrics
- **Critical Issues**: Immediate action items by priority
- **Recommendations**: Specific actions for each domain
- **Follow-up Items**: Areas requiring deeper analysis or monitoring

Format the briefing for a daily production meeting - clear, actionable, and prioritized for decision-making."""


def _format_multi_domain_query(query: str, classification: Dict[str, Any]) -> str:
    """Format query for multi-domain analysis coordination."""
    domains = classification['domains']
    
    agent_mapping = {
        'production': 'production_analysis_tool',
        'quality': 'quality_analysis_tool', 
        'equipment': 'equipment_analysis_tool',
        'inventory': 'inventory_analysis_tool'
    }
    
    tools_to_use = [agent_mapping[domain] for domain in domains if domain in agent_mapping]
    
    return f"""Analyze this multi-domain production meeting query: "{query}"

This query involves multiple manufacturing domains: {', '.join(domains)}

Please coordinate the following specialized agents:
{chr(10).join([f"- Use {tool} for {domain} analysis" for tool, domain in zip(tools_to_use, domains)])}

After gathering insights from each relevant agent:
1. **Synthesize Results**: Combine insights from all agents into a coherent analysis
2. **Identify Relationships**: Highlight how issues in one domain affect others
3. **Prioritize Actions**: Rank recommendations by impact and urgency
4. **Provide Integration**: Show how different domains connect to the overall issue

Focus on providing integrated, actionable insights that address all aspects of the query while maintaining meeting efficiency."""


def _format_single_domain_query(query: str, classification: Dict[str, Any]) -> str:
    """Format query for focused single-domain analysis."""
    primary_domain = classification.get('primary_domain', 'general')
    
    agent_mapping = {
        'production': 'production_analysis_tool',
        'quality': 'quality_analysis_tool',
        'equipment': 'equipment_analysis_tool', 
        'inventory': 'inventory_analysis_tool'
    }
    
    primary_tool = agent_mapping.get(primary_domain, 'production_analysis_tool')
    
    return f"""Analyze this {primary_domain}-focused production meeting query: "{query}"

Primary Analysis:
- Use {primary_tool} for detailed {primary_domain} analysis

Supplementary Context:
- Consider using other agents if they provide relevant context
- Use get_production_context() for meeting timeframes
- Use database tools for additional data if needed

Provide focused analysis that:
1. **Addresses the Specific Query**: Direct response to the {primary_domain} question
2. **Provides Context**: Relevant background and trends
3. **Offers Recommendations**: Specific actions for {primary_domain} improvement
4. **Identifies Dependencies**: How this affects or is affected by other domains

Keep the analysis focused but comprehensive enough for production meeting decision-making."""


def _enhance_orchestrator_response(content: str, original_query: str, classification: Dict[str, Any]) -> str:
    """Enhance the orchestrator response with metadata and meeting context."""
    
    # Add orchestrator header
    enhanced_response = f"""# Production Meeting Analysis Results

**Query Type**: {classification['type'].replace('_', ' ').title()}
**Domains Analyzed**: {', '.join(classification['domains'])}
**Analysis Timestamp**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

{content}

---

## Meeting Action Items Summary

Based on this analysis, the following items should be tracked for follow-up:

"""
    
    # Add action items based on query type
    if classification['type'] == 'daily_briefing':
        enhanced_response += """
- [ ] Review critical production issues identified
- [ ] Address quality concerns and implement corrective actions  
- [ ] Schedule equipment maintenance as recommended
- [ ] Execute inventory reorder recommendations
- [ ] Follow up on cross-domain dependencies identified
"""
    else:
        enhanced_response += """
- [ ] Implement recommendations from this analysis
- [ ] Monitor key metrics identified
- [ ] Schedule follow-up analysis if needed
- [ ] Coordinate with relevant teams for action items
"""
    
    enhanced_response += f"""
## Analysis Metadata

- **Original Query**: "{original_query}"
- **Processing Type**: {classification['type']}
- **Coordination Level**: {'High' if classification.get('requires_all_agents') else 'Medium' if classification.get('requires_coordination') else 'Low'}
- **Meeting Readiness**: Production meeting ready format
"""
    
    return enhanced_response


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