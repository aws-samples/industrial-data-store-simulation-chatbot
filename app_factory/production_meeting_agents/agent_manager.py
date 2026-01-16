"""
Production Meeting Agent Manager

Provides integration layer between the dashboard system and the agent-as-tools
implementation, following the same patterns as MESAgentManager.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor

from .config import ProductionMeetingConfig, default_config
from .error_handling import ProductionMeetingErrorHandler, ProductionMeetingError
from .production_meeting_agent import production_meeting_analysis_tool

# Thread pool for parallel agent execution
_executor = ThreadPoolExecutor(max_workers=5)


logger = logging.getLogger(__name__)


class ProductionMeetingAgentManager:
    """
    Manages production meeting agents and provides integration with the dashboard system.
    
    This class follows the same pattern as MESAgentManager, providing a clean interface
    between the Streamlit dashboard and the agent-as-tools implementation.
    """
    
    def __init__(self, config: Optional[ProductionMeetingConfig] = None):
        """
        Initialize the production meeting agent manager.
        
        Args:
            config: Configuration for the agent manager
        """
        self.config = config or default_config
        self.error_handler = ProductionMeetingErrorHandler()
        self._is_initialized = False
        self._agent_status = {}
        self._session_context = {}
        self._meeting_context = {}
        self._proactive_insights_cache = {}
        
        logger.info("ProductionMeetingAgentManager initialized")
        
        # Initialize immediately if agent is enabled
        if self.config.agent_enabled:
            try:
                asyncio.create_task(self.initialize())
            except RuntimeError:
                # If no event loop is running, initialize synchronously
                pass
    
    async def initialize(self):
        """Initialize the agent manager and verify agent availability."""
        try:
            # Verify agent tools are available
            self._verify_agent_tools()
            
            self._is_initialized = True
            self._agent_status = {
                'production_agent': self.config.enable_production_agent,
                'quality_agent': self.config.enable_quality_agent,
                'equipment_agent': self.config.enable_equipment_agent,
                'inventory_agent': self.config.enable_inventory_agent,
                'main_orchestrator': True,
                'tools_available': True
            }
            logger.info("Production meeting agents initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize production meeting agents: {e}")
            raise ProductionMeetingError(f"Agent initialization failed: {e}")
    
    def _verify_agent_tools(self):
        """Verify that agent tools are available and functional."""
        try:
            # Test that the main orchestrator tool is available
            if not callable(production_meeting_analysis_tool):
                raise ProductionMeetingError("Main production meeting analysis tool not available")
            
            logger.info("Agent tools verification completed successfully")
        except Exception as e:
            logger.error(f"Agent tools verification failed: {e}")
            raise ProductionMeetingError(f"Agent tools not available: {e}")
    
    async def process_query(self, query: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Process a query using the production meeting agent tools.

        Args:
            query: The user query to process
            context: Optional context information

        Returns:
            Dictionary containing the analysis results
        """
        if not self._is_initialized:
            await self.initialize()

        if not self.config.agent_enabled:
            return {
                'success': False,
                'error': 'Production Meeting Agent not enabled',
                'message': 'Agent is disabled in configuration',
                'query': query,
                'suggested_actions': [
                    'Enable agent in configuration',
                    'Check agent settings',
                    'Verify Strands SDK installation'
                ]
            }

        try:
            start_time = datetime.now()

            # Update session context
            self._update_session_context(query, context)

            # Run the synchronous agent tool in thread pool for true async parallelism
            loop = asyncio.get_event_loop()
            analysis_result = await loop.run_in_executor(
                _executor,
                production_meeting_analysis_tool,
                query
            )

            execution_time = (datetime.now() - start_time).total_seconds()

            # Format response following MES agent manager pattern
            response = {
                'success': True,
                'agent_type': 'Production Meeting Agent',
                'query': query,
                'analysis': analysis_result,
                'execution_time': execution_time,
                'timestamp': datetime.now().isoformat(),
                'context': context or {},
                'agent_manager': {
                    'version': '1.0.0',
                    'integration_layer': 'Strands SDK',
                    'processing_time': execution_time
                },
                'progress_updates': self.get_progress_updates()
            }

            logger.info(f"Query processed successfully in {execution_time:.2f} seconds")
            return response

        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return self.error_handler.handle_error(e, {'query': query, 'context': context})
    
    def _update_session_context(self, query: str, context: Optional[Dict] = None):
        """Update session context with current query and context information."""
        self._session_context.update({
            'last_query': query,
            'last_query_time': datetime.now().isoformat(),
            'query_count': self._session_context.get('query_count', 0) + 1
        })
        
        if context:
            self._session_context.update(context)
        
        # Update meeting context based on query patterns
        self._update_meeting_context(query)
    
    def _update_meeting_context(self, query: str):
        """Update meeting context based on query patterns and content."""
        query_lower = query.lower()
        
        # Detect meeting type from query
        if any(word in query_lower for word in ['daily', 'today', 'briefing']):
            self._meeting_context['meeting_type'] = 'daily'
        elif any(word in query_lower for word in ['weekly', 'week']):
            self._meeting_context['meeting_type'] = 'weekly'
        elif any(word in query_lower for word in ['monthly', 'month']):
            self._meeting_context['meeting_type'] = 'monthly'
        
        # Detect focus areas from query
        focus_areas = []
        if any(word in query_lower for word in ['production', 'work order', 'throughput', 'bottleneck']):
            focus_areas.append('production')
        if any(word in query_lower for word in ['quality', 'defect', 'yield']):
            focus_areas.append('quality')
        if any(word in query_lower for word in ['equipment', 'oee', 'maintenance', 'downtime']):
            focus_areas.append('equipment')
        if any(word in query_lower for word in ['inventory', 'stock', 'shortage', 'material']):
            focus_areas.append('inventory')
        
        if focus_areas:
            self._meeting_context['focus_areas'] = list(set(
                self._meeting_context.get('focus_areas', []) + focus_areas
            ))
        
        # Update meeting timestamp
        self._meeting_context['last_updated'] = datetime.now().isoformat()
    
    def set_meeting_context(self, meeting_type: str, focus_areas: List[str], 
                           participants: Optional[List[str]] = None):
        """
        Set explicit meeting context for enhanced insights.
        
        Args:
            meeting_type: Type of meeting ('daily', 'weekly', 'monthly')
            focus_areas: List of focus areas for the meeting
            participants: Optional list of meeting participants
        """
        self._meeting_context = {
            'meeting_type': meeting_type,
            'focus_areas': focus_areas,
            'participants': participants or [],
            'set_time': datetime.now().isoformat(),
            'last_updated': datetime.now().isoformat()
        }
        
        logger.info(f"Meeting context set: {meeting_type} meeting with focus on {focus_areas}")
    
    def get_meeting_context(self) -> Dict[str, Any]:
        """Get current meeting context."""
        return self._meeting_context.copy()
    
    def get_agent_status(self) -> Dict[str, Any]:
        """
        Get the current status of all agents.
        
        Returns:
            Dictionary containing agent status information
        """
        base_status = {
            'agent_type': 'Production Meeting Agent',
            'capabilities': ['production', 'quality', 'equipment', 'inventory', 'multi-domain', 'daily-briefing'],
            'config': {
                'enabled': self.config.agent_enabled,
                'model': self.config.default_model,
                'timeout': self.config.timeout_seconds,
                'meeting_focus': self.config.meeting_focus,
                'analysis_depth': self.config.analysis_depth,
                'max_query_steps': self.config.max_query_steps,
                'progress_updates_enabled': self.config.enable_progress_updates
            },
            'tools_available': [
                'production_meeting_analysis_tool',
                'production_analysis_tool',
                'quality_analysis_tool', 
                'equipment_analysis_tool',
                'inventory_analysis_tool',
                'run_sqlite_query',
                'get_database_schema',
                'create_intelligent_visualization'
            ],
            'initialized': self._is_initialized,
            'agents': self._agent_status.copy(),
            'error_stats': self.error_handler.get_error_stats(),
            'session_context': self._session_context.copy(),
            'meeting_context': self._meeting_context.copy(),
            'timestamp': datetime.now().isoformat()
        }
        
        if self._is_initialized:
            base_status.update({
                'status': 'ready',
                'integration_status': 'Strands SDK integrated successfully'
            })
        else:
            base_status.update({
                'status': 'not_initialized',
                'integration_status': 'Strands SDK not integrated'
            })
        
        return base_status
    
    def is_ready(self) -> bool:
        """
        Check if the agent manager is ready to process queries.
        
        Returns:
            True if ready, False otherwise
        """
        return self._is_initialized and self.config.agent_enabled
    
    async def get_daily_briefing(self, date: Optional[str] = None) -> str:
        """
        Get a daily briefing for production meetings.
        
        Args:
            date: Optional date for the briefing (defaults to today)
            
        Returns:
            Daily briefing text
        """
        if not self._is_initialized:
            await self.initialize()
            
        try:
            briefing_date = date or datetime.now().strftime('%Y-%m-%d')
            
            # Create comprehensive daily briefing query
            briefing_query = f"""Generate a comprehensive daily production briefing for {briefing_date}. 

Please provide:
1. **Executive Summary**: Key production status and critical issues
2. **Production Performance**: Current production metrics and targets
3. **Quality Status**: Quality metrics and any quality issues
4. **Equipment Status**: Equipment performance and maintenance needs
5. **Inventory Alerts**: Critical inventory levels and supply issues
6. **Priority Actions**: Immediate actions required for today
7. **Key Metrics**: Important KPIs and performance indicators

Focus on information most relevant for a daily production meeting and provide actionable insights for production managers."""

            # Use the main orchestrator tool for comprehensive briefing
            briefing_result = production_meeting_analysis_tool(briefing_query)
            
            logger.info(f"Daily briefing generated successfully for {briefing_date}")
            return briefing_result
            
        except Exception as e:
            logger.error(f"Error generating daily briefing: {e}")
            error_response = self.error_handler.handle_error(e, {'operation': 'daily_briefing', 'date': date})
            return error_response.get('user_message', 'Unable to generate daily briefing')
    
    async def get_contextual_insights(self, dashboard_data: Dict, tab_name: str) -> str:
        """
        Get contextual insights for a specific dashboard tab.
        
        Args:
            dashboard_data: Current dashboard data
            tab_name: Name of the dashboard tab
            
        Returns:
            Contextual insights text
        """
        if not self._is_initialized:
            await self.initialize()
            
        try:
            # Create contextual query based on tab name and data
            contextual_query = self._create_contextual_query(tab_name, dashboard_data)
            
            # Use the main orchestrator tool for contextual analysis
            insights_result = production_meeting_analysis_tool(contextual_query)
            
            logger.info(f"Contextual insights generated successfully for {tab_name} tab")
            return insights_result
            
        except Exception as e:
            logger.error(f"Error generating contextual insights: {e}")
            error_response = self.error_handler.handle_error(e, {
                'operation': 'contextual_insights', 
                'tab_name': tab_name
            })
            return error_response.get('user_message', 'Unable to generate insights')
    
    def _create_contextual_query(self, tab_name: str, dashboard_data: Dict) -> str:
        """Create a contextual query based on dashboard tab and data."""
        tab_queries = {
            'production': """Analyze the current production dashboard data and provide contextual insights for production managers. 
                           Focus on production performance, bottlenecks, work order status, and immediate production priorities.""",
            
            'quality': """Analyze the current quality dashboard data and provide contextual insights for quality managers.
                        Focus on quality metrics, defect patterns, quality trends, and immediate quality improvement actions.""",
            
            'equipment': """Analyze the current equipment dashboard data and provide contextual insights for maintenance managers.
                          Focus on equipment performance, OEE metrics, maintenance needs, and immediate equipment priorities.""",
            
            'inventory': """Analyze the current inventory dashboard data and provide contextual insights for inventory managers.
                          Focus on inventory levels, shortage risks, consumption patterns, and immediate inventory actions.""",
            
            'productivity': """Analyze the current productivity dashboard data and provide contextual insights for production managers.
                             Focus on productivity metrics, efficiency trends, performance gaps, and improvement opportunities.""",
            
            'root_cause': """Analyze the current root cause dashboard data and provide contextual insights for problem-solving.
                           Focus on root cause analysis, problem patterns, corrective actions, and prevention strategies.""",
            
            'weekly': """Analyze the current weekly dashboard data and provide contextual insights for weekly reviews.
                       Focus on weekly trends, performance summaries, key achievements, and areas for improvement."""
        }
        
        base_query = tab_queries.get(tab_name.lower(), 
                                   f"Analyze the current {tab_name} dashboard data and provide relevant insights for production meetings.")
        
        # Add dashboard data context if available
        if dashboard_data:
            data_summary = f"\n\nCurrent dashboard context: {len(dashboard_data)} data elements available"
            if 'metrics' in dashboard_data:
                data_summary += f", including {len(dashboard_data['metrics'])} metrics"
            base_query += data_summary
        
        return base_query
    
    def get_progress_updates(self) -> List[Dict[str, Any]]:
        """
        Get current progress updates from the agent.
        
        Returns:
            List of progress update dictionaries
        """
        # Return basic progress information
        return [
            {
                'step': 'Agent Ready',
                'status': 'completed' if self._is_initialized else 'pending',
                'message': 'Production meeting agents are ready for analysis',
                'timestamp': datetime.now().isoformat()
            }
        ]
    
    def get_supported_queries(self) -> List[str]:
        """
        Get a list of supported query types.
        
        Returns:
            List of supported query examples
        """
        return [
            "What are today's production priorities?",
            "Show me quality issues from this week",
            "Which equipment needs attention?",
            "What inventory shortages should I be aware of?",
            "Give me a daily production briefing",
            "Analyze production bottlenecks",
            "Show equipment downtime trends",
            "What are the critical issues for today's meeting?",
            "How is our overall equipment effectiveness?",
            "Which work orders are behind schedule?",
            "What quality problems need immediate attention?"
        ]
    
    def generate_proactive_suggestions(self, conversation_history: List[Dict]) -> List[str]:
        """
        Generate proactive follow-up questions based on conversation history and production conditions.
        
        Args:
            conversation_history: List of previous conversation items
            
        Returns:
            List of proactive suggestion strings
        """
        if not conversation_history:
            return [
                "What are the current production bottlenecks?",
                "Which quality metrics need immediate attention?", 
                "How is our equipment performance trending?",
                "What inventory items are at risk of stockout?",
                "Give me a daily production briefing"
            ]
        
        # Analyze recent queries to suggest complementary analyses
        recent_queries = [item.get('query', '') for item in conversation_history[-3:]]
        all_queries_text = ' '.join(recent_queries).lower()
        
        suggestions = []
        
        # Domain-specific follow-up suggestions
        if 'production' in all_queries_text and 'quality' not in all_queries_text:
            suggestions.append("How do quality issues correlate with production problems?")
        
        if 'quality' in all_queries_text and 'equipment' not in all_queries_text:
            suggestions.append("Which equipment issues are causing quality problems?")
        
        if 'equipment' in all_queries_text and 'inventory' not in all_queries_text:
            suggestions.append("How do equipment failures affect inventory consumption?")
        
        if 'inventory' in all_queries_text and 'production' not in all_queries_text:
            suggestions.append("How do inventory shortages impact production schedules?")
        
        # Meeting-focused suggestions
        if not any(meeting_word in all_queries_text for meeting_word in ['briefing', 'summary', 'meeting']):
            suggestions.append("Generate a daily production meeting briefing")
        
        # Time-based suggestions
        if not any(time_word in all_queries_text for time_word in ['trend', 'over time', 'historical']):
            suggestions.append("What are the historical trends for these metrics?")
        
        # Comparative analysis suggestions
        if not any(comp_word in all_queries_text for comp_word in ['compare', 'versus', 'vs']):
            suggestions.append("How do these metrics compare across different work centers?")
        
        # Root cause analysis suggestions
        if not any(cause_word in all_queries_text for cause_word in ['cause', 'why', 'reason']):
            suggestions.append("What are the root causes of these issues?")
        
        # Default production meeting suggestions if no specific patterns detected
        if not suggestions:
            suggestions.extend([
                "What manufacturing KPIs should we monitor daily?",
                "Which areas have the highest improvement potential?",
                "How can we optimize our overall equipment effectiveness?",
                "What are today's critical production priorities?"
            ])
        
        return suggestions[:3]  # Return top 3 suggestions
    
    async def get_proactive_insights(self, production_conditions: Optional[Dict] = None) -> List[str]:
        """
        Generate proactive insights based on current production conditions.
        
        Args:
            production_conditions: Optional dictionary of current production conditions
            
        Returns:
            List of proactive insight strings
        """
        if not self._is_initialized:
            await self.initialize()
        
        try:
            # Check cache first
            cache_key = f"proactive_{datetime.now().strftime('%Y-%m-%d_%H')}"
            if cache_key in self._proactive_insights_cache:
                return self._proactive_insights_cache[cache_key]
            
            # Generate proactive insights query
            proactive_query = """Analyze current production conditions and generate proactive insights for today's production meeting.

Please identify:
1. **Critical Issues**: Any urgent production, quality, equipment, or inventory issues requiring immediate attention
2. **Trending Problems**: Issues that are developing and may become critical soon
3. **Opportunities**: Areas where improvements can be made today
4. **Preventive Actions**: Actions that can prevent potential problems
5. **Performance Alerts**: Metrics that are trending in concerning directions

Focus on actionable insights that production managers should be aware of proactively."""

            # Add production conditions context if provided
            if production_conditions:
                proactive_query += f"\n\nCurrent production conditions context: {production_conditions}"
            
            # Use the main orchestrator tool
            insights_result = production_meeting_analysis_tool(proactive_query)
            
            # Parse insights into list format
            insights_list = self._parse_insights_to_list(insights_result)
            
            # Cache the results for 1 hour
            self._proactive_insights_cache[cache_key] = insights_list
            
            logger.info("Proactive insights generated successfully")
            return insights_list
            
        except Exception as e:
            logger.error(f"Error generating proactive insights: {e}")
            return [
                "Unable to generate proactive insights at this time",
                "Consider checking production metrics manually",
                "Review critical equipment status and inventory levels"
            ]
    
    def _parse_insights_to_list(self, insights_text: str) -> List[str]:
        """Parse insights text into a list of actionable insights."""
        # Simple parsing - split by lines and filter meaningful content
        lines = insights_text.split('\n')
        insights = []
        
        for line in lines:
            line = line.strip()
            # Skip empty lines, headers, and formatting
            if (line and 
                not line.startswith('#') and 
                not line.startswith('**') and
                len(line) > 20 and
                any(keyword in line.lower() for keyword in 
                    ['issue', 'problem', 'alert', 'attention', 'critical', 'urgent', 
                     'recommend', 'suggest', 'should', 'need', 'require'])):
                insights.append(line)
        
        # Return top 5 insights
        return insights[:5] if insights else [
            "No specific proactive insights identified at this time",
            "All systems appear to be operating within normal parameters"
        ]
    
    async def get_meeting_summary_insights(self, meeting_data: Dict) -> Dict[str, Any]:
        """
        Generate comprehensive meeting summary insights.
        
        Args:
            meeting_data: Dictionary containing meeting data and context
            
        Returns:
            Dictionary containing structured meeting insights
        """
        if not self._is_initialized:
            await self.initialize()
        
        try:
            meeting_type = meeting_data.get('type', 'daily')
            focus_areas = meeting_data.get('focus_areas', ['production', 'quality', 'equipment', 'inventory'])
            
            # Generate comprehensive meeting summary
            summary_query = f"""Generate a comprehensive {meeting_type} meeting summary with insights across all manufacturing domains.

Please provide structured insights for:
1. **Executive Summary**: Key findings and priorities for the {meeting_type} meeting
2. **Critical Actions**: Immediate actions required today
3. **Performance Highlights**: Key achievements and positive trends
4. **Areas of Concern**: Issues requiring management attention
5. **Recommendations**: Specific recommendations for improvement
6. **Follow-up Items**: Items to track for next meeting

Focus areas for this meeting: {', '.join(focus_areas)}

Provide actionable, meeting-ready insights that enable efficient decision-making."""

            # Use the main orchestrator tool
            summary_result = production_meeting_analysis_tool(summary_query)
            
            return {
                'meeting_type': meeting_type,
                'focus_areas': focus_areas,
                'summary': summary_result,
                'generated_at': datetime.now().isoformat(),
                'meeting_context': self._meeting_context.copy()
            }
            
        except Exception as e:
            logger.error(f"Error generating meeting summary insights: {e}")
            return {
                'meeting_type': meeting_data.get('type', 'daily'),
                'focus_areas': meeting_data.get('focus_areas', []),
                'summary': 'Unable to generate meeting summary at this time',
                'error': str(e),
                'generated_at': datetime.now().isoformat()
            }
    
    def reload_agent(self):
        """
        Reload the agent with current configuration.
        
        Useful for applying configuration changes without restarting the application.
        """
        self._is_initialized = False
        self._agent_status = {}
        self._session_context = {}
        self._meeting_context = {}
        self._proactive_insights_cache = {}
        
        if self.config.agent_enabled:
            try:
                asyncio.create_task(self.initialize())
            except RuntimeError:
                # If no event loop is running, mark for lazy initialization
                pass
        
        logger.info("Agent manager reloaded")
    
    def update_config(self, new_config: ProductionMeetingConfig):
        """
        Update agent configuration and reload if necessary.
        
        Args:
            new_config: New agent configuration
        """
        config_changed = (
            self.config.default_model != new_config.default_model or
            self.config.agent_enabled != new_config.agent_enabled or
            self.config.meeting_focus != new_config.meeting_focus or
            self.config.analysis_depth != new_config.analysis_depth
        )
        
        self.config = new_config
        
        if config_changed:
            self.reload_agent()
        
        logger.info("Agent configuration updated")
    
    def get_integration_info(self) -> Dict[str, Any]:
        """
        Get information about the Strands SDK integration.
        
        Returns:
            Dictionary containing integration details
        """
        return {
            'integration_type': 'Strands SDK',
            'agent_framework': 'Strands Agent',
            'ui_framework': 'Streamlit',
            'database_backend': 'SQLite',
            'visualization_library': 'Plotly Express',
            'supported_features': [
                'Multi-step analysis',
                'Progress tracking',
                'Intelligent visualization',
                'Error recovery',
                'Domain expertise',
                'Tool integration',
                'Query refinement',
                'Educational feedback',
                'Daily briefings',
                'Contextual insights',
                'Multi-domain coordination'
            ],
            'agent_ready': self.is_ready(),
            'config_valid': self.config.agent_enabled,
            'specialized_agents': [
                'Production Analysis Agent',
                'Quality Analysis Agent', 
                'Equipment Analysis Agent',
                'Inventory Analysis Agent'
            ]
        }
    
    def get_streaming_progress(self):
        """
        Generator for streaming progress updates during agent execution.
        
        Yields:
            Dict containing progress update information
        """
        for update in self.get_progress_updates():
            yield update
    
    def shutdown(self):
        """Shutdown the agent manager and clean up resources."""
        try:
            self._is_initialized = False
            self._agent_status = {}
            self._session_context = {}
            self._meeting_context = {}
            self._proactive_insights_cache = {}
            logger.info("Production meeting agent manager shutdown complete")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")