"""
Agent-enabled MES Chat interface using Strands SDK.

This module provides an enhanced chat interface that integrates with the MES Analysis Agent
to provide intelligent, multi-step analysis capabilities with progress tracking and 
enhanced result presentation.
"""

import json
import logging
import os
import sys
import time
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

import streamlit as st
import pandas as pd
from dotenv import load_dotenv

# Import shared modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.database import DatabaseManager
# Removed bedrock_utils dependency - using simplified model management
from mes_agents.agent_manager import MESAgentManager
from mes_agents.config import AgentConfig

# Configuration
load_dotenv()
proj_dir = os.path.abspath('')
db_path = os.path.join(proj_dir, 'mes.db')

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize database tool for fallback
db_tool = DatabaseManager(db_path)


def convert_df_to_csv(df):
    """Convert dataframe to CSV for download"""
    return df.to_csv(index=False).encode('utf-8')


def reset_agent_chat():
    """Reset the agent chat state"""
    st.session_state.agent_messages = [
        {
            "role": "assistant", 
            "content": "Welcome to MES Insight Chat with AI Agents! I'm your intelligent manufacturing analyst. How can I help you analyze your MES data today?"
        }
    ]
    st.session_state.agent_conversation_history = []
    st.session_state.agent_last_result = None
    st.session_state.agent_progress = []


def display_progress_updates(progress_updates: List[Dict[str, Any]]):
    """
    Display agent progress updates in the UI.
    
    Args:
        progress_updates: List of progress update dictionaries
    """
    if not progress_updates:
        return
    
    with st.expander("🔄 Agent Analysis Progress", expanded=True):
        for i, update in enumerate(progress_updates):
            status_icon = {
                'initializing': '🚀',
                'planning': '🧠', 
                'executing': '⚙️',
                'analyzing': '📊',
                'completing': '✅',
                'completed': '🎉',
                'error': '❌'
            }.get(update.get('status', 'executing'), '⚙️')
            
            timestamp = update.get('timestamp', '')
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    time_str = dt.strftime('%H:%M:%S')
                except:
                    time_str = ''
            else:
                time_str = ''
            
            st.write(f"{status_icon} **Step {update.get('step', i+1)}**: {update.get('message', 'Processing...')} {time_str}")


def display_agent_response(response: Dict[str, Any], message_index: int):
    """
    Display agent response with enhanced error handling and formatting.
    
    Args:
        response: Agent response dictionary
        message_index: Index of the message for unique keys
    """
    # Handle different types of responses
    if response.get('partial_success'):
        # Partial results available
        display_partial_results_response(response, message_index)
        return
    elif not response.get('success', True):
        # Error response with enhanced information
        display_enhanced_error_response(response, message_index)
        return
    
    # Display successful analysis
    analysis_content = response.get('analysis', '')
    if analysis_content:
        st.markdown(analysis_content)
    
    # Display progress updates if available
    progress_updates = response.get('progress_updates', [])
    if progress_updates:
        display_progress_updates(progress_updates)
    
    # Display execution metadata
    execution_time = response.get('execution_time', 0)
    analysis_depth = response.get('analysis_depth', 'standard')
    agent_type = response.get('agent_type', 'MES Analysis Agent')
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Analysis Time", f"{execution_time:.2f}s")
    with col2:
        st.metric("Analysis Depth", analysis_depth.title())
    with col3:
        st.metric("Agent Type", agent_type.replace('MES ', ''))
    
    # Display capabilities used
    capabilities_used = response.get('capabilities_used', [])
    if capabilities_used:
        st.markdown("**Analysis Capabilities Used:**")
        caps_text = " • ".join(cap.replace('_', ' ').title() for cap in capabilities_used)
        st.info(caps_text)
    
    # Display follow-up suggestions
    follow_ups = response.get('follow_up_suggestions', [])
    if follow_ups:
        st.markdown("**💡 Suggested Follow-up Analyses:**")
        cols = st.columns(min(len(follow_ups), 2))
        for i, suggestion in enumerate(follow_ups):
            with cols[i % 2]:
                if st.button(suggestion, key=f"followup_{message_index}_{i}", use_container_width=True):
                    st.session_state.agent_messages.append({"role": "user", "content": suggestion})
                    st.session_state["process_agent_query"] = suggestion
                    st.rerun()


def display_enhanced_error_response(response: Dict[str, Any], message_index: int):
    """
    Display enhanced error response with comprehensive information and recovery options.
    
    Args:
        response: Error response dictionary
        message_index: Index of the message for unique keys
    """
    # Main error message
    error_category = response.get('error_category', 'unknown')
    severity = response.get('severity', 'medium')
    
    # Color code by severity
    severity_colors = {
        'low': '🟢',
        'medium': '🟡', 
        'high': '🟠',
        'critical': '🔴'
    }
    
    severity_icon = severity_colors.get(severity, '🟡')
    
    st.error(f"{severity_icon} **{response.get('user_friendly_message', 'Analysis Error')}**")
    
    # Show root cause if available
    if response.get('root_cause'):
        st.info(f"**Root Cause**: {response['root_cause']}")
    
    # Recovery options in expandable section
    if response.get('suggestions') or response.get('recovery_options'):
        with st.expander("🔧 Recovery Options", expanded=True):
            recovery_options = response.get('recovery_options', response.get('suggestions', []))
            for i, option in enumerate(recovery_options):
                st.write(f"{i+1}. {option}")
    
    # Educational content
    if response.get('educational_content'):
        with st.expander("💡 Learning Tips", expanded=False):
            for tip in response['educational_content']:
                st.markdown(tip)
    
    # Alternative approaches
    if response.get('alternative_approaches'):
        with st.expander("🎯 Alternative Approaches", expanded=False):
            st.markdown("**Try these alternative questions:**")
            cols = st.columns(min(len(response['alternative_approaches']), 2))
            for i, approach in enumerate(response['alternative_approaches']):
                with cols[i % 2]:
                    if st.button(approach, key=f"alt_{message_index}_{i}", use_container_width=True):
                        st.session_state.agent_messages.append({"role": "user", "content": approach})
                        st.session_state["process_agent_query"] = approach
                        st.rerun()
    
    # Technical details in collapsible section
    if response.get('technical_details') or response.get('error_details'):
        with st.expander("🔍 Technical Details", expanded=False):
            if response.get('technical_details'):
                st.code(response['technical_details'])
            
            if response.get('error_details'):
                st.json(response['error_details'])
    
    # Execution metadata
    if response.get('execution_time') or response.get('error_category'):
        col1, col2, col3 = st.columns(3)
        with col1:
            if response.get('execution_time'):
                st.metric("Execution Time", f"{response['execution_time']:.2f}s")
        with col2:
            st.metric("Error Category", error_category.replace('_', ' ').title())
        with col3:
            st.metric("Severity", severity.title())


def display_partial_results_response(response: Dict[str, Any], message_index: int):
    """
    Display partial results when analysis was interrupted but some progress was made.
    
    Args:
        response: Partial results response dictionary
        message_index: Index of the message for unique keys
    """
    # Main message about partial results
    st.warning("⏱️ **Analysis Interrupted - Partial Results Available**")
    st.info(response.get('message', 'Analysis was interrupted, but some progress was made.'))
    
    # Progress summary if available
    if response.get('progress_summary'):
        progress = response['progress_summary']
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Completed Steps", f"{progress.get('completed_steps', 0)}/{progress.get('total_steps', 0)}")
        with col2:
            completion_pct = progress.get('completion_percentage', 0)
            st.metric("Progress", f"{completion_pct:.1f}%")
        with col3:
            st.metric("Last Action", progress.get('last_completed_action', 'Unknown')[:20] + "...")
    
    # Show partial results if available
    if response.get('partial_results'):
        with st.expander("📊 Partial Results", expanded=True):
            partial_data = response['partial_results']
            
            if partial_data.get('collected_data'):
                st.json(partial_data['collected_data'])
            
            if partial_data.get('suggested_simplified_query'):
                st.markdown("**Suggested Simplified Query:**")
                st.code(partial_data['suggested_simplified_query'])
    
    # Completion suggestions
    if response.get('completion_suggestions'):
        with st.expander("✅ How to Complete the Analysis", expanded=True):
            st.markdown("**Suggestions to get complete results:**")
            for i, suggestion in enumerate(response['completion_suggestions']):
                st.write(f"{i+1}. {suggestion}")
    
    # Next steps
    if response.get('next_steps'):
        with st.expander("🎯 Next Steps", expanded=False):
            cols = st.columns(min(len(response['next_steps']), 2))
            for i, step in enumerate(response['next_steps']):
                with cols[i % 2]:
                    if st.button(step, key=f"next_{message_index}_{i}", use_container_width=True):
                        st.session_state.agent_messages.append({"role": "user", "content": step})
                        st.session_state["process_agent_query"] = step
                        st.rerun()
    
    # Error analysis if available
    if response.get('error_analysis'):
        with st.expander("🔍 Error Analysis", expanded=False):
            error_analysis = response['error_analysis']
            st.write(f"**Category**: {error_analysis.get('category', 'Unknown').replace('_', ' ').title()}")
            st.write(f"**Root Cause**: {error_analysis.get('root_cause', 'Unknown')}")
            
            if error_analysis.get('educational_content'):
                st.markdown("**Learning Tips:**")
                for tip in error_analysis['educational_content']:
                    st.markdown(tip)


def display_agent_status_sidebar(agent_manager: MESAgentManager):
    """
    Display agent status and configuration in the sidebar.
    
    Args:
        agent_manager: The MES agent manager instance
    """
    st.subheader("🤖 Agent Status")
    
    status = agent_manager.get_agent_status()
    
    # Agent status indicator
    status_color = {
        'ready': '🟢',
        'not_available': '🔴', 
        'error': '🟡'
    }.get(status.get('status'), '🔴')
    
    st.write(f"{status_color} **Status**: {status.get('status', 'unknown').title()}")
    
    if status.get('status') == 'ready':
        st.success("Agent ready for analysis")
        
        # Display agent capabilities
        capabilities = status.get('capabilities', [])
        if capabilities:
            st.markdown("**Capabilities:**")
            for cap in capabilities:
                st.write(f"• {cap.title()}")
    
    elif status.get('status') == 'not_available':
        st.error("Agent not available")
        if status.get('error'):
            st.write(f"Error: {status['error']}")
    
    # Display configuration
    config = status.get('config', {})
    if config:
        with st.expander("⚙️ Agent Configuration"):
            st.write(f"**Model**: {config.get('model', 'Unknown')}")
            st.write(f"**Analysis Depth**: {config.get('analysis_depth', 'standard').title()}")
            st.write(f"**Timeout**: {config.get('timeout', 120)}s")
            st.write(f"**Max Steps**: {config.get('max_query_steps', 5)}")
            st.write(f"**Progress Updates**: {'✅' if config.get('progress_updates_enabled') else '❌'}")
    
    # Display integration info
    integration_info = agent_manager.get_integration_info()
    with st.expander("🔗 Integration Details"):
        st.write(f"**Framework**: {integration_info.get('integration_type', 'Unknown')}")
        st.write(f"**Agent Ready**: {'✅' if integration_info.get('agent_ready') else '❌'}")
        st.write(f"**Database**: {integration_info.get('database_backend', 'Unknown')}")
        st.write(f"**Visualization**: {integration_info.get('visualization_library', 'Unknown')}")


async def process_agent_query(agent_manager: MESAgentManager, query: str) -> Dict[str, Any]:
    """
    Process query using the agent manager.
    
    Args:
        agent_manager: The MES agent manager
        query: User query string
        
    Returns:
        Agent response dictionary
    """
    # Prepare context from conversation history
    context = {
        'history': st.session_state.get('agent_conversation_history', []),
        'previous_results': [st.session_state.get('agent_last_result')] if st.session_state.get('agent_last_result') else [],
        'preferences': {
            'analysis_depth': st.session_state.get('analysis_depth', 'standard'),
            'include_visualizations': True,
            'include_follow_ups': True
        }
    }
    
    # Process the query
    result = await agent_manager.process_query(query, context)
    
    # Update conversation history
    st.session_state.agent_conversation_history.append({
        'query': query,
        'timestamp': datetime.now().isoformat(),
        'summary': result.get('analysis', '')[:200] + '...' if result.get('analysis') else 'Analysis completed'
    })
    
    # Store last result
    st.session_state.agent_last_result = result
    
    return result


def run_agent_mes_chat():
    """Main function to run the agent-enabled MES chat interface"""
    
    # Page configuration
    st.header("🤖 MES Insight Chat - AI Agent Edition")
    st.markdown("""
    **Enhanced with Intelligent AI Agents** - This advanced chatbot uses specialized AI agents 
    to provide comprehensive analysis of your Manufacturing Execution System (MES) data.
    
    Ask complex questions about production, quality, equipment, and inventory - the agents will 
    break down your queries into logical steps and provide detailed insights.
    """)
    
    # Initialize session state for agent chat
    if "agent_messages" not in st.session_state:
        reset_agent_chat()
    
    if "agent_conversation_history" not in st.session_state:
        st.session_state.agent_conversation_history = []
        
    if "agent_last_result" not in st.session_state:
        st.session_state.agent_last_result = None
        
    if "agent_progress" not in st.session_state:
        st.session_state.agent_progress = []
    
    # Initialize agent manager with default configuration
    try:
        # Create agent configuration with defaults
        agent_config = AgentConfig()
        
        # Initialize agent manager
        agent_manager = MESAgentManager(agent_config)
        
    except Exception as e:
        st.error(f"Failed to initialize agent manager: {e}")
        st.stop()
    
    # Sidebar configuration
    with st.sidebar:
        st.subheader("⚙️ Agent Chat Settings")
        
        # Reset chat button
        st.button("🔄 Reset Agent Chat", on_click=reset_agent_chat, use_container_width=True)
        
        # Return to main menu button
        if st.button("🏠 Return to Main Menu", use_container_width=True):
            st.session_state.app_mode = None
            st.rerun()
        
        st.divider()
        
        # Agent configuration
        st.subheader("🤖 Agent Configuration")
        
        # Analysis depth selection
        analysis_depth = st.selectbox(
            "Analysis Depth",
            options=["quick", "standard", "comprehensive"],
            index=1,
            help="Choose how deep the agent should analyze your queries",
            key="analysis_depth"
        )
        
        # Update agent config if changed
        if agent_config.analysis_depth != analysis_depth:
            agent_config.analysis_depth = analysis_depth
            agent_manager.update_config(agent_config)
        
        # Model selection using config
        available_models = agent_config.SUPPORTED_MODELS
        model_display_names = agent_config.get_model_display_names()
        
        current_model_index = 0
        if agent_config.default_model in available_models:
            current_model_index = available_models.index(agent_config.default_model)
        
        selected_model_index = st.selectbox(
            "AI Model",
            range(len(available_models)),
            index=current_model_index,
            format_func=lambda x: model_display_names.get(available_models[x], available_models[x]),
            help="Select the AI model for agent analysis",
            key="selected_model"
        )
        
        selected_model_id = available_models[selected_model_index]
        if agent_config.default_model != selected_model_id:
            agent_config.default_model = selected_model_id
            agent_manager.update_config(agent_config)
        
        st.divider()
        
        # Display agent status
        display_agent_status_sidebar(agent_manager)
        
        st.divider()
        
        # About section
        with st.expander("ℹ️ About Agent Chat"):
            st.markdown("""
            **AI Agent Features:**
            
            🧠 **Multi-Step Analysis**: Agents break down complex queries into logical steps
            
            📊 **Domain Expertise**: Specialized knowledge in production, quality, equipment, and inventory
            
            🔄 **Progress Tracking**: Real-time updates on analysis progress
            
            💡 **Intelligent Suggestions**: Proactive follow-up recommendations
            
            🎯 **Error Recovery**: Smart error handling and alternative approaches
            
            📈 **Advanced Visualizations**: AI-selected charts based on data characteristics
            """)
    
    # Main chat interface
    main_col = st.container()
    
    with main_col:
        # Load example questions
        try:
            questions_path = Path(__file__).parent.parent / 'data' / 'sample_questions.json'
            if not questions_path.exists():
                questions_path = Path('sample_questions.json')
                
            with open(questions_path, 'r', encoding="utf-8") as file:
                question_data = json.load(file)
                category_questions = question_data.get('categories', {})
        except Exception as e:
            logger.warning(f"Could not load example questions: {e}")
            category_questions = {}
    
        # Example questions for agents
        if category_questions:
            st.subheader("🎯 Agent-Powered Example Questions")
            st.markdown("*These questions showcase the agent's multi-step analysis capabilities*")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("##### 🏭 Production Analysis")
                for q in category_questions.get("🏭 Production", [])[:3]:
                    if st.button(f"🤖 {q}", key=f"agent_prod_{hash(q)}", use_container_width=True):
                        st.session_state.agent_messages.append({"role": "user", "content": q})
                        st.session_state["process_agent_query"] = q
                        st.rerun()
                        
                st.markdown("##### 🔧 Equipment Analysis")
                for q in category_questions.get("🔧 Machines", [])[:3]:
                    if st.button(f"🤖 {q}", key=f"agent_mach_{hash(q)}", use_container_width=True):
                        st.session_state.agent_messages.append({"role": "user", "content": q})
                        st.session_state["process_agent_query"] = q
                        st.rerun()
            
            with col2:
                st.markdown("##### 📦 Inventory Analysis")
                for q in category_questions.get("📦 Inventory", [])[:3]:
                    if st.button(f"🤖 {q}", key=f"agent_inv_{hash(q)}", use_container_width=True):
                        st.session_state.agent_messages.append({"role": "user", "content": q})
                        st.session_state["process_agent_query"] = q
                        st.rerun()
                        
                st.markdown("##### ⚠️ Quality Analysis")
                for q in category_questions.get("⚠️ Quality", [])[:3]:
                    if st.button(f"🤖 {q}", key=f"agent_qual_{hash(q)}", use_container_width=True):
                        st.session_state.agent_messages.append({"role": "user", "content": q})
                        st.session_state["process_agent_query"] = q
                        st.rerun()
        
        st.divider()
        
        # Chat history container
        st.subheader("💬 Agent Conversation")
        
        # Initialize process_agent_query if it doesn't exist
        if "process_agent_query" not in st.session_state:
            st.session_state["process_agent_query"] = None
        
        # Display chat history
        for i, message in enumerate(st.session_state.agent_messages):
            if message["role"] == "user":
                with st.chat_message("user"):
                    st.write(message["content"])
            else:
                with st.chat_message("assistant"):
                    # Check if this is an agent response
                    if isinstance(message["content"], dict):
                        display_agent_response(message["content"], i)
                    else:
                        # Simple text message
                        st.markdown(message["content"])
        
        # Chat input
        user_input = st.chat_input("Ask your AI agent about manufacturing data...")
        
        if user_input:
            st.session_state.agent_messages.append({"role": "user", "content": user_input})
            st.session_state["process_agent_query"] = user_input
            st.rerun()
    
    # Process agent query if needed
    if st.session_state["process_agent_query"]:
        query = st.session_state["process_agent_query"]
        st.session_state["process_agent_query"] = None  # Clear the flag
        
        # Check if agent is ready
        if not agent_manager.is_ready():
            st.error("Agent is not ready. Please check the configuration and try again.")
            return
        
        # Create a placeholder for progress updates
        progress_placeholder = st.empty()
        
        with st.spinner("🤖 Agent is analyzing your query..."):
            try:
                # Process the query asynchronously
                response = asyncio.run(process_agent_query(agent_manager, query))
                
                # Add the response to messages
                st.session_state.agent_messages.append({
                    "role": "assistant",
                    "content": response
                })
                
                # Clear progress placeholder
                progress_placeholder.empty()
                
                # Rerun to display the new message
                st.rerun()
                
            except Exception as e:
                logger.error(f"Error processing agent query: {e}")
                error_response = {
                    'success': False,
                    'error': str(e),
                    'message': 'Failed to process query with agent',
                    'query': query,
                    'suggested_actions': [
                        'Check agent configuration',
                        'Verify database connectivity', 
                        'Try a simpler query',
                        'Contact system administrator'
                    ]
                }
                
                st.session_state.agent_messages.append({
                    "role": "assistant", 
                    "content": error_response
                })
                
                progress_placeholder.empty()
                st.rerun()


if __name__ == "__main__":
    run_agent_mes_chat()