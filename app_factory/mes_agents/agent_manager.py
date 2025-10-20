"""
Agent Manager for MES Agents System.

This module manages the lifecycle and coordination of MES Analysis Agents,
providing a clean interface between the Streamlit UI and the agent system.

Key Features:
- Agent initialization and configuration management
- Query processing with comprehensive error handling
- Progress tracking and status monitoring
- Integration with Strands SDK

Usage:
    manager = MESAgentManager()
    result = await manager.process_query("What are our quality issues?")
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from .config import AgentConfig, default_config
from .mes_analysis_agent import MESAnalysisAgent


class MESAgentManager:
    """
    Manager for MES Analysis Agent integration with Strands SDK.
    
    This manager handles the lifecycle and coordination of the MES Analysis Agent,
    providing a clean interface between the Streamlit UI and the agent system.
    """
    
    def __init__(self, config: Optional[AgentConfig] = None):
        """
        Initialize the MES Agent Manager.
        
        Args:
            config: Agent configuration. Uses default if not provided.
        """
        self.config = config or default_config
        self.agent = None
        self._initialize_agent()
        
    def _initialize_agent(self):
        """Initialize the MES Analysis Agent if enabled."""
        if self.config.agent_enabled:
            try:
                self.agent = MESAnalysisAgent(self.config)
            except Exception as e:
                print(f"Warning: Failed to initialize MES Analysis Agent: {e}")
                self.agent = None
        
    async def process_query(self, query: str, context: Dict = None) -> Dict[str, Any]:
        """
        Process query using the MES Analysis Agent.
        
        Args:
            query: User query string
            context: Optional context dictionary
            
        Returns:
            Dictionary containing agent response
        """
        if not self.agent:
            return {
                'success': False,
                'error': 'MES Analysis Agent not available',
                'message': 'Agent is disabled or failed to initialize',
                'query': query,
                'suggested_actions': [
                    'Check agent configuration',
                    'Verify Strands SDK installation',
                    'Enable agent in configuration'
                ]
            }
        
        try:
            # Process the query using the agent
            result = await self.agent.analyze(query, context or {})
            
            # Ensure the result has the expected structure for UI integration
            if result.get('success', True):
                # Add agent manager metadata
                result['agent_manager'] = {
                    'version': '1.0.0',
                    'integration_layer': 'Strands SDK',
                    'processing_time': result.get('execution_time', 0.0)
                }
                
                # Ensure progress updates are available
                if 'progress_updates' not in result:
                    result['progress_updates'] = self.get_progress_updates()
            
            return result
            
        except Exception as e:
            # Enhanced error handling with comprehensive information
            return {
                'success': False,
                'error': str(e),
                'error_category': 'agent_manager',
                'severity': 'high',
                'user_friendly_message': 'I encountered an issue while processing your request. Let me help you with some alternatives.',
                'root_cause': f'Agent manager error: {str(e)}',
                'query': query,
                'progress_updates': self.get_progress_updates(),
                'suggestions': [
                    'Check database connectivity and agent configuration',
                    'Verify your query format and try again',
                    'Try a simpler query to test the system',
                    'Contact system administrator if issues persist'
                ],
                'recovery_options': [
                    'Retry with a modified query',
                    'Check database schema first',
                    'Try a different analysis approach',
                    'Use basic database queries instead of agent analysis'
                ],
                'educational_content': [
                    '🛠️ **System Status**: The AI agent system may be experiencing temporary issues',
                    '📊 **Alternative**: You can still access data using direct database queries',
                    '🔄 **Recovery**: Most issues resolve themselves with a retry'
                ],
                'alternative_approaches': [
                    'Try asking a simpler question about your manufacturing data',
                    'Check what tables are available in the database',
                    'Ask for help with query formulation',
                    'Request basic data exploration to start'
                ],
                'timestamp': datetime.now().isoformat(),
                'execution_time': 0.0
            }
    
    def get_agent_status(self) -> Dict[str, Any]:
        """
        Return current agent status and capabilities.
        
        Returns:
            Dictionary containing agent status information
        """
        base_status = {
            'agent_type': 'MES Analysis Agent',
            'capabilities': ['production', 'quality', 'equipment', 'inventory', 'multi-domain'],
            'config': {
                'enabled': self.config.agent_enabled,
                'model': self.config.default_model,
                'timeout': self.config.timeout_seconds,
                'analysis_depth': self.config.analysis_depth,
                'max_query_steps': self.config.max_query_steps,
                'progress_updates_enabled': self.config.enable_progress_updates
            },
            'tools_available': [
                'run_sqlite_query',
                'get_database_schema', 
                'create_intelligent_visualization'
            ]
        }
        
        if self.agent:
            # Get detailed status from the agent
            try:
                agent_info = self.agent.get_agent_info()
                base_status.update({
                    'status': 'ready',
                    'agent_info': agent_info,
                    'progress_updates': self.agent.get_progress_updates(),
                    'integration_status': 'Strands SDK integrated successfully'
                })
            except Exception as e:
                base_status.update({
                    'status': 'error',
                    'error': f'Agent info retrieval failed: {str(e)}',
                    'integration_status': 'Strands SDK integration error'
                })
        else:
            base_status.update({
                'status': 'not_available',
                'error': 'Agent not initialized',
                'integration_status': 'Strands SDK not integrated'
            })
        
        return base_status
    
    def is_ready(self) -> bool:
        """
        Check if the agent manager is ready for operation.
        
        Returns:
            True if agent is initialized and ready, False otherwise
        """
        return self.config.agent_enabled and self.agent is not None
    
    def get_progress_updates(self) -> List[Dict[str, Any]]:
        """
        Get current progress updates from the agent.
        
        Returns:
            List of progress update dictionaries
        """
        if self.agent:
            return self.agent.get_progress_updates()
        return []
    
    def reload_agent(self):
        """
        Reload the agent with current configuration.
        
        Useful for applying configuration changes without restarting the application.
        """
        self.agent = None
        self._initialize_agent()
    
    def get_streaming_progress(self):
        """
        Generator for streaming progress updates during agent execution.
        
        Yields:
            Dict containing progress update information
        """
        if self.agent:
            for update in self.agent.get_progress_updates():
                yield update
    
    def update_config(self, new_config: AgentConfig):
        """
        Update agent configuration and reload if necessary.
        
        Args:
            new_config: New agent configuration
        """
        config_changed = (
            self.config.default_model != new_config.default_model or
            self.config.agent_enabled != new_config.agent_enabled
        )
        
        self.config = new_config
        
        if config_changed:
            self.reload_agent()
    
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
                'Educational feedback'
            ],
            'agent_ready': self.is_ready(),
            'config_valid': self.config.agent_enabled
        }
    
    def generate_proactive_suggestions(self, conversation_history: List[Dict]) -> List[str]:
        """
        Generate proactive follow-up questions based on conversation history.
        
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
                "What inventory items are at risk of stockout?"
            ]
        
        # Analyze recent queries to suggest complementary analyses
        recent_queries = [item.get('query', '') for item in conversation_history[-3:]]
        all_queries_text = ' '.join(recent_queries).lower()
        
        suggestions = []
        
        # If user has been asking about one domain, suggest others
        if 'production' in all_queries_text and 'quality' not in all_queries_text:
            suggestions.append("How do quality issues correlate with production problems?")
        
        if 'quality' in all_queries_text and 'equipment' not in all_queries_text:
            suggestions.append("Which equipment issues are causing quality problems?")
        
        if 'equipment' in all_queries_text and 'inventory' not in all_queries_text:
            suggestions.append("How do equipment failures affect inventory consumption?")
        
        if 'inventory' in all_queries_text and 'production' not in all_queries_text:
            suggestions.append("How do inventory shortages impact production schedules?")
        
        # Time-based suggestions
        if not any(time_word in all_queries_text for time_word in ['trend', 'over time', 'historical']):
            suggestions.append("What are the historical trends for these metrics?")
        
        # Comparative analysis suggestions
        if not any(comp_word in all_queries_text for comp_word in ['compare', 'versus', 'vs']):
            suggestions.append("How do these metrics compare across different work centers?")
        
        # Root cause analysis suggestions
        if not any(cause_word in all_queries_text for cause_word in ['cause', 'why', 'reason']):
            suggestions.append("What are the root causes of these issues?")
        
        # Default suggestions if no specific patterns detected
        if not suggestions:
            suggestions.extend([
                "What manufacturing KPIs should we monitor daily?",
                "Which areas have the highest improvement potential?",
                "How can we optimize our overall equipment effectiveness?"
            ])
        
        return suggestions[:3]  # Return top 3 suggestions