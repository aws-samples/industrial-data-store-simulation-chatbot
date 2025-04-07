"""
Weekly report dashboard functionality
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

from shared.database import DatabaseManager
from production_meeting.utils.interactive_explanations import metric_with_explanation

# Initialize database manager
db_manager = DatabaseManager()

def weekly_overview_dashboard():
    """Display weekly overview dashboard"""
    st.header("📅 Weekly Performance Overview")
    
    # Date range selector
    col1, col2 = st.columns(2)
    with col1:
        end_date = st.date_input(
            "End Date", 
            value=datetime.now().date(), 
            key="weekly_end_date"
        )
    with col2:
        # Calculate start date (7 days before end date)
        start_date = end_date - timedelta(days=6)
        st.write(f"Date Range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    
    # Convert to strings for SQL
    end_date_str = end_date.strftime('%Y-%m-%d')
    start_date_str = start_date.strftime('%Y-%m-%d')
    
    # Weekly production data
    weekly_production_query = f"""
    SELECT 
        date(wo.ActualEndTime) as ProductionDate,
        COUNT(wo.OrderID) as CompletedOrders,
        SUM(wo.Quantity) as PlannedQuantity,
        SUM(wo.ActualProduction) as ActualProduction,
        SUM(wo.Scrap) as ScrapQuantity,
        ROUND(SUM(wo.ActualProduction) * 100.0 / SUM(wo.Quantity), 2) as CompletionPercentage
    FROM 
        WorkOrders wo
    WHERE 
        wo.Status = 'completed'
        AND wo.ActualEndTime BETWEEN '{start_date_str}' AND '{end_date_str} 23:59:59'
    GROUP BY 
        date(wo.ActualEndTime)
    ORDER BY 
        ProductionDate
    """
    
    result = db_manager.execute_query(weekly_production_query)
    if result["success"] and result["row_count"] > 0:
        weekly_production = pd.DataFrame(result["rows"])
        
        # Production trend chart
        st.subheader("Daily Production Trend")
        
        fig = px.line(
            weekly_production,
            x='ProductionDate',
            y=['PlannedQuantity', 'ActualProduction'],
            title='Daily Production (Planned vs Actual)',
            labels={
                'value': 'Units',
                'variable': 'Metric',
                'ProductionDate': 'Date'
            },
            markers=True
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Weekly OEE data
        weekly_oee_query = f"""
        SELECT 
            date(m.Date) as MeasurementDate,
            AVG(m.Availability) * 100 as AvgAvailability,
            AVG(m.Performance) * 100 as AvgPerformance,
            AVG(m.Quality) * 100 as AvgQuality,
            AVG(m.OEE) * 100 as AvgOEE
        FROM 
            OEEMetrics m
        WHERE 
            m.Date BETWEEN '{start_date_str}' AND '{end_date_str} 23:59:59'
        GROUP BY 
            date(m.Date)
        ORDER BY 
            MeasurementDate
        """
        
        result = db_manager.execute_query(weekly_oee_query)
        if result["success"] and result["row_count"] > 0:
            weekly_oee = pd.DataFrame(result["rows"])
            
            # OEE trend chart
            st.subheader("Daily OEE Metrics")
            
            fig = px.line(
                weekly_oee,
                x='MeasurementDate',
                y=['AvgAvailability', 'AvgPerformance', 'AvgQuality', 'AvgOEE'],
                title='Daily OEE Components',
                labels={
                    'value': 'Percentage (%)',
                    'variable': 'Metric',
                    'MeasurementDate': 'Date'
                },
                markers=True
            )
            
            # Add target line at 85%
            fig.add_shape(
                type="line",
                x0=weekly_oee['MeasurementDate'].min(),
                y0=85,
                x1=weekly_oee['MeasurementDate'].max(),
                y1=85,
                line=dict(color="red", width=2, dash="dash"),
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No OEE data available for the selected period")
        
        # Weekly quality data
        weekly_quality_query = f"""
        SELECT 
            date(qc.Date) as InspectionDate,
            COUNT(qc.CheckID) as InspectionCount,
            ROUND(AVG(qc.DefectRate) * 100, 2) as AvgDefectRate,
            ROUND(AVG(qc.YieldRate) * 100, 2) as AvgYieldRate,
            SUM(CASE WHEN qc.Result = 'pass' THEN 1 ELSE 0 END) as PassCount,
            SUM(CASE WHEN qc.Result = 'fail' THEN 1 ELSE 0 END) as FailCount
        FROM 
            QualityControl qc
        WHERE 
            qc.Date BETWEEN '{start_date_str}' AND '{end_date_str} 23:59:59'
        GROUP BY 
            date(qc.Date)
        ORDER BY 
            InspectionDate
        """
        
        result = db_manager.execute_query(weekly_quality_query)
        if result["success"] and result["row_count"] > 0:
            weekly_quality = pd.DataFrame(result["rows"])
            
            # Quality trend chart
            st.subheader("Daily Quality Metrics")
            
            fig = px.line(
                weekly_quality,
                x='InspectionDate',
                y=['AvgDefectRate', 'AvgYieldRate'],
                title='Daily Quality Metrics',
                labels={
                    'value': 'Percentage (%)',
                    'variable': 'Metric',
                    'InspectionDate': 'Date'
                },
                markers=True
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No quality data available for the selected period")
        
        # Weekly summary
        st.subheader("Weekly Performance Summary")
        
        # Calculate weekly totals
        total_planned = weekly_production['PlannedQuantity'].sum()
        total_actual = weekly_production['ActualProduction'].sum()
        total_scrap = weekly_production['ScrapQuantity'].sum()
        avg_completion = weekly_production['CompletionPercentage'].mean()
        
        # Create summary metrics
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Planned", f"{int(total_planned):,}")
        col2.metric("Total Produced", f"{int(total_actual):,}")
        col3.metric("Total Scrap", f"{int(total_scrap):,}")
        col4.metric("Avg Completion", f"{avg_completion:.1f}%")
        
        # Calculate OEE summary if available
        if 'weekly_oee' in locals():
            avg_oee = weekly_oee['AvgOEE'].mean()
            st.metric("Average OEE", f"{avg_oee:.1f}%")
    else:
        st.info("No production data available for the selected period")
