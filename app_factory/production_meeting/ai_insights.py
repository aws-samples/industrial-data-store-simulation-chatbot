"""
AI-powered insights and analysis for the Production Meeting

This module provides AI-powered insights using production meeting agents
instead of direct Bedrock API calls, following the agent-as-tools pattern.
"""

import streamlit as st
import pandas as pd
import numpy as np
import logging
import time
import plotly.express as px
import asyncio
from datetime import datetime

from app_factory.shared.database import DatabaseManager
from app_factory.shared.db_utils import today, days_ahead, date_diff_days
from app_factory.production_meeting_agents.agent_manager import ProductionMeetingAgentManager
from app_factory.production_meeting_agents.config import default_config
from app_factory.production_meeting.analysis_cache_manager import AnalysisCacheManager

# Configure logging for AI insights
logger = logging.getLogger(__name__)

# Initialize database manager, agent manager, and cache manager
db_manager = DatabaseManager()
agent_manager = ProductionMeetingAgentManager(default_config)
cache_manager = AnalysisCacheManager()


def provide_tab_insights(tab_name, dashboard_data=None):
    """
    Provide contextual insights for dashboard tabs using production meeting agents
    
    Args:
        tab_name (str): Name of the dashboard tab (production, quality, equipment, inventory)
        dashboard_data (dict, optional): Current dashboard data for context
        
    Returns:
        str: AI-generated contextual insights for the tab
    """
    logger.info(f"Providing tab insights for: {tab_name}")
    
    try:
        # Use the agent manager's contextual insights functionality with proper async handling
        insights = asyncio.run(agent_manager.get_contextual_insights(dashboard_data or {}, tab_name))
        logger.info(f"Successfully generated tab insights for {tab_name}")
        return insights
        
    except Exception as e:
        logger.error(f"Error generating tab insights for {tab_name}: {e}")
        return f"Unable to generate insights for {tab_name} at this time. Please try refreshing the page."

def generate_ai_insight(context, query=None, dashboard_data=None, model_id=None, temperature=0.1, include_historical=True):
    """
    Generate AI insights based on dashboard data using production meeting agents
    
    Args:
        context (str): The context for the AI (production, quality, etc.)
        query (str, optional): Specific question to answer, if any
        dashboard_data (dict, optional): Preloaded dashboard data
        model_id (str, optional): Model ID (maintained for compatibility, not used)
        temperature (float, optional): Temperature (maintained for compatibility, not used)
        include_historical (bool): Whether to include historical context
        
    Returns:
        str: AI-generated insight
    """
    logger.info(f"Generating AI insight for context: {context}, query: {query[:50] if query else 'None'}...")
    
    # Initialize agent manager if not ready
    if not agent_manager.is_ready():
        logger.warning("Agent manager not ready, attempting initialization")
        try:
            # Run initialization in event loop if available
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Create a task for initialization
                asyncio.create_task(agent_manager.initialize())
            else:
                # Run synchronously if no event loop
                asyncio.run(agent_manager.initialize())
            logger.info("Agent manager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize agent manager: {e}")
            return f"**Agent Initialization Error**\n\nUnable to initialize production meeting agents: {str(e)}\n\nPlease check the agent configuration and try again."
    
    # Create context for agent processing
    agent_context = {
        'context_type': context,
        'include_historical': include_historical,
        'dashboard_data': dashboard_data or {},
        'query_type': 'specific' if query else 'contextual'
    }
    
    # Create agent query based on context and user input
    if query:
        # User provided a specific query
        agent_query = f"""Analyze the {context} context for this specific question: {query}
        
        {'Include historical context and trends in your analysis.' if include_historical else ''}
        
        Provide a concise, informative, and fact-based answer focusing on the most important insights 
        related to the question. Use bullet points where appropriate."""
    else:
        # Generate context-specific insights
        context_queries = {
            'production': f"""Analyze current production performance and provide insights on:
                1. Production performance against targets
                2. {'Historical trends and performance changes' if include_historical else 'Key bottlenecks or issues'}
                3. Recommendations for improving throughput or efficiency
                
                Be concise but specific. Focus on actionable information for production meetings.""",
            
            'machines': f"""Analyze current equipment status and provide insights on:
                1. Machine availability and performance
                2. {'Historical equipment trends and performance changes' if include_historical else 'Critical maintenance issues'}
                3. Recommendations for improving equipment reliability
                
                Be concise but specific. Focus on actionable information for production meetings.""",
            
            'equipment': f"""Analyze current equipment status and provide insights on:
                1. Machine availability and performance
                2. {'Historical equipment trends and performance changes' if include_historical else 'Critical maintenance issues'}
                3. Recommendations for improving equipment reliability
                
                Be concise but specific. Focus on actionable information for production meetings.""",
            
            'quality': f"""Analyze current quality metrics and provide insights on:
                1. Quality metrics and defect patterns
                2. {'Historical quality trends and performance changes' if include_historical else 'Critical quality issues'}
                3. Recommendations for improving quality and reducing defects
                
                Be concise but specific. Focus on actionable information for production meetings.""",
            
            'inventory': f"""Analyze current inventory status and provide insights on:
                1. Critical inventory shortages or concerns
                2. {'Historical consumption patterns and trends' if include_historical else 'Inventory trends and priorities'}
                3. Recommendations for inventory management
                
                Be concise but specific. Focus on actionable information for production meetings.""",
            
            'summary': f"""Generate a concise daily production meeting summary covering:
                1. Overall production status and key metrics{'compared to historical trends' if include_historical else ''}
                2. Critical issues requiring immediate attention
                3. Top recommendations for today's focus
                
                Be very concise - readable in under 30 seconds. Focus on actionable information."""
        }
        
        agent_query = context_queries.get(context, f"""Analyze the current {context} data and provide comprehensive insights for production meetings.
            
            {'Include historical context and trends where relevant.' if include_historical else ''}
            
            Focus on actionable information and patterns rather than just repeating data.""")
    
    # Process query using production meeting agents
    try:
        with st.spinner("Generating AI insights using production meeting agents..."):
            start_time = time.time()
            logger.debug(f"Processing agent query: {agent_query[:100]}...")
            
            # Process query using agent manager with optimized async handling
            try:
                # Use the agent manager's process_query method directly
                # The agent manager handles async/sync coordination internally
                response = asyncio.run(agent_manager.process_query(agent_query, agent_context))
                logger.debug(f"Agent response received: success={response.get('success', False)}")
                
            except asyncio.TimeoutError:
                logger.warning("Agent processing timed out, providing partial results")
                response = {
                    'success': False,
                    'error': 'timeout',
                    'user_message': "Analysis is taking longer than expected. Please try a more specific question or try again.",
                    'suggested_actions': [
                        'Try a more specific question',
                        'Check if the database is responding',
                        'Try again in a moment'
                    ]
                }
            except Exception as async_error:
                logger.error(f"Async processing failed: {async_error}")
                # Provide a fallback response
                response = {
                    'success': False,
                    'error': 'processing_error',
                    'user_message': f"Agent processing encountered an issue: {str(async_error)}",
                    'suggested_actions': [
                        'Check agent configuration',
                        'Verify database connectivity',
                        'Try refreshing the page'
                    ]
                }
            
            elapsed_time = time.time() - start_time
            logger.info(f"Agent processing completed in {elapsed_time:.2f}s")
            
            if response.get('success', False):
                output = response.get('analysis', 'No analysis available')
                agent_execution_time = response.get('execution_time', elapsed_time)
                
                # Add attribution with agent information
                output += f"\n\n<small><i>Generated by Production Meeting Agent in {agent_execution_time:.1f}s</i></small>"
                
                logger.info(f"Successfully generated AI insight for context: {context}")
                return output
            else:
                # Handle agent error with detailed logging
                error_msg = response.get('error', 'Unknown agent error')
                user_message = response.get('user_message', error_msg)
                logger.warning(f"Agent processing failed: {error_msg}")
                
                return f"""
                **Agent Processing Error**
                
                The production meeting agent encountered an issue:
                
                {user_message}
                
                Suggested actions:
                {chr(10).join('- ' + action for action in response.get('suggested_actions', ['Check agent configuration', 'Try again in a moment']))}
                """
            
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Critical error generating insights with production meeting agents: {error_msg}", exc_info=True)
        
        # Provide a helpful error message with debugging information
        return f"""
        **Agent System Error**
        
        There was a problem with the production meeting agent system:
        
        ```
        {error_msg}
        ```
        
        Possible solutions:
        - Check that the production meeting agents are properly configured
        - Verify that the Strands SDK is installed and configured
        - Check the application logs for more details
        - Try refreshing the page and attempting again
        
        If the problem persists, contact your system administrator.
        
        <small>Error logged at {time.strftime('%Y-%m-%d %H:%M:%S')}</small>
        """

def generate_predictive_insights():
    """Generate predictive insights from the manufacturing data"""
    logger.info("Generating predictive insights")
    st.subheader("🔮 Predictive Insights")
    
    # Predict inventory shortages based on current levels and consumption patterns
    inventory_query = """
    SELECT 
        i.Name as ItemName,
        i.Category,
        i.Quantity as CurrentQuantity,
        i.ReorderLevel,
        i.LeadTime as LeadTimeInDays,
        s.Name as SupplierName
    FROM 
        Inventory i
    JOIN 
        Suppliers s ON i.SupplierID = s.SupplierID
    WHERE 
        i.Quantity < i.ReorderLevel * 1.5
    ORDER BY 
        (i.Quantity * 1.0 / i.ReorderLevel) ASC
    LIMIT 10
    """
    
    result = db_manager.execute_query(inventory_query)
    
    if result["success"] and result["row_count"] > 0:
        inventory_df = pd.DataFrame(result["rows"])
        
        # Get consumption patterns
        from app_factory.shared.db_utils import days_ago
        thirty_days_ago = days_ago(30)

        consumption_query = """
        SELECT
            i.ItemID,
            i.Name as ItemName,
            AVG(mc.ActualQuantity) as AvgDailyConsumption,
            COUNT(DISTINCT wo.OrderID) as TotalOrders
        FROM
            MaterialConsumption mc
        JOIN
            Inventory i ON mc.ItemID = i.ItemID
        JOIN
            WorkOrders wo ON mc.OrderID = wo.OrderID
        WHERE
            mc.ConsumptionDate >= :thirty_days_ago
        GROUP BY
            i.ItemID, i.Name
        """

        consumption_result = db_manager.execute_query(consumption_query, {"thirty_days_ago": thirty_days_ago})
        
        if consumption_result["success"] and consumption_result["row_count"] > 0:
            consumption_df = pd.DataFrame(consumption_result["rows"])
            
            # Merge inventory with consumption data
            prediction_df = inventory_df.merge(consumption_df, on='ItemName', how='left')
            
            # Fill NAs for items with no recent consumption
            prediction_df['AvgDailyConsumption'] = prediction_df['AvgDailyConsumption'].fillna(0)
            
            # Calculate days until stockout (based on current consumption patterns)
            prediction_df['DaysUntilStockout'] = np.where(
                prediction_df['AvgDailyConsumption'] > 0,
                prediction_df['CurrentQuantity'] / prediction_df['AvgDailyConsumption'],
                float('inf')
            )
            
            # Filter to items that will stock out before lead time replenishment
            critical_items = prediction_df[prediction_df['DaysUntilStockout'] < prediction_df['LeadTimeInDays']]
            
            if not critical_items.empty:
                st.write("### Predicted Inventory Shortages")
                
                # Create risk level
                critical_items['RiskLevel'] = np.where(
                    critical_items['DaysUntilStockout'] < critical_items['LeadTimeInDays'] * 0.5,
                    'High',
                    'Medium'
                )
                
                # Sort by risk level and days until stockout
                critical_items = critical_items.sort_values(['RiskLevel', 'DaysUntilStockout'])
                
                for i, row in critical_items.iterrows():
                    with st.container():
                        cols = st.columns([1, 5])
                        
                        risk_color = "red" if row['RiskLevel'] == 'High' else "orange"
                        
                        with cols[0]:
                            st.markdown(f"<span style='color:{risk_color};font-weight:bold'>{row['RiskLevel']} Risk</span>", unsafe_allow_html=True)
                        
                        with cols[1]:
                            st.write(f"**{row['ItemName']}** ({row['Category']})")
                            st.write(f"Will stock out in **{row['DaysUntilStockout']:.1f} days** but lead time is **{row['LeadTimeInDays']} days**")
                            st.progress(min(1.0, row['CurrentQuantity'] / row['ReorderLevel']))
        
        # Find upcoming machine capacity issues
        seven_days_ahead = days_ahead(7)

        capacity_query = """
        SELECT
            wc.Name as WorkCenterName,
            COUNT(wo.OrderID) as PlannedOrders,
            SUM(wo.Quantity) as TotalQuantity,
            wc.Capacity as HourlyCapacity,
            SUM(wo.Quantity) / wc.Capacity as EstimatedHours
        FROM
            WorkOrders wo
        JOIN
            WorkCenters wc ON wo.WorkCenterID = wc.WorkCenterID
        WHERE
            wo.Status = 'scheduled'
            AND wo.PlannedStartTime <= :seven_days_ahead
        GROUP BY
            wc.Name, wc.Capacity
        ORDER BY
            EstimatedHours DESC
        """

        capacity_result = db_manager.execute_query(capacity_query, {"seven_days_ahead": seven_days_ahead})
        
        if capacity_result["success"] and capacity_result["row_count"] > 0:
            capacity_df = pd.DataFrame(capacity_result["rows"])
            
            # Calculate days of work
            capacity_df['DaysOfWork'] = capacity_df['EstimatedHours'] / 8  # Assuming 8-hour shifts
            
            # Identify potential capacity constraints
            constrained_centers = capacity_df[capacity_df['DaysOfWork'] > 5]  # More than 5 days of work in 7-day window
            
            if not constrained_centers.empty:
                st.write("### Predicted Capacity Constraints (Next 7 Days)")
                
                for i, row in constrained_centers.iterrows():
                    with st.container():
                        st.write(f"**{row['WorkCenterName']}**: {row['DaysOfWork']:.1f} days of work scheduled ({row['PlannedOrders']} orders, {int(row['TotalQuantity']):,} units)")
                        
                        # Calculate and display utilization
                        utilization = min(row['DaysOfWork'] / 5, 1.0)  # 5 working days is 100% utilization
                        
                        # Color based on utilization
                        if utilization > 1.2:  # Over 120% utilization
                            bar_color = "red"
                            message = "Critical overload"
                        elif utilization > 1.0:  # 100-120% utilization
                            bar_color = "orange"
                            message = "Slight overload"
                        else:
                            bar_color = "blue"
                            message = "Within capacity"
                        
                        st.progress(min(utilization, 1.0))
                        st.markdown(f"<span style='color:{bar_color}'>{message} - {utilization * 100:.0f}% utilization</span>", unsafe_allow_html=True)
        
        # Find upcoming maintenance issues
        today_str = today()
        week_ahead = days_ahead(7)

        maintenance_query = """
        SELECT
            m.Name as MachineName,
            m.Type as MachineType,
            wc.Name as WorkCenterName,
            m.NextMaintenanceDate
        FROM
            Machines m
        JOIN
            WorkCenters wc ON m.WorkCenterID = wc.WorkCenterID
        WHERE
            m.NextMaintenanceDate >= :today AND m.NextMaintenanceDate <= :week_ahead
        ORDER BY
            m.NextMaintenanceDate ASC
        """

        maintenance_result = db_manager.execute_query(
            maintenance_query,
            {"today": today_str, "week_ahead": week_ahead}
        )

        if maintenance_result["success"] and maintenance_result["row_count"] > 0:
            st.write("### Upcoming Machine Maintenance")

            maintenance_df = pd.DataFrame(maintenance_result["rows"])
            # Calculate DaysUntilMaintenance in Python (replaces julianday)
            maintenance_df["DaysUntilMaintenance"] = maintenance_df["NextMaintenanceDate"].apply(
                lambda x: date_diff_days(x[:10] if x else today_str, today_str)
            )

            # Get production schedule for impacted machines
            for i, row in maintenance_df.iterrows():
                # Query for work orders that might be impacted
                # Use parameterized query to prevent SQL injection
                impact_query = """
                SELECT
                    COUNT(wo.OrderID) as AffectedOrders,
                    SUM(wo.Quantity) as AffectedQuantity
                FROM
                    WorkOrders wo
                WHERE
                    wo.MachineID = (SELECT MachineID FROM Machines WHERE Name = :machine_name)
                    AND wo.Status = 'scheduled'
                    AND wo.PlannedStartTime <= :maintenance_date
                    AND wo.PlannedEndTime >= :maintenance_date
                """

                impact_result = db_manager.execute_query(
                    impact_query,
                    {
                        "machine_name": row['MachineName'],
                        "maintenance_date": row['NextMaintenanceDate']
                    }
                )
                
                if impact_result["success"] and impact_result["row_count"] > 0:
                    impact_data = impact_result["rows"][0]
                    
                    with st.container():
                        st.write(f"**{row['MachineName']}** in {row['WorkCenterName']}")
                        st.write(f"Maintenance due in {row['DaysUntilMaintenance']:.1f} days")
                        
                        if impact_data['AffectedOrders'] > 0:
                            st.warning(f"**Production Impact**: {impact_data['AffectedOrders']} orders ({impact_data['AffectedQuantity']} units) may be affected")
                        else:
                            st.success("No scheduled orders will be impacted by this maintenance")
    else:
        st.info("No critical inventory predictions found")







def display_cached_analysis(analysis_data, analysis_type):
    """Display cached analysis results"""
    analyses = analysis_data.get('analyses', {})
    
    if analysis_type == "Quick Summary":
        # Display all cached analyses in summary format
        st.subheader("📊 Daily Production Summary (Cached)")
        
        # Show cache info
        generated_at = datetime.fromisoformat(analysis_data['generated_at'])
        st.info(f"Analysis generated: {generated_at.strftime('%Y-%m-%d %H:%M')} | "
                f"Execution time: {analysis_data.get('total_execution_time', 0):.1f}s")
        
        # Display each analysis in tabs
        if analyses:
            tab_names = []
            tab_data = []
            
            for key, analysis in analyses.items():
                if 'analysis' in analysis:
                    display_name = key.replace('_', ' ').title()
                    tab_names.append(display_name)
                    tab_data.append(analysis)
            
            if tab_names:
                tabs = st.tabs(tab_names)
                
                for i, (tab, data) in enumerate(zip(tabs, tab_data)):
                    with tab:
                        st.markdown(data['analysis'])
                        
                        # Show follow-up suggestions if available
                        follow_ups = data.get('follow_up_suggestions', [])
                        if follow_ups:
                            st.markdown("**💡 Suggested Follow-ups:**")
                            for j, suggestion in enumerate(follow_ups[:3]):
                                if st.button(suggestion, key=f"cached_followup_{i}_{j}"):
                                    # Switch to conversational mode with this question
                                    st.session_state.switch_to_chat = suggestion
                                    st.rerun()
        else:
            st.warning("No cached analysis data available")
    
    else:
        # For other analysis types, show specific cached data if available
        analysis_map = {
            "Predictive Insights": "equipment_status"
        }
        
        target_analysis = analysis_map.get(analysis_type)
        if target_analysis and target_analysis in analyses:
            analysis = analyses[target_analysis]
            if 'analysis' in analysis:
                st.markdown(analysis['analysis'])
            else:
                st.error(f"Cached analysis failed: {analysis.get('error', 'Unknown error')}")
        else:
            st.warning(f"No cached data available for {analysis_type}. Please use live analysis.")


def display_ai_insights_tab():
    """Display the AI Insights tab in the production meeting using cached results and live agents"""
    st.header("🤖 AI Insights & Analysis")
    
    # Check for chat mode switch
    if hasattr(st.session_state, 'switch_to_chat'):
        question = st.session_state.switch_to_chat
        delattr(st.session_state, 'switch_to_chat')
        
        # Import and run chat interface with the question
        try:
            from app_factory.mes_chat.chat_interface import run_mes_chat
            st.info(f"Switching to MES Chat for deeper analysis: '{question}'")
            
            # Initialize chat with the question
            if "messages" not in st.session_state:
                st.session_state.messages = [
                    {"role": "assistant", "content": "Welcome to MES Insight Chat! I see you have a follow-up question from the daily analysis."}
                ]
            
            st.session_state.messages.append({"role": "user", "content": question})
            st.session_state["process_query"] = question
            
            # Run the chat interface
            run_mes_chat()
            return
            
        except ImportError as e:
            st.error(f"Could not load MES Chat interface: {e}")
    
    col1, col2 = st.columns([3, 1])
    
    with col2:
        # Cache status and settings sidebar
        st.subheader("📊 Analysis Status")
        
        # Display cache status
        cache_status = cache_manager.get_cache_status()
        
        if cache_status['is_fresh']:
            st.success("✅ Fresh Daily Analysis Available")
            latest = cache_status['latest_analysis']
            if latest:
                st.info(f"Generated: {latest['date']}")
        else:
            st.warning("⚠️ No Fresh Analysis Available")
            st.info("Using live agent analysis (slower)")
        
        # Analysis mode selector
        use_cached = st.radio(
            "Analysis Mode",
            options=["Cached (Fast)", "Live Agent (Comprehensive)"],
            index=0 if cache_status['is_fresh'] else 1,
            help="Cached analysis is pre-generated daily. Live analysis provides real-time insights."
        )
        
        # Analysis type selector
        analysis_type = st.radio(
            "Analysis Type",
            options=[
                "Quick Summary", 
                "Predictive Insights"
            ],
            index=0,
        )
        
        # Reset auto-load state when switching analysis types
        if "previous_analysis_type" not in st.session_state:
            st.session_state.previous_analysis_type = analysis_type
        elif st.session_state.previous_analysis_type != analysis_type:
            st.session_state.auto_loaded_summary = False
            st.session_state.previous_analysis_type = analysis_type
        
        # Settings for live analysis
        if use_cached == "Live Agent (Comprehensive)":
            st.divider()
            st.subheader("Live Agent Settings")
            
            # Display agent status
            if agent_manager.is_ready():
                st.success("✅ Production Meeting Agents Ready")
                agent_status = agent_manager.get_agent_status()
                st.info(f"Model: {agent_status['config']['model']}")
            else:
                st.warning("⚠️ Agents Initializing...")
                if st.button("Initialize Agents"):
                    try:
                        asyncio.run(agent_manager.initialize())
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to initialize agents: {e}")
            
            # Analysis depth control
            analysis_depth = st.selectbox(
                "Analysis Depth",
                options=["Standard", "Comprehensive"],
                index=0,
                help="Standard for quick insights, Comprehensive for detailed analysis"
            )
            
            # Meeting focus control
            meeting_focus = st.selectbox(
                "Meeting Focus",
                options=["Daily", "Weekly", "Monthly"],
                index=0,
                help="Adjust insights based on meeting timeframe"
            )
        
        # Initialize auto-load tracking
        if "auto_loaded_summary" not in st.session_state:
            st.session_state.auto_loaded_summary = False
        
        # Dynamic button text based on state
        if (use_cached == "Cached (Fast)" and 
            analysis_type == "Quick Summary" and 
            cache_status['is_fresh'] and 
            st.session_state.auto_loaded_summary):
            button_text = "Refresh Cached Analysis"
        elif use_cached == "Cached (Fast)":
            button_text = "Load Cached Analysis"
        else:
            button_text = "Generate Live Analysis"
        
        generate_button = st.button(button_text, use_container_width=True)
        
        # MES Chat integration
        st.divider()
        st.subheader("🔍 Deep Dive Analysis")
        st.markdown("For follow-up questions and deeper analysis:")
        
        if st.button("Open MES Chat", use_container_width=True):
            # Switch to chat mode
            st.session_state.switch_to_chat = "I'd like to dive deeper into the production analysis"
            st.rerun()
        
        # Cache management
        st.divider()
        with st.expander("🗂️ Cache Management"):
            st.write(f"Cache size: {cache_status['cache_size_mb']} MB")
            st.write(f"Available analyses: {cache_status['available_analyses']}")
            
            if st.button("Refresh Cache Status"):
                st.rerun()
        
        # Set agent context for live analysis
        if use_cached == "Live Agent (Comprehensive)" and generate_button:
            agent_manager.set_meeting_context(
                meeting_type=meeting_focus.lower(),
                focus_areas=['production', 'quality', 'equipment', 'inventory']
            )
    
    with col1:
        # Handle analysis generation
        if generate_button:
            if use_cached == "Cached (Fast)":
                # Load and display cached analysis
                cached_analysis = cache_manager.get_latest_analysis(max_age_hours=24)
                
                if cached_analysis:
                    # Show refresh info if this was a refresh action
                    if (analysis_type == "Quick Summary" and 
                        st.session_state.auto_loaded_summary):
                        latest = cache_status['latest_analysis']
                        st.info(f"🔄 Refreshed Quick Summary from cache (Generated: {latest['date']})")
                    
                    display_cached_analysis(cached_analysis, analysis_type)
                    
                    # Mark as loaded for Quick Summary
                    if analysis_type == "Quick Summary":
                        st.session_state.auto_loaded_summary = True
                else:
                    st.error("No cached analysis available. Please use Live Agent analysis or run the daily scheduler.")
                    st.info("To generate daily cache, run: `uv run python scripts/run_daily_analysis.py` or `make run-analysis`")
            
            else:
                # Use live agent analysis (original functionality)
                # Initialize various analysis session states
                for key in ["summary_insights", "predictive_insights"]:
                    if key not in st.session_state:
                        st.session_state[key] = False
                
                # Determine which analysis to display
                if analysis_type == "Quick Summary":
                    st.session_state.current_analysis = "summary"
                elif analysis_type == "Predictive Insights":
                    st.session_state.current_analysis = "predictive"
        
        # Display the appropriate analysis based on state (for live analysis)
        if hasattr(st.session_state, 'current_analysis') and use_cached == "Live Agent (Comprehensive)":
            if st.session_state.current_analysis == "summary":
                # Use agent manager for summary generation
                summary = generate_ai_insight("summary", include_historical=(analysis_depth == "Comprehensive"))
                st.markdown(summary, unsafe_allow_html=True)
                st.session_state.summary_insights = True
            
            elif st.session_state.current_analysis == "predictive":
                if not st.session_state.predictive_insights:
                    with st.spinner("Generating predictive insights..."):
                        generate_predictive_insights()
                        st.session_state.predictive_insights = True
                else:
                    generate_predictive_insights()
        
        elif not generate_button:
            # Auto-load Quick Summary if cached data is fresh and not already loaded
            if (use_cached == "Cached (Fast)" and 
                analysis_type == "Quick Summary" and 
                cache_status['is_fresh'] and 
                not st.session_state.auto_loaded_summary):
                
                # Auto-load cached Quick Summary
                cached_analysis = cache_manager.get_latest_analysis(max_age_hours=24)
                if cached_analysis:
                    # Show cache info
                    latest = cache_status['latest_analysis']
                    st.success(f"✅ Auto-loaded Quick Summary from cache (Generated: {latest['date']})")
                    
                    # Display the analysis
                    display_cached_analysis(cached_analysis, "Quick Summary")
                    st.session_state.auto_loaded_summary = True
                else:
                    st.error("No cached analysis available. Please use Live Agent analysis or run the daily scheduler.")
                    st.info("To generate daily cache, run: `uv run python scripts/run_daily_analysis.py` or `make run-analysis`")
            
            elif (use_cached == "Cached (Fast)" and 
                  analysis_type == "Predictive Insights"):
                # For Predictive Insights, show instruction to click generate
                st.info("Click 'Load Cached Analysis' to view predictive insights from the daily analysis cache.")
                
                # Show cache freshness info
                if cache_status['is_fresh']:
                    latest = cache_status['latest_analysis']
                    st.info(f"Cache available from: {latest['date']}")
                else:
                    st.warning("No fresh cache available - consider using Live Agent analysis.")
            
            elif use_cached == "Live Agent (Comprehensive)":
                # For live analysis, show instruction
                st.info("Click 'Generate Live Analysis' to create real-time insights using production meeting agents.")
                
                if not agent_manager.is_ready():
                    st.warning("⚠️ Agents are still initializing. Please wait or try refreshing.")
            
            else:
                # Fallback state
                st.info("Select an analysis mode and type to get started.")
                
                # Show helpful tips for cache setup if no cache available
                if not cache_status['is_fresh']:
                    st.info("💡 **Tip**: Run the daily analysis scheduler to enable fast cached insights!")
                    st.code("uv run python scripts/run_daily_analysis.py")
                    st.info("Or use the shortcut: `make run-analysis`")



def provide_contextual_tab_insights(tab_name, dashboard_data=None):
    """
    Provide contextual insights for specific dashboard tabs using production meeting agents
    
    Args:
        tab_name (str): Name of the dashboard tab (production, quality, equipment, inventory, etc.)
        dashboard_data (dict, optional): Current dashboard data for context
        
    Returns:
        str: Contextual insights for the tab
    """
    # Initialize agent manager if not ready
    if not agent_manager.is_ready():
        try:
            # Run initialization
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(agent_manager.initialize())
            else:
                asyncio.run(agent_manager.initialize())
        except Exception as e:
            logger.error(f"Failed to initialize agent manager for tab insights: {e}")
            return f"**Agent Initialization Error**\n\nUnable to initialize production meeting agents for {tab_name} insights."
    
    try:
        with st.spinner(f"Generating {tab_name} insights..."):
            start_time = time.time()
            
            # Process contextual insights using agent manager
            try:
                # Try async processing
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    response = asyncio.run_coroutine_threadsafe(
                        agent_manager.get_contextual_insights(dashboard_data or {}, tab_name), 
                        loop
                    ).result(timeout=30)
                else:
                    response = asyncio.run(agent_manager.get_contextual_insights(dashboard_data or {}, tab_name))
            except (RuntimeError, asyncio.TimeoutError):
                # Fallback for synchronous processing
                logging.warning("Async tab insights processing failed, using fallback")
                response = f"Analyzing {tab_name} data for contextual insights..."
            
            elapsed_time = time.time() - start_time
            
            # Add attribution
            if isinstance(response, str):
                response += f"\n\n<small><i>Generated by Production Meeting Agent for {tab_name.title()} in {elapsed_time:.1f}s</i></small>"
            
            return response
            
    except Exception as e:
        error_msg = str(e)
        logging.error(f"Error generating tab insights for {tab_name}: {error_msg}")
        
        return f"""
        **Tab Insights Error**
        
        Unable to generate insights for the {tab_name} tab:
        
        ```
        {error_msg}
        ```
        
        The tab data is still available, but AI-powered insights are temporarily unavailable.
        """


if __name__ == "__main__":
    # Test directly
    st.set_page_config(page_title="AI Insights Test", layout="wide")
    st.title("AI Insights Test")
    display_ai_insights_tab()