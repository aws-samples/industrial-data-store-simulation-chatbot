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

from app_factory.shared.database import DatabaseManager
from app_factory.production_meeting_agents.agent_manager import ProductionMeetingAgentManager
from app_factory.production_meeting_agents.config import default_config

# Configure logging for AI insights
logger = logging.getLogger(__name__)

# Initialize database manager and agent manager
db_manager = DatabaseManager()
agent_manager = ProductionMeetingAgentManager(default_config)


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
        consumption_query = """
        SELECT 
            i.ItemID,
            i.Name as ItemName,
            AVG(mc.ActualQuantity) as AvgDailyConsumption,
            COUNT(DISTINCT wo.OrderID) / COUNT(DISTINCT date(mc.ConsumptionDate)) as OrdersPerDay
        FROM 
            MaterialConsumption mc
        JOIN 
            Inventory i ON mc.ItemID = i.ItemID
        JOIN 
            WorkOrders wo ON mc.OrderID = wo.OrderID
        WHERE 
            mc.ConsumptionDate >= date('now', '-30 day')
        GROUP BY 
            i.ItemID, i.Name
        """
        
        consumption_result = db_manager.execute_query(consumption_query)
        
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
            AND wo.PlannedStartTime <= date('now', '+7 day')
        GROUP BY 
            wc.Name, wc.Capacity
        ORDER BY 
            EstimatedHours DESC
        """
        
        capacity_result = db_manager.execute_query(capacity_query)
        
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
        maintenance_query = """
        SELECT 
            m.Name as MachineName,
            m.Type as MachineType,
            wc.Name as WorkCenterName,
            m.NextMaintenanceDate,
            julianday(m.NextMaintenanceDate) - julianday('now') as DaysUntilMaintenance
        FROM 
            Machines m
        JOIN 
            WorkCenters wc ON m.WorkCenterID = wc.WorkCenterID
        WHERE 
            julianday(m.NextMaintenanceDate) - julianday('now') BETWEEN 0 AND 7
        ORDER BY 
            DaysUntilMaintenance ASC
        """
        
        maintenance_result = db_manager.execute_query(maintenance_query)
        
        if maintenance_result["success"] and maintenance_result["row_count"] > 0:
            st.write("### Upcoming Machine Maintenance")
            
            maintenance_df = pd.DataFrame(maintenance_result["rows"])
            
            # Get production schedule for impacted machines
            for i, row in maintenance_df.iterrows():
                # Query for work orders that might be impacted
                impact_query = f"""
                SELECT 
                    COUNT(wo.OrderID) as AffectedOrders,
                    SUM(wo.Quantity) as AffectedQuantity
                FROM 
                    WorkOrders wo
                WHERE 
                    wo.MachineID = (SELECT MachineID FROM Machines WHERE Name = '{row['MachineName']}')
                    AND wo.Status = 'scheduled'
                    AND julianday(wo.PlannedStartTime) <= julianday('{row['NextMaintenanceDate']}')
                    AND julianday(wo.PlannedEndTime) >= julianday('{row['NextMaintenanceDate']}')
                """
                
                impact_result = db_manager.execute_query(impact_query)
                
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

def generate_decision_intelligence():
    """Generate focused action items based on current data"""
    logger.info("Generating decision intelligence insights")
    st.header("🎯 Critical Actions Needed")
    
    # Get inventory items below reorder point
    inventory_query = """
    SELECT 
        i.Name as ItemName,
        i.Category,
        i.Quantity as CurrentQuantity,
        i.ReorderLevel,
        (i.ReorderLevel - i.Quantity) as ShortageAmount,
        i.LeadTime as LeadTimeInDays
    FROM 
        Inventory i
    WHERE 
        i.Quantity < i.ReorderLevel
    ORDER BY 
        ShortageAmount DESC
    LIMIT 5
    """
    
    result = db_manager.execute_query(inventory_query)
    
    if result["success"] and result["row_count"] > 0:
        st.subheader("Inventory Actions")
        inventory_df = pd.DataFrame(result["rows"])
        
        for i, row in inventory_df.iterrows():
            st.info(f"**Replenish {row['ItemName']}**: {row['ShortageAmount']} units below reorder level with {row['LeadTimeInDays']} day lead time")
            
    # Get top downtime reasons to address
    downtime_query = """
    SELECT 
        d.Reason,
        COUNT(d.DowntimeID) as EventCount,
        SUM(d.Duration) as TotalMinutes,
        m.Type as MachineType
    FROM 
        Downtimes d
    JOIN 
        Machines m ON d.MachineID = m.MachineID
    WHERE 
        d.StartTime >= date('now', '-7 day')
    GROUP BY 
        d.Reason, m.Type
    ORDER BY 
        TotalMinutes DESC
    LIMIT 3
    """
    
    result = db_manager.execute_query(downtime_query)
    
    if result["success"] and result["row_count"] > 0:
        st.subheader("Downtime Actions")
        downtime_df = pd.DataFrame(result["rows"])
        
        for i, row in downtime_df.iterrows():
            st.info(f"**Address {row['Reason']} in {row['MachineType']}**: {row['EventCount']} events totaling {row['TotalMinutes']} minutes")

def generate_narrative_summary():
    """Generate a narrative summary of production data"""
    logger.info("Generating narrative summary of production data")
    st.header("📖 Production Story")
    
    # Get production data from the last 7 days
    production_query = """
    SELECT 
        date(wo.ActualEndTime) as ProductionDate,
        SUM(wo.Quantity) as PlannedQuantity,
        SUM(wo.ActualProduction) as ActualProduction,
        SUM(wo.Scrap) as ScrapQuantity,
        ROUND(SUM(wo.ActualProduction) * 100.0 / SUM(wo.Quantity), 2) as CompletionPercentage
    FROM 
        WorkOrders wo
    WHERE 
        wo.Status = 'completed'
        AND wo.ActualEndTime >= date('now', '-7 day')
    GROUP BY 
        date(wo.ActualEndTime)
    ORDER BY 
        ProductionDate
    """
    
    result = db_manager.execute_query(production_query)
    
    if result["success"] and result["row_count"] > 0:
        prod_df = pd.DataFrame(result["rows"])
        
        # Get yesterday's production
        if len(prod_df) >= 2:
            yesterday = prod_df.iloc[-2]
            today = prod_df.iloc[-1]
            
            # Calculate performance changes
            completion_change = today['CompletionPercentage'] - yesterday['CompletionPercentage']
            output_change = today['ActualProduction'] - yesterday['ActualProduction']
            
            # Get production by product category for yesterday
            category_query = """
            SELECT 
                p.Category as ProductCategory,
                SUM(wo.ActualProduction) as TotalProduction,
                ROUND(SUM(wo.ActualProduction) * 100.0 / SUM(wo.Quantity), 2) as CompletionRate
            FROM 
                WorkOrders wo
            JOIN 
                Products p ON wo.ProductID = p.ProductID
            WHERE 
                wo.Status = 'completed'
                AND date(wo.ActualEndTime) = date('now', '-1 day')
            GROUP BY 
                p.Category
            ORDER BY 
                TotalProduction DESC
            """
            
            category_result = db_manager.execute_query(category_query)
            
            # Get quality metrics for yesterday
            quality_query = """
            SELECT 
                ROUND(AVG(qc.DefectRate) * 100, 2) as AvgDefectRate,
                ROUND(AVG(qc.YieldRate) * 100, 2) as AvgYieldRate,
                COUNT(qc.CheckID) as InspectionCount,
                SUM(CASE WHEN qc.Result = 'pass' THEN 1 ELSE 0 END) as PassCount,
                SUM(CASE WHEN qc.Result = 'fail' THEN 1 ELSE 0 END) as FailCount
            FROM 
                QualityControl qc
            WHERE 
                date(qc.Date) = date('now', '-1 day')
            """
            
            quality_result = db_manager.execute_query(quality_query)
            
            # Get equipment performance for yesterday
            equipment_query = """
            SELECT 
                ROUND(AVG(oee.OEE) * 100, 2) as AvgOEE,
                ROUND(AVG(oee.Availability) * 100, 2) as AvgAvailability,
                ROUND(AVG(oee.Performance) * 100, 2) as AvgPerformance,
                ROUND(AVG(oee.Quality) * 100, 2) as AvgQuality
            FROM 
                OEEMetrics oee
            WHERE 
                date(oee.Date) = date('now', '-1 day')
            """
            
            equipment_result = db_manager.execute_query(equipment_query)
            
            # Generate executive summary
            st.subheader("Executive Summary")
            
            summary_parts = []
            
            # Production summary
            summary_parts.append(f"Production yesterday achieved {today['CompletionPercentage']:.1f}% of target")
            
            # Quality summary if available
            if quality_result["success"] and quality_result["row_count"] > 0:
                quality_data = quality_result["rows"][0]
                summary_parts.append(f"with quality yield at {quality_data['AvgYieldRate']:.1f}%")
            
            # Production change
            if completion_change > 0:
                summary_parts.append(f"Improvement of {completion_change:.1f}% from previous day")
            elif completion_change < 0:
                summary_parts.append(f"Decline of {abs(completion_change):.1f}% from previous day")
                
            # Equipment summary if available
            if equipment_result["success"] and equipment_result["row_count"] > 0:
                equipment_data = equipment_result["rows"][0]
                summary_parts.append(f"OEE was {equipment_data['AvgOEE']:.1f}%")
            
            # Create the full summary
            summary = ". ".join(summary_parts) + "."
            
            st.info(summary)
            
            # Add tabs for different narrative views
            tab1, tab2, tab3 = st.tabs(["Key Trends", "What's Changed", "Focus Areas"])
            
            with tab1:
                st.write("**Key Production Trends**")
                
                # Generate trends based on last 7 days of data
                avg_completion = prod_df['CompletionPercentage'].mean()
                trend_direction = "↗️ Improving" if prod_df['CompletionPercentage'].iloc[-1] > avg_completion else "↘️ Declining"
                
                st.write(f"**Production Completion**: {trend_direction} (Last 7 days)")
                st.write(f"  7-day average: {avg_completion:.1f}%, Yesterday: {today['CompletionPercentage']:.1f}%")
                
                # Quality trend if available
                if quality_result["success"] and quality_result["row_count"] > 0:
                    quality_data = quality_result["rows"][0]
                    
                    # Get historical quality data for trend
                    hist_quality_query = """
                    SELECT 
                        date(qc.Date) as InspectionDate,
                        ROUND(AVG(qc.YieldRate) * 100, 2) as AvgYieldRate
                    FROM 
                        QualityControl qc
                    WHERE 
                        qc.Date >= date('now', '-7 day')
                    GROUP BY 
                        date(qc.Date)
                    ORDER BY 
                        InspectionDate
                    """
                    
                    hist_quality_result = db_manager.execute_query(hist_quality_query)
                    
                    if hist_quality_result["success"] and hist_quality_result["row_count"] > 0:
                        hist_quality_df = pd.DataFrame(hist_quality_result["rows"])
                        
                        avg_yield = hist_quality_df['AvgYieldRate'].mean()
                        yield_trend = "↗️ Improving" if hist_quality_df['AvgYieldRate'].iloc[-1] > avg_yield else "↘️ Declining"
                        
                        st.write(f"**Quality Yield**: {yield_trend} (Last 7 days)")
                        st.write(f"  7-day average: {avg_yield:.1f}%, Yesterday: {quality_data['AvgYieldRate']:.1f}%")
                
                # Equipment trend if available
                if equipment_result["success"] and equipment_result["row_count"] > 0:
                    equipment_data = equipment_result["rows"][0]
                    
                    # Get historical OEE data for trend
                    hist_oee_query = """
                    SELECT 
                        date(oee.Date) as MeasurementDate,
                        ROUND(AVG(oee.OEE) * 100, 2) as AvgOEE
                    FROM 
                        OEEMetrics oee
                    WHERE 
                        oee.Date >= date('now', '-7 day')
                    GROUP BY 
                        date(oee.Date)
                    ORDER BY 
                        MeasurementDate
                    """
                    
                    hist_oee_result = db_manager.execute_query(hist_oee_query)
                    
                    if hist_oee_result["success"] and hist_oee_result["row_count"] > 0:
                        hist_oee_df = pd.DataFrame(hist_oee_result["rows"])
                        
                        avg_oee = hist_oee_df['AvgOEE'].mean()
                        oee_trend = "↗️ Improving" if hist_oee_df['AvgOEE'].iloc[-1] > avg_oee else "↘️ Declining"
                        
                        st.write(f"**OEE**: {oee_trend} (Last 7 days)")
                        st.write(f"  7-day average: {avg_oee:.1f}%, Yesterday: {equipment_data['AvgOEE']:.1f}%")
            
            with tab2:
                st.write("**What's Changed Since Yesterday**")
                
                # Create columns for positive and negative changes
                pos_col, neg_col = st.columns(2)
                
                # Get notable changes in production, quality, equipment, etc.
                changes = {
                    "improvements": [],
                    "concerns": []
                }
                
                # Production changes
                if completion_change >= 2:  # At least 2% improvement
                    changes["improvements"].append(f"Production completion rate **+{completion_change:.1f}%**")
                elif completion_change <= -2:  # At least 2% decline
                    changes["concerns"].append(f"Production completion rate **{completion_change:.1f}%**")
                
                # Get significant changes in quality metrics
                if quality_result["success"] and quality_result["row_count"] > 0:
                    quality_data = quality_result["rows"][0]
                    
                    # Get previous day's quality data
                    prev_quality_query = """
                    SELECT 
                        ROUND(AVG(qc.DefectRate) * 100, 2) as AvgDefectRate,
                        ROUND(AVG(qc.YieldRate) * 100, 2) as AvgYieldRate
                    FROM 
                        QualityControl qc
                    WHERE 
                        date(qc.Date) = date('now', '-2 day')
                    """
                    
                    prev_quality_result = db_manager.execute_query(prev_quality_query)
                    
                    if prev_quality_result["success"] and prev_quality_result["row_count"] > 0:
                        prev_quality_data = prev_quality_result["rows"][0]
                        
                        # Calculate changes
                        yield_change = quality_data['AvgYieldRate'] - prev_quality_data['AvgYieldRate']
                        defect_change = quality_data['AvgDefectRate'] - prev_quality_data['AvgDefectRate']
                        
                        if yield_change >= 1:  # At least 1% improvement in yield
                            changes["improvements"].append(f"Quality yield **+{yield_change:.1f}%**")
                        elif yield_change <= -1:  # At least 1% decline in yield
                            changes["concerns"].append(f"Quality yield **{yield_change:.1f}%**")
                        
                        if defect_change <= -1:  # At least 1% reduction in defects
                            changes["improvements"].append(f"Defect rate **{defect_change:.1f}%**")
                        elif defect_change >= 1:  # At least 1% increase in defects
                            changes["concerns"].append(f"Defect rate **+{defect_change:.1f}%**")
                
                # Get significant changes in equipment performance
                if equipment_result["success"] and equipment_result["row_count"] > 0:
                    equipment_data = equipment_result["rows"][0]
                    
                    # Get previous day's equipment data
                    prev_equipment_query = """
                    SELECT 
                        ROUND(AVG(oee.OEE) * 100, 2) as AvgOEE,
                        ROUND(AVG(oee.Availability) * 100, 2) as AvgAvailability
                    FROM 
                        OEEMetrics oee
                    WHERE 
                        date(oee.Date) = date('now', '-2 day')
                    """
                    
                    prev_equipment_result = db_manager.execute_query(prev_equipment_query)
                    
                    if prev_equipment_result["success"] and prev_equipment_result["row_count"] > 0:
                        prev_equipment_data = prev_equipment_result["rows"][0]
                        
                        # Calculate changes
                        oee_change = equipment_data['AvgOEE'] - prev_equipment_data['AvgOEE']
                        availability_change = equipment_data['AvgAvailability'] - prev_equipment_data['AvgAvailability']
                        
                        if oee_change >= 2:  # At least 2% improvement in OEE
                            changes["improvements"].append(f"OEE **+{oee_change:.1f}%**")
                        elif oee_change <= -2:  # At least 2% decline in OEE
                            changes["concerns"].append(f"OEE **{oee_change:.1f}%**")
                        
                        if availability_change >= 2:  # At least 2% improvement in availability
                            changes["improvements"].append(f"Machine availability **+{availability_change:.1f}%**")
                        elif availability_change <= -2:  # At least 2% decline in availability
                            changes["concerns"].append(f"Machine availability **{availability_change:.1f}%**")
                
                # Check for inventory alerts
                inventory_query = """
                SELECT 
                    COUNT(*) as AlertCount
                FROM 
                    Inventory
                WHERE 
                    Quantity < ReorderLevel
                """
                
                inventory_result = db_manager.execute_query(inventory_query)
                
                if inventory_result["success"] and inventory_result["row_count"] > 0:
                    alert_count = inventory_result["rows"][0]['AlertCount']
                    
                    if alert_count > 0:
                        # Get specific inventory items that are low
                        low_inventory_query = """
                        SELECT 
                            i.Name as ItemName,
                            i.Quantity as CurrentQuantity,
                            i.ReorderLevel,
                            (i.ReorderLevel - i.Quantity) as ShortageAmount
                        FROM 
                            Inventory i
                        WHERE 
                            i.Quantity < i.ReorderLevel
                        ORDER BY 
                            ShortageAmount DESC
                        LIMIT 3
                        """
                        
                        low_inventory_result = db_manager.execute_query(low_inventory_query)
                        
                        if low_inventory_result["success"] and low_inventory_result["row_count"] > 0:
                            low_items = pd.DataFrame(low_inventory_result["rows"])
                            item_names = low_items['ItemName'].tolist()
                            item_text = ", ".join(item_names)
                            changes["concerns"].append(f"**{alert_count} materials below reorder point**: {item_text}")
                        else:
                            changes["concerns"].append(f"**{alert_count} materials** below reorder point")
                
                # Display changes
                with pos_col:
                    st.write("**Improvements ✅**")
                    if changes["improvements"]:
                        for improvement in changes["improvements"]:
                            st.write(f"- {improvement}")
                    else:
                        st.write("- No significant improvements detected")
                
                with neg_col:
                    st.write("**Concerns ⚠️**")
                    if changes["concerns"]:
                        for concern in changes["concerns"]:
                            st.write(f"- {concern}")
                    else:
                        st.write("- No significant concerns detected")
            
            with tab3:
                st.write("**Focus Areas for Today**")
                
                # Identify focus areas based on production data, quality issues, etc.
                focus_areas = []
                
                # Check for completion rate issues
                if today['CompletionPercentage'] < 90:
                    focus_areas.append({
                        "area": "Production Completion",
                        "reason": f"Current completion rate ({today['CompletionPercentage']:.1f}%) below target (90%)"
                    })
                
                # Check for quality issues
                if quality_result["success"] and quality_result["row_count"] > 0:
                    quality_data = quality_result["rows"][0]
                    
                    if quality_data['AvgDefectRate'] > 5:
                        focus_areas.append({
                            "area": "Quality",
                            "reason": f"Defect rate ({quality_data['AvgDefectRate']:.1f}%) above target (5%)"
                        })
                
                # Check for OEE issues
                if equipment_result["success"] and equipment_result["row_count"] > 0:
                    equipment_data = equipment_result["rows"][0]
                    
                    if equipment_data['AvgOEE'] < 75:
                        focus_areas.append({
                            "area": "Equipment Effectiveness",
                            "reason": f"OEE ({equipment_data['AvgOEE']:.1f}%) below target (75%)"
                        })
                
                # Check for inventory alerts
                if inventory_result["success"] and inventory_result["row_count"] > 0:
                    alert_count = inventory_result["rows"][0]['AlertCount']
                    
                    if alert_count > 0:
                        focus_areas.append({
                            "area": "Inventory Management",
                            "reason": f"{alert_count} materials below reorder point"
                        })
                
                # Get top bottleneck
                bottleneck_query = """
                SELECT 
                    wc.Name as WorkCenterName,
                    COUNT(wo.OrderID) as ActiveOrders
                FROM 
                    WorkOrders wo
                JOIN 
                    WorkCenters wc ON wo.WorkCenterID = wc.WorkCenterID
                WHERE 
                    wo.Status = 'in_progress'
                GROUP BY 
                    wc.Name
                ORDER BY 
                    ActiveOrders DESC
                LIMIT 1
                """
                
                bottleneck_result = db_manager.execute_query(bottleneck_query)
                
                if bottleneck_result["success"] and bottleneck_result["row_count"] > 0:
                    bottleneck = bottleneck_result["rows"][0]
                    
                    focus_areas.append({
                        "area": f"{bottleneck['WorkCenterName']} Work Center",
                        "reason": f"Current system bottleneck with {bottleneck['ActiveOrders']} active orders"
                    })
                
                # Display focus areas
                if focus_areas:
                    for i, area in enumerate(focus_areas):
                        st.write(f"**{i+1}. {area['area']}**")
                        st.write(f"  - *Why*: {area['reason']}")
                else:
                    st.success("No critical focus areas detected - operations are running smoothly")
    else:
        st.warning("Not enough production data available to generate narrative summary")

def add_conversational_analysis():
    """Add a natural language interface to drill into specific production issues"""
    st.header("🔍 Ask Me Anything")
    
    example_questions = [
        "What would improve our on-time delivery rate?",
        "Which products have the highest defect rates?", 
        "What inventory items need replenishment?",
        "Where are our biggest bottlenecks in production?"
    ]
    
    # Initialize session state for current question if needed
    if "current_question" not in st.session_state:
        st.session_state.current_question = ""
    
    # Display example questions as clickable buttons
    st.write("Try asking:")
    question_cols = st.columns(2)
    for i, question in enumerate(example_questions):
        if question_cols[i % 2].button(question, key=f"q_{i}"):
            st.session_state.current_question = question
    
    # Input field for custom questions
    user_question = st.text_input(
        "Ask a question about production data:", 
        value=st.session_state.current_question
    )
    
    if user_question:
        # Update session state
        st.session_state.current_question = user_question
        
        # Process the question
        with st.spinner("Analyzing data..."):
            # Generate response using AI
            response = generate_ai_insight("all", query=user_question)
            
            st.markdown(response)
            
            # Try to display relevant visualizations based on the question
            
            # For defect-related questions
            if "defect" in user_question.lower() or "quality" in user_question.lower():
                # Get defect data
                defect_query = """
                SELECT 
                    d.DefectType,
                    COUNT(d.DefectID) as DefectCount,
                    AVG(d.Severity) as AvgSeverity,
                    p.Name as ProductName,
                    p.Category as ProductCategory,
                    wc.Name as WorkCenterName
                FROM 
                    Defects d
                JOIN 
                    QualityControl qc ON d.CheckID = qc.CheckID
                JOIN 
                    WorkOrders wo ON qc.OrderID = wo.OrderID
                JOIN 
                    Products p ON wo.ProductID = p.ProductID
                JOIN 
                    WorkCenters wc ON wo.WorkCenterID = wc.WorkCenterID
                WHERE 
                    qc.Date >= date('now', '-30 day')
                GROUP BY 
                    d.DefectType, p.Name, p.Category, wc.Name
                ORDER BY 
                    DefectCount DESC
                LIMIT 15
                """
                
                result = db_manager.execute_query(defect_query)
                
                if result["success"] and result["row_count"] > 0:
                    defect_df = pd.DataFrame(result["rows"])
                    
                    # Create visualization based on available data
                    st.subheader("Related Data Visualization")
                    
                    fig = px.bar(
                        defect_df.head(10), 
                        x="DefectType", 
                        y="DefectCount",
                        color="AvgSeverity",
                        hover_data=["ProductCategory", "WorkCenterName"],
                        title="Top Defect Types by Count and Severity",
                        color_continuous_scale="Reds"
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
            
            # For OEE/equipment-related questions
            elif "oee" in user_question.lower() or "equipment" in user_question.lower() or "machine" in user_question.lower():
                # Get OEE data by shift or machine type based on the question
                if "shift" in user_question.lower():
                    # OEE by shift
                    oee_query = """
                    SELECT 
                        s.Name as ShiftName,
                        ROUND(AVG(oee.OEE) * 100, 2) as AvgOEE,
                        ROUND(AVG(oee.Availability) * 100, 2) as AvgAvailability,
                        ROUND(AVG(oee.Performance) * 100, 2) as AvgPerformance,
                        ROUND(AVG(oee.Quality) * 100, 2) as AvgQuality
                    FROM 
                        OEEMetrics oee
                    JOIN 
                        Machines m ON oee.MachineID = m.MachineID
                    JOIN 
                        WorkOrders wo ON m.MachineID = wo.MachineID
                    JOIN 
                        Employees e ON wo.EmployeeID = e.EmployeeID
                    JOIN 
                        Shifts s ON e.ShiftID = s.ShiftID
                    WHERE 
                        oee.Date >= date('now', '-30 day')
                    GROUP BY 
                        s.Name
                    ORDER BY 
                        AvgOEE DESC
                    """
                else:
                    # OEE by machine type
                    oee_query = """
                    SELECT 
                        m.Type as MachineType,
                        ROUND(AVG(oee.OEE) * 100, 2) as AvgOEE,
                        ROUND(AVG(oee.Availability) * 100, 2) as AvgAvailability,
                        ROUND(AVG(oee.Performance) * 100, 2) as AvgPerformance,
                        ROUND(AVG(oee.Quality) * 100, 2) as AvgQuality
                    FROM 
                        OEEMetrics oee
                    JOIN 
                        Machines m ON oee.MachineID = m.MachineID
                    WHERE 
                        oee.Date >= date('now', '-30 day')
                    GROUP BY 
                        m.Type
                    ORDER BY 
                        AvgOEE DESC
                    """
                
                result = db_manager.execute_query(oee_query)
                
                if result["success"] and result["row_count"] > 0:
                    oee_df = pd.DataFrame(result["rows"])
                    
                    # Create visualization based on available data
                    st.subheader("Related Data Visualization")
                    
                    # Determine the grouping column (ShiftName or MachineType)
                    group_col = "ShiftName" if "ShiftName" in oee_df.columns else "MachineType"
                    
                    # Create bar chart
                    oee_components = oee_df.melt(
                        id_vars=[group_col],
                        value_vars=["AvgAvailability", "AvgPerformance", "AvgQuality", "AvgOEE"],
                        var_name="Metric",
                        value_name="Value"
                    )
                    
                    fig = px.bar(
                        oee_components,
                        x=group_col,
                        y="Value",
                        color="Metric",
                        barmode="group",
                        title=f"OEE Components by {group_col}",
                        labels={"Value": "Percentage (%)", group_col: group_col.replace("Name", "")}
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
            
            # For inventory-related questions
            elif "inventory" in user_question.lower() or "material" in user_question.lower() or "component" in user_question.lower():
                # Get inventory data
                inventory_query = """
                SELECT 
                    i.Name as ItemName,
                    i.Category,
                    i.Quantity as CurrentQuantity,
                    i.ReorderLevel,
                    (i.Quantity - i.ReorderLevel) as Margin,
                    i.LeadTime as LeadTimeInDays,
                    s.Name as SupplierName
                FROM 
                    Inventory i
                JOIN 
                    Suppliers s ON i.SupplierID = s.SupplierID
                ORDER BY 
                    Margin ASC
                LIMIT 20
                """
                
                result = db_manager.execute_query(inventory_query)
                
                if result["success"] and result["row_count"] > 0:
                    inventory_df = pd.DataFrame(result["rows"])
                    
                    # Create visualization based on available data
                    st.subheader("Related Data Visualization")
                    
                    # Calculate inventory status
                    inventory_df["Status"] = pd.cut(
                        inventory_df["Margin"],
                        bins=[-float('inf'), -10, 0, float('inf')],
                        labels=["Critical", "Low", "Adequate"]
                    )
                    
                    # Create bar chart
                    fig = px.bar(
                        inventory_df.head(15),
                        x="ItemName",
                        y="CurrentQuantity",
                        color="Status",
                        hover_data=["ReorderLevel", "LeadTimeInDays", "SupplierName"],
                        title="Inventory Levels vs. Reorder Points",
                        labels={"CurrentQuantity": "Current Quantity", "ItemName": "Item"},
                        color_discrete_map={"Critical": "red", "Low": "orange", "Adequate": "green"}
                    )
                    
                    # Add reorder level line
                    for i, row in inventory_df.head(15).iterrows():
                        fig.add_shape(
                            type="line",
                            x0=i-0.4,
                            x1=i+0.4,
                            y0=row["ReorderLevel"],
                            y1=row["ReorderLevel"],
                            line=dict(color="black", width=2, dash="dash")
                        )
                    
                    st.plotly_chart(fig, use_container_width=True)

def display_ai_insights_tab():
    """Display the AI Insights tab in the production meeting using production meeting agents"""
    st.header("🤖 AI Insights & Analysis")
    
    col1, col2 = st.columns([3, 1])
    
    with col2:
        # Agent settings sidebar
        st.subheader("Agent Settings")
        
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
        
        # Analysis type selector
        analysis_type = st.radio(
            "Analysis Type",
            options=[
                "Quick Summary", 
                "Decision Intelligence", 
                "Predictive Insights", 
                "Narrative Analysis", 
                "Conversational Q&A"
            ],
            index=0,
        )
        
        # Generate button
        generate_button = st.button("Generate Insights", use_container_width=True)
        
        # Set agent context based on settings
        if generate_button:
            agent_manager.set_meeting_context(
                meeting_type=meeting_focus.lower(),
                focus_areas=['production', 'quality', 'equipment', 'inventory']
            )
    
    with col1:
        # Initialize various analysis session states
        for key in ["summary_insights", "decision_insights", "predictive_insights", "narrative_insights"]:
            if key not in st.session_state:
                st.session_state[key] = False
        
        # Determine which analysis to display based on selection and button click
        if generate_button:
            if analysis_type == "Quick Summary":
                st.session_state.current_analysis = "summary"
            elif analysis_type == "Decision Intelligence":
                st.session_state.current_analysis = "decision"
            elif analysis_type == "Predictive Insights":
                st.session_state.current_analysis = "predictive"
            elif analysis_type == "Narrative Analysis":
                st.session_state.current_analysis = "narrative"
            elif analysis_type == "Conversational Q&A":
                st.session_state.current_analysis = "conversational"
        
        # Display the appropriate analysis based on state
        if hasattr(st.session_state, 'current_analysis'):
            if st.session_state.current_analysis == "summary":
                # Use agent manager for summary generation
                summary = generate_ai_insight("summary", include_historical=(analysis_depth == "Comprehensive"))
                st.markdown(summary, unsafe_allow_html=True)
                st.session_state.summary_insights = True
            
            elif st.session_state.current_analysis == "decision":
                if not st.session_state.decision_insights:
                    with st.spinner("Generating decision intelligence insights..."):
                        generate_decision_intelligence()
                        st.session_state.decision_insights = True
                else:
                    generate_decision_intelligence()
            
            elif st.session_state.current_analysis == "predictive":
                if not st.session_state.predictive_insights:
                    with st.spinner("Generating predictive insights..."):
                        generate_predictive_insights()
                        st.session_state.predictive_insights = True
                else:
                    generate_predictive_insights()
            
            elif st.session_state.current_analysis == "narrative":
                if not st.session_state.narrative_insights:
                    with st.spinner("Generating narrative insights..."):
                        generate_narrative_summary()
                        st.session_state.narrative_insights = True
                else:
                    generate_narrative_summary()
            
            elif st.session_state.current_analysis == "conversational":
                add_conversational_analysis()
        else:
            st.info("Select an analysis type and click 'Generate Insights' to get started")



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