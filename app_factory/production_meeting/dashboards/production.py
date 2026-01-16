"""
Enhanced production dashboard for daily production meetings
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np

from app_factory.shared.database import DatabaseManager

# Initialize database manager
db_manager = DatabaseManager()

# Import shared color configuration
from .color_config import (
    DEFAULT_COLORS, STATUS_COLORS,
    get_performance_color, get_status_color_map, apply_theme_compatibility
)

def get_oee_color(oee_value):
    """Get color based on OEE value using Streamlit color scheme"""
    return get_performance_color(oee_value, {'excellent': 85, 'good': 70, 'fair': 50})

def create_enhanced_gauge(value, title, target=85, max_value=100):
    """Create an enhanced gauge chart - theme compatible with centered number"""
    # Calculate delta for display
    delta_value = value - target
    delta_sign = "+" if delta_value >= 0 else ""
    delta_color = "#00CC96" if delta_value >= 0 else "#EF553B"

    fig = go.Figure(go.Indicator(
        mode="gauge",  # Only gauge, we'll add number via annotation
        value=value,
        domain={'x': [0, 1], 'y': [0.2, 1]},
        title={'text': title, 'font': {'size': 14}},
        gauge={
            'axis': {'range': [0, max_value], 'tickwidth': 1, 'tickfont': {'size': 10}},
            'bar': {'color': get_oee_color(value), 'thickness': 0.25},
            'borderwidth': 1,
            'steps': [
                {'range': [0, 60], 'color': 'rgba(239, 85, 59, 0.3)'},   # Red with transparency
                {'range': [60, 85], 'color': 'rgba(255, 161, 90, 0.3)'}, # Orange with transparency
                {'range': [85, 100], 'color': 'rgba(0, 204, 150, 0.3)'} # Green with transparency
            ],
            'threshold': {
                'line': {'color': "#EF553B", 'width': 3},
                'thickness': 0.75,
                'value': target
            }
        }
    ))

    # Add centered number annotation
    fig.add_annotation(
        x=0.5,
        y=0.35,
        text=f"<b>{value:.0f}%</b>",
        showarrow=False,
        font=dict(size=36),
        xanchor='center',
        yanchor='middle'
    )

    # Add delta annotation below the number
    fig.add_annotation(
        x=0.5,
        y=0.18,
        text=f"<span style='color:{delta_color}'>{delta_sign}{delta_value:.0f}</span>",
        showarrow=False,
        font=dict(size=16, color=delta_color),
        xanchor='center',
        yanchor='middle'
    )

    fig.update_layout(
        height=300,
        margin=dict(l=30, r=30, t=60, b=40)
    )

    return apply_theme_compatibility(fig)

def create_enhanced_trend_chart(df, x_col, y_cols, title, colors=None):
    """Create an enhanced trend chart with better formatting and colors"""
    if colors is None:
        colors = DEFAULT_COLORS
    
    fig = go.Figure()
    
    for i, y_col in enumerate(y_cols):
        fig.add_trace(go.Scatter(
            x=df[x_col],
            y=df[y_col],
            name=y_col.replace('Avg', '').replace('_', ' ').title(),
            line=dict(color=colors[i % len(colors)], width=3),
            mode='lines+markers',
            marker=dict(size=6),
            hovertemplate=f'<b>{y_col}</b><br>Date: %{{x}}<br>Value: %{{y:.1f}}%<extra></extra>'
        ))
    
    fig.update_layout(
        title=dict(text=title, font=dict(size=16)),
        xaxis_title='Date',
        yaxis_title='Percentage (%)',
        hovermode='x unified',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        template="plotly",
        height=400
    )
    
    return apply_theme_compatibility(fig)

def create_enhanced_bar_chart(df, x_col, y_cols, title, colors=None, show_values=True):
    """Create an enhanced bar chart with better formatting"""
    if colors is None:
        colors = DEFAULT_COLORS
    
    if isinstance(y_cols, str):
        y_cols = [y_cols]
    
    fig = go.Figure()
    
    for i, y_col in enumerate(y_cols):
        fig.add_trace(go.Bar(
            name=y_col.replace('_', ' ').title(),
            x=df[x_col],
            y=df[y_col],
            marker_color=colors[i % len(colors)],
            text=df[y_col] if show_values else None,
            texttemplate='%{text:.0f}' if show_values else None,
            textposition='outside' if show_values else None,
            hovertemplate=f'<b>{y_col}</b><br>{x_col}: %{{x}}<br>Value: %{{y:,.0f}}<extra></extra>'
        ))
    
    fig.update_layout(
        title=dict(text=title, font=dict(size=16)),
        xaxis_title=x_col.replace('_', ' ').title(),
        yaxis_title='Value',
        barmode='group' if len(y_cols) > 1 else 'relative',
        template="plotly",
        height=400,
        legend=dict(
            orientation="h",
            yanchor="bottom", 
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    return apply_theme_compatibility(fig)

def production_summary_dashboard():
    """Display the enhanced production summary dashboard for daily production meetings"""
    
    # Create tabs for different aspects of production
    tab1, tab2, tab3, tab4 = st.tabs([
        "📈 Daily Overview", 
        "⚙️ OEE & Performance", 
        "🔍 Bottlenecks & Issues",
        "📆 Production Schedule"
    ])
    
    with tab1:
        display_daily_overview()
    
    with tab2:
        display_performance_metrics()
    
    with tab3:
        display_bottlenecks_and_issues()
    
    with tab4:
        display_production_schedule()

def display_daily_overview():
    """Display the daily production overview"""
    st.header("📈 Production Overview")
    
    # Current day vs previous day metrics
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Yesterday's Production")
        
        # Get production data for yesterday
        yesterday_data = db_manager.get_daily_production_summary(days_back=1)
        
        if not yesterday_data.empty:
            # Summary metrics
            total_planned = yesterday_data['PlannedQuantity'].sum()
            total_actual = yesterday_data['ActualProduction'].sum()
            total_scrap = yesterday_data['ScrapQuantity'].sum() 
            completion_rate = (total_actual / total_planned * 100) if total_planned > 0 else 0
            scrap_rate = (total_scrap / total_planned * 100) if total_planned > 0 else 0
            
            # Display metrics
            metrics_cols = st.columns(4)
            metrics_cols[0].metric("Planned Units", f"{int(total_planned):,}")
            metrics_cols[1].metric("Actual Units", f"{int(total_actual):,}")
            metrics_cols[2].metric("Completion Rate", f"{completion_rate:.1f}%")
            metrics_cols[3].metric("Scrap Rate", f"{scrap_rate:.1f}%")
            
            # Show production by product
            st.subheader("Production by Product")
            
            # Create enhanced production visualization
            fig = px.bar(
                yesterday_data, 
                x='ProductName', 
                y=['PlannedQuantity', 'ActualProduction', 'ScrapQuantity'],
                barmode='group',
                title='Yesterday\'s Production Performance by Product',
                labels={'value': 'Units', 'variable': 'Metric', 'ProductName': 'Product'},
                color_discrete_map={
                    'PlannedQuantity': DEFAULT_COLORS[2],  # Blue
                    'ActualProduction': DEFAULT_COLORS[3], # Green
                    'ScrapQuantity': DEFAULT_COLORS[0]     # Red
                }
            )
            
            # Enhanced formatting
            fig.update_layout(
                template="plotly",
                height=400,
                title=dict(font=dict(size=16)),
                xaxis=dict(tickangle=-45),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                ),
                hovermode='x unified'
            )
            
            # Add data labels
            fig.update_traces(
                texttemplate='%{y:,.0f}',
                textposition='outside'
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Show detailed data
            with st.expander("Detailed Production Data", expanded=False):
                st.dataframe(yesterday_data)
        else:
            st.info("No production data available for yesterday")
    
    with col2:
        st.subheader("Production Trend (Last 7 Days)")
        
        # Get production data for the last 7 days
        production_trend_query = """
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
            AND wo.ActualEndTime >= date('now', '-7 day')
        GROUP BY 
            date(wo.ActualEndTime)
        ORDER BY 
            ProductionDate
        """
        
        result = db_manager.execute_query(production_trend_query)
        
        if result["success"] and result["row_count"] > 0:
            trend_df = pd.DataFrame(result["rows"])
            
            # Convert date strings to datetime for better x-axis formatting
            trend_df['ProductionDate'] = pd.to_datetime(trend_df['ProductionDate'])
            
            # Create enhanced production trend visualization
            fig = go.Figure()
            
            # Add production quantities with Streamlit colors
            fig.add_trace(go.Bar(
                x=trend_df['ProductionDate'],
                y=trend_df['PlannedQuantity'],
                name='Planned Production',
                marker_color=DEFAULT_COLORS[2],  # Blue
                text=trend_df['PlannedQuantity'],
                texttemplate='%{text:,.0f}',
                textposition='outside',
                hovertemplate='<b>Planned</b><br>Date: %{x}<br>Quantity: %{y:,.0f}<extra></extra>'
            ))
            
            fig.add_trace(go.Bar(
                x=trend_df['ProductionDate'],
                y=trend_df['ActualProduction'],
                name='Actual Production',
                marker_color=DEFAULT_COLORS[3],  # Green
                text=trend_df['ActualProduction'],
                texttemplate='%{text:,.0f}',
                textposition='outside',
                hovertemplate='<b>Actual</b><br>Date: %{x}<br>Quantity: %{y:,.0f}<extra></extra>'
            ))
            
            # Add completion percentage line on secondary y-axis
            fig.add_trace(go.Scatter(
                x=trend_df['ProductionDate'],
                y=trend_df['CompletionPercentage'],
                name='Completion Rate',
                line=dict(color=DEFAULT_COLORS[0], width=4),  # Red
                mode='lines+markers',
                marker=dict(size=8),
                yaxis='y2',
                hovertemplate='<b>Completion Rate</b><br>Date: %{x}<br>Rate: %{y:.1f}%<extra></extra>'
            ))
            
            # Enhanced layout with secondary y-axis
            fig.update_layout(
                title=dict(text='Production Trend (Last 7 Days)', font=dict(size=16)),
                xaxis_title='Date',
                yaxis_title='Production Quantity',
                yaxis2=dict(
                    title='Completion Rate (%)',
                    anchor='x',
                    overlaying='y',
                    side='right',
                    range=[0, 110],
                    tickformat='.0f'
                ),
                barmode='group',
                template="plotly",
                height=450,
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                ),
                hovermode='x unified'
            )
            
            # Add target completion line
            fig.add_shape(
                type="line",
                x0=trend_df['ProductionDate'].min(),
                x1=trend_df['ProductionDate'].max(),
                y0=100,
                y1=100,
                line=dict(color="green", width=2, dash="dash"),
                yref='y2'
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Add weekly summary 
            weekly_avg_completion = trend_df['CompletionPercentage'].mean()
            weekly_total_quantity = trend_df['ActualProduction'].sum()
            
            metrics_cols = st.columns(2)
            metrics_cols[0].metric(
                "Weekly Avg Completion", 
                f"{weekly_avg_completion:.1f}%"
            )
            metrics_cols[1].metric(
                "Weekly Total Production", 
                f"{int(weekly_total_quantity):,} units"
            )
        else:
            st.info("No trend data available for the past 7 days")
    
    # Work orders status section
    st.subheader("Current Work Order Status")
    
    # Get current work order status
    work_order_status = db_manager.get_work_order_status()
    
    if not work_order_status.empty:
        # Layout with columns
        col1, col2 = st.columns([1, 2])
        
        with col1:
            # Create enhanced status donut chart
            fig = px.pie(
                work_order_status,
                values='OrderCount',
                names='Status',
                title='Work Order Status Distribution',
                color='Status',
                color_discrete_map=get_status_color_map(work_order_status['Status'].unique()),
                hole=0.5  # Larger hole for better readability
            )
            
            # Enhanced formatting
            fig.update_traces(
                textposition='inside',
                textinfo='percent+label',
                textfont_size=12
            )
            
            fig.update_layout(
                legend=dict(
                    orientation="v",
                    yanchor="middle",
                    y=0.5,
                    xanchor="left",
                    x=1.05
                ),
                height=350,
                margin=dict(l=20, r=100, t=60, b=20),
                title=dict(font=dict(size=14))
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Get work order details by product category
            work_order_details_query = """
            SELECT 
                p.Category as ProductCategory,
                wo.Status,
                COUNT(wo.OrderID) as OrderCount,
                SUM(wo.Quantity) as PlannedQuantity
            FROM 
                WorkOrders wo
            JOIN 
                Products p ON wo.ProductID = p.ProductID
            WHERE 
                wo.Status IN ('scheduled', 'in_progress')
            GROUP BY 
                p.Category, wo.Status
            ORDER BY 
                OrderCount DESC
            """
            
            result = db_manager.execute_query(work_order_details_query)
            
            if result["success"] and result["row_count"] > 0:
                category_df = pd.DataFrame(result["rows"])
                
                # Create grouped bar chart
                fig = px.bar(
                    category_df,
                    x='ProductCategory',
                    y='OrderCount',
                    color='Status',
                    title='Active Work Orders by Product Category',
                    color_discrete_map={
                        'scheduled': '#636EFA',
                        'in_progress': '#FFA15A'
                    },
                    barmode='group',
                    labels={'OrderCount': 'Number of Orders', 'ProductCategory': 'Product Category'}
                )
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No active work orders by product category available")
    else:
        st.info("No work order status data available")

def display_performance_metrics():
    """Display OEE and other performance metrics"""
    st.header("⚙️ OEE & Performance Metrics")
    
    # Create top layout with key metrics
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("OEE Overview (Last 24 Hours)")
        
        # Get yesterday's OEE metrics
        oee_query = """
        SELECT 
            ROUND(AVG(oee.OEE) * 100, 2) as AvgOEE,
            ROUND(AVG(oee.Availability) * 100, 2) as AvgAvailability,
            ROUND(AVG(oee.Performance) * 100, 2) as AvgPerformance,
            ROUND(AVG(oee.Quality) * 100, 2) as AvgQuality,
            SUM(oee.Downtime) as TotalDowntimeMinutes
        FROM 
            OEEMetrics oee
        WHERE 
            date(oee.Date) = date('now', '-1 day')
        """
        
        result = db_manager.execute_query(oee_query)
        
        if result["success"] and result["row_count"] > 0:
            oee_data = result["rows"][0]
            
            # Create enhanced gauge chart for OEE
            fig = create_enhanced_gauge(
                value=oee_data["AvgOEE"],
                title="Overall Equipment Effectiveness (OEE)",
                target=85,
                max_value=100
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Show OEE component metrics
            metrics_cols = st.columns(3)
            
            metrics_cols[0].metric(
                "Availability", 
                f"{oee_data['AvgAvailability']:.1f}%",
                help="Percentage of scheduled time that the operation is available to operate"
            )
            
            metrics_cols[1].metric(
                "Performance", 
                f"{oee_data['AvgPerformance']:.1f}%",
                help="Speed at which work center runs as a percentage of its designed speed"
            )
            
            metrics_cols[2].metric(
                "Quality", 
                f"{oee_data['AvgQuality']:.1f}%",
                help="Good units produced as a percentage of total units started"
            )
            
            # Show downtime metric
            downtime_hours = oee_data["TotalDowntimeMinutes"] / 60 if oee_data["TotalDowntimeMinutes"] else 0
            st.metric(
                "Total Downtime", 
                f"{downtime_hours:.1f} hours"
            )
        else:
            st.info("No OEE data available for yesterday")
    
    with col2:
        st.subheader("OEE Trend (Last 7 Days)")
        
        # Get OEE trend data
        oee_trend_query = """
        SELECT 
            date(oee.Date) as MeasurementDate,
            ROUND(AVG(oee.OEE) * 100, 2) as AvgOEE,
            ROUND(AVG(oee.Availability) * 100, 2) as AvgAvailability,
            ROUND(AVG(oee.Performance) * 100, 2) as AvgPerformance,
            ROUND(AVG(oee.Quality) * 100, 2) as AvgQuality
        FROM 
            OEEMetrics oee
        WHERE 
            oee.Date >= date('now', '-7 day')
        GROUP BY 
            date(oee.Date)
        ORDER BY 
            MeasurementDate
        """
        
        result = db_manager.execute_query(oee_trend_query)
        
        if result["success"] and result["row_count"] > 0:
            oee_trend_df = pd.DataFrame(result["rows"])
            
            # Convert date strings to datetime
            oee_trend_df['MeasurementDate'] = pd.to_datetime(oee_trend_df['MeasurementDate'])
            
            # Create enhanced trend chart for OEE components
            fig = create_enhanced_trend_chart(
                df=oee_trend_df,
                x_col='MeasurementDate',
                y_cols=['AvgOEE', 'AvgAvailability', 'AvgPerformance', 'AvgQuality'],
                title='OEE Components Trend (Last 7 Days)',
                colors=['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4']  # Streamlit colors
            )
            
            # Add target line at 85%
            fig.add_shape(
                type="line",
                x0=oee_trend_df['MeasurementDate'].min(),
                x1=oee_trend_df['MeasurementDate'].max(),
                y0=85,
                y1=85,
                line=dict(color="red", width=2, dash="dash"),
                name="Target (85%)"
            )
            
            fig.add_annotation(
                x=oee_trend_df['MeasurementDate'].iloc[-1],
                y=85,
                text="Target: 85%",
                showarrow=True,
                arrowhead=2,
                arrowcolor="red",
                font=dict(color="red")
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No OEE trend data available")
    
    # Get OEE by Machine Type
    st.subheader("OEE by Machine Type (Yesterday)")
    
    oee_by_machine_query = """
    SELECT 
        m.Type as MachineType,
        ROUND(AVG(oee.OEE) * 100, 2) as AvgOEE,
        ROUND(AVG(oee.Availability) * 100, 2) as AvgAvailability,
        ROUND(AVG(oee.Performance) * 100, 2) as AvgPerformance,
        ROUND(AVG(oee.Quality) * 100, 2) as AvgQuality,
        SUM(oee.Downtime) as TotalDowntime
    FROM 
        OEEMetrics oee
    JOIN
        Machines m ON oee.MachineID = m.MachineID
    WHERE 
        date(oee.Date) = date('now', '-1 day')
    GROUP BY 
        m.Type
    ORDER BY 
        AvgOEE DESC
    """
    
    result = db_manager.execute_query(oee_by_machine_query)
    
    if result["success"] and result["row_count"] > 0:
        machine_oee_df = pd.DataFrame(result["rows"])
        
        # Create visualization
        fig = px.bar(
            machine_oee_df,
            x='MachineType',
            y=['AvgAvailability', 'AvgPerformance', 'AvgQuality'],
            title='OEE Components by Machine Type',
            labels={
                'value': 'Percentage (%)', 
                'variable': 'Component', 
                'MachineType': 'Machine Type'
            },
            barmode='group',
            color_discrete_map={
                'AvgAvailability': '#636EFA',
                'AvgPerformance': '#FFA15A',
                'AvgQuality': '#00CC96'
            }
        )
        
        # Add OEE as a line
        fig.add_trace(go.Scatter(
            x=machine_oee_df['MachineType'],
            y=machine_oee_df['AvgOEE'],
            name='OEE',
            mode='lines+markers',
            line=dict(color='#19D3F3', width=4)
        ))
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Show machine details in expandable section
        with st.expander("Machine Performance Details", expanded=False):
            st.dataframe(machine_oee_df)
    else:
        st.info("No OEE by machine type data available")

    # Shift Performance Section
    st.subheader("Shift Performance Comparison (Yesterday)")
    
    # Get shift performance data
    shift_performance_query = """
    SELECT 
        s.Name as ShiftName,
        COUNT(wo.OrderID) as CompletedOrders,
        SUM(wo.Quantity) as PlannedQuantity,
        SUM(wo.ActualProduction) as ActualProduction,
        SUM(wo.Scrap) as ScrapQuantity,
        ROUND(SUM(wo.ActualProduction) * 100.0 / SUM(wo.Quantity), 2) as CompletionPercentage
    FROM 
        WorkOrders wo
    JOIN
        Employees e ON wo.EmployeeID = e.EmployeeID
    JOIN
        Shifts s ON e.ShiftID = s.ShiftID
    WHERE 
        date(wo.ActualEndTime) = date('now', '-1 day')
        AND wo.Status = 'completed'
    GROUP BY 
        s.Name
    ORDER BY 
        CompletedOrders DESC
    """
    
    result = db_manager.execute_query(shift_performance_query)
    
    if result["success"] and result["row_count"] > 0:
        shift_df = pd.DataFrame(result["rows"])
        
        # Create visualization
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Bar chart for production by shift
            fig = px.bar(
                shift_df,
                x='ShiftName',
                y=['PlannedQuantity', 'ActualProduction', 'ScrapQuantity'],
                title='Production by Shift',
                labels={
                    'value': 'Units', 
                    'variable': 'Metric', 
                    'ShiftName': 'Shift'
                },
                barmode='group',
                color_discrete_map={
                    'PlannedQuantity': '#636EFA',
                    'ActualProduction': '#00CC96',
                    'ScrapQuantity': '#EF553B'
                }
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Completion rate comparison
            fig = px.bar(
                shift_df,
                x='ShiftName',
                y='CompletionPercentage',
                title='Completion Rate by Shift',
                labels={
                    'CompletionPercentage': 'Completion %', 
                    'ShiftName': 'Shift'
                },
                color='CompletionPercentage',
                color_continuous_scale=['#EF553B', '#FFA15A', '#00CC96'],
                range_color=[75, 100]
            )
            
            # Add target line
            fig.add_shape(
                type="line",
                x0=-0.5,
                x1=len(shift_df) - 0.5,
                y0=90,
                y1=90,
                line=dict(width=2, dash="dash")
            )
            
            # Add target annotation
            fig.add_annotation(
                x=0,
                y=90,
                text="Target: 90%",
                showarrow=False,
                yshift=10,
                xshift=50,
            )
            
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No shift performance data available")

def display_bottlenecks_and_issues():
    """Display production bottlenecks and issues"""
    st.header("🔍 Bottlenecks & Issues")
    
    # Create columns layout
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("⚠️ Work Center Bottlenecks")
        
        # Get work center load/capacity data
        work_center_load_query = """
        SELECT 
            wc.Name as WorkCenterName,
            COUNT(wo.OrderID) as ActiveOrders,
            SUM(wo.Quantity) as TotalQuantity,
            wc.Capacity as HourlyCapacity,
            ROUND(SUM(wo.Quantity) / wc.Capacity, 2) as EstimatedHours,
            (ROUND(SUM(wo.Quantity) / wc.Capacity, 2) / 8) as EstimatedDays
        FROM 
            WorkOrders wo
        JOIN 
            WorkCenters wc ON wo.WorkCenterID = wc.WorkCenterID
        WHERE 
            wo.Status = 'in_progress'
        GROUP BY 
            wc.Name, wc.Capacity
        ORDER BY 
            EstimatedHours DESC
        LIMIT 5
        """
        
        result = db_manager.execute_query(work_center_load_query)
        
        if result["success"] and result["row_count"] > 0:
            bottlenecks_df = pd.DataFrame(result["rows"])

            # Use EstimatedDays directly as backlog metric
            bottlenecks_df['BacklogDays'] = bottlenecks_df['EstimatedDays']

            # Create a bottleneck visualization showing days of backlog
            fig = px.bar(
                bottlenecks_df,
                x='WorkCenterName',
                y='BacklogDays',
                title='Work Center Backlog (Active Orders)',
                labels={
                    'BacklogDays': 'Backlog (Days)',
                    'WorkCenterName': 'Work Center'
                },
                color='BacklogDays',
                color_continuous_scale=['#00CC96', '#FFA15A', '#EF553B'],
                range_color=[0, 10]
            )

            # Add target line at 2 days (reasonable target for in-progress work)
            fig.add_shape(
                type="line",
                x0=-0.5,
                x1=len(bottlenecks_df) - 0.5,
                y0=2,
                y1=2,
                line=dict(color="red", width=2, dash="dash")
            )
            fig.add_annotation(
                x=len(bottlenecks_df) - 0.5,
                y=2,
                text="Target: 2 days",
                showarrow=False,
                xanchor="right",
                font=dict(color="red", size=10)
            )

            st.plotly_chart(fig, use_container_width=True)

            # Show detailed data with conditional formatting
            st.write("Top Work Center Bottlenecks:")

            for i, row in bottlenecks_df.iterrows():
                backlog_days = row['BacklogDays']
                if backlog_days > 5:
                    status_color = "red"
                    status_text = "Critical Backlog"
                elif backlog_days > 3:
                    status_color = "orange"
                    status_text = "High Backlog"
                elif backlog_days > 2:
                    status_color = "blue"
                    status_text = "Moderate Backlog"
                else:
                    status_color = "green"
                    status_text = "Normal"

                st.markdown(f"""
                **{row['WorkCenterName']}**: <span style='color:{status_color}'>{status_text}</span>
                {row['ActiveOrders']} active orders, {int(row['TotalQuantity']):,} units
                Est. time to complete: {row['EstimatedHours']:.1f} hours ({row['EstimatedDays']:.1f} days)
                """, unsafe_allow_html=True)

                # Add progress bar to visualize load (scale: 0-10 days)
                st.progress(min(backlog_days / 10, 1.0))
                st.markdown("---")
        else:
            st.info("No work center bottleneck data available")
    
    with col2:
        st.subheader("🚧 Recent Downtime Events (24h)")
        
        # Get top downtime events from today and yesterday
        downtime_query = """
        SELECT 
            m.Name as MachineName,
            m.Type as MachineType,
            d.Reason as DowntimeReason,
            d.Category as DowntimeCategory,
            d.Duration as DurationMinutes,
            d.Description
        FROM 
            Downtimes d
        JOIN 
            Machines m ON d.MachineID = m.MachineID
        WHERE 
            d.StartTime >= date('now', '-1 day')
        ORDER BY 
            d.Duration DESC
        LIMIT 5
        """
        
        result = db_manager.execute_query(downtime_query)
        
        if result["success"] and result["row_count"] > 0:
            downtime_df = pd.DataFrame(result["rows"])
            
            # Create visualization
            fig = px.bar(
                downtime_df,
                x='DurationMinutes',
                y='MachineName',
                color='DowntimeCategory',
                title='Top Downtime Events (Last 24h)',
                labels={
                    'DurationMinutes': 'Duration (minutes)', 
                    'MachineName': 'Machine',
                    'DowntimeCategory': 'Category'
                },
                color_discrete_map={
                    'planned': '#636EFA',
                    'unplanned': '#EF553B'
                },
                orientation='h'
            )
            
            # Sort by duration
            fig.update_layout(yaxis={'categoryorder':'total ascending'})
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Display downtime details
            st.write("Downtime Details:")
            
            for i, row in downtime_df.iterrows():
                downtime_color = "blue" if row['DowntimeCategory'] == 'planned' else "red"
                
                st.markdown(f"""
                **{row['MachineName']} ({row['MachineType']})**: <span style='color:{downtime_color}'>{row['DurationMinutes']} minutes</span>  
                Reason: {row['DowntimeReason']} ({row['DowntimeCategory']})  
                Description: {row['Description']}
                """, unsafe_allow_html=True)
                st.markdown("---")
        else:
            st.info("No downtime events in the last 24 hours")
    
    # Get top downtime reasons by category
    st.subheader("Downtime Pareto (Last 7 Days)")
    
    downtime_pareto_query = """
    SELECT 
        d.Reason as DowntimeReason,
        d.Category as DowntimeCategory,
        COUNT(d.DowntimeID) as OccurrenceCount,
        SUM(d.Duration) as TotalMinutes
    FROM 
        Downtimes d
    WHERE 
        d.StartTime >= date('now', '-7 day')
    GROUP BY 
        d.Reason, d.Category
    ORDER BY 
        TotalMinutes DESC
    LIMIT 10
    """
    
    result = db_manager.execute_query(downtime_pareto_query)
    
    if result["success"] and result["row_count"] > 0:
        pareto_df = pd.DataFrame(result["rows"])
        
        # Add cumulative percentage for Pareto analysis
        pareto_df = pareto_df.sort_values('TotalMinutes', ascending=False)
        pareto_df['CumulativeMinutes'] = pareto_df['TotalMinutes'].cumsum()
        total_minutes = pareto_df['TotalMinutes'].sum()
        pareto_df['CumulativePercentage'] = (pareto_df['CumulativeMinutes'] / total_minutes) * 100
        
        # Create Pareto chart
        fig = go.Figure()
        
        # Add bars
        fig.add_trace(go.Bar(
            x=pareto_df['DowntimeReason'],
            y=pareto_df['TotalMinutes'],
            name='Downtime Minutes',
            marker_color=pareto_df['DowntimeCategory'].map({
                'planned': '#636EFA',
                'unplanned': '#EF553B'
            })
        ))
        
        # Add cumulative percentage line
        fig.add_trace(go.Scatter(
            x=pareto_df['DowntimeReason'],
            y=pareto_df['CumulativePercentage'],
            name='Cumulative %',
            mode='lines+markers',
            line=dict(color='#00CC96', width=3),
            yaxis='y2'
        ))
        
        # Update layout with dual y-axis
        fig.update_layout(
            title='Downtime Pareto Analysis (80/20 Rule)',
            xaxis_title='Downtime Reason',
            yaxis_title='Total Minutes',
            yaxis2=dict(
                title='Cumulative %',
                anchor='x',
                overlaying='y',
                side='right',
                range=[0, 100]
            ),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        # Add 80% line for Pareto principle
        fig.add_shape(
            type="line",
            x0=-0.5,
            x1=len(pareto_df) - 0.5,
            y0=80,
            y1=80,
            line=dict(color="red", width=2, dash="dash"),
            yref='y2'
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Show downtime summary
        total_hours = total_minutes / 60
        planned_minutes = pareto_df[pareto_df['DowntimeCategory'] == 'planned']['TotalMinutes'].sum()
        unplanned_minutes = pareto_df[pareto_df['DowntimeCategory'] == 'unplanned']['TotalMinutes'].sum()
        
        metrics_cols = st.columns(3)
        
        metrics_cols[0].metric(
            "Total Downtime", 
            f"{total_hours:.1f} hours"
        )
        
        metrics_cols[1].metric(
            "Planned Downtime", 
            f"{planned_minutes / 60:.1f} hours",
            f"{planned_minutes / total_minutes * 100:.1f}%"
        )
        
        metrics_cols[2].metric(
            "Unplanned Downtime", 
            f"{unplanned_minutes / 60:.1f} hours",
            f"{unplanned_minutes / total_minutes * 100:.1f}%"
        )
    else:
        st.info("No downtime pareto data available")

def display_production_schedule():
    """Display production schedule and planning data"""
    st.header("📆 Production Schedule & Planning")
    
    # Create columns layout
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Today's Production Plan")
        
        # Get today's scheduled production
        todays_plan_query = """
        SELECT 
            p.Name as ProductName,
            p.Category as ProductCategory,
            COUNT(wo.OrderID) as OrderCount,
            SUM(wo.Quantity) as PlannedQuantity,
            wc.Name as WorkCenterName
        FROM 
            WorkOrders wo
        JOIN 
            Products p ON wo.ProductID = p.ProductID
        JOIN 
            WorkCenters wc ON wo.WorkCenterID = wc.WorkCenterID
        WHERE 
            date(wo.PlannedStartTime) <= date('now')
            AND date(wo.PlannedEndTime) >= date('now')
            AND wo.Status IN ('scheduled', 'in_progress')
        GROUP BY 
            p.Name, p.Category, wc.Name
        ORDER BY 
            OrderCount DESC
        """
        
        result = db_manager.execute_query(todays_plan_query)
        
        if result["success"] and result["row_count"] > 0:
            today_df = pd.DataFrame(result["rows"])
            
            # Create visualization
            fig = px.bar(
                today_df,
                x='ProductName',
                y='PlannedQuantity',
                color='WorkCenterName',
                title="Today's Production Plan by Product",
                labels={
                    'PlannedQuantity': 'Planned Units', 
                    'ProductName': 'Product',
                    'WorkCenterName': 'Work Center'
                }
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Show summary metrics
            total_orders = today_df['OrderCount'].sum()
            total_quantity = today_df['PlannedQuantity'].sum()
            
            metrics_cols = st.columns(2)
            metrics_cols[0].metric("Active Orders Today", f"{int(total_orders):,}")
            metrics_cols[1].metric("Planned Production Today", f"{int(total_quantity):,} units")
            
            # Show detailed table
            with st.expander("Today's Detailed Plan", expanded=False):
                st.dataframe(today_df)
        else:
            st.info("No production plan data available for today")
    
    with col2:
        st.subheader("Weekly Production Forecast")
        
        # Get weekly planned production (next 7 days)
        weekly_forecast_query = """
        SELECT 
            date(wo.PlannedStartTime) as ProductionDate,
            p.Category as ProductCategory,
            COUNT(wo.OrderID) as OrderCount,
            SUM(wo.Quantity) as PlannedQuantity
        FROM 
            WorkOrders wo
        JOIN 
            Products p ON wo.ProductID = p.ProductID
        WHERE 
            wo.PlannedStartTime >= date('now')
            AND wo.PlannedStartTime <= date('now', '+7 day')
            AND wo.Status = 'scheduled'
        GROUP BY 
            date(wo.PlannedStartTime), p.Category
        ORDER BY 
            ProductionDate
        """
        
        result = db_manager.execute_query(weekly_forecast_query)
        
        if result["success"] and result["row_count"] > 0:
            forecast_df = pd.DataFrame(result["rows"])
            
            # Convert to datetime for better display
            forecast_df['ProductionDate'] = pd.to_datetime(forecast_df['ProductionDate'])
            
            # Create visualization
            fig = px.area(
                forecast_df,
                x='ProductionDate',
                y='PlannedQuantity',
                color='ProductCategory',
                title='Weekly Production Forecast',
                labels={
                    'PlannedQuantity': 'Planned Units', 
                    'ProductionDate': 'Date',
                    'ProductCategory': 'Product Category'
                }
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Weekly summary
            total_weekly_quantity = forecast_df['PlannedQuantity'].sum()
            total_weekly_orders = forecast_df['OrderCount'].sum()
            
            metrics_cols = st.columns(2)
            metrics_cols[0].metric("Weekly Planned Orders", f"{int(total_weekly_orders):,}")
            metrics_cols[1].metric("Weekly Planned Units", f"{int(total_weekly_quantity):,}")
        else:
            st.info("No production forecast data available")
    
    # Material requirements section
    st.subheader("Critical Material Requirements")
    
    # Get materials required for upcoming production with potential shortages
    material_requirements_query = """
    SELECT 
        i.Name as ItemName,
        i.Category as ItemCategory,
        i.Quantity as CurrentInventory,
        i.ReorderLevel,
        i.LeadTime as LeadTimeInDays,
        s.Name as SupplierName,
        SUM(bom.Quantity * wo.Quantity) as RequiredQuantity,
        i.Quantity - SUM(bom.Quantity * wo.Quantity) as ProjectedBalance
    FROM 
        WorkOrders wo
    JOIN 
        BillOfMaterials bom ON wo.ProductID = bom.ProductID
    JOIN 
        Inventory i ON bom.ComponentID = i.ItemID
    JOIN 
        Suppliers s ON i.SupplierID = s.SupplierID
    WHERE 
        wo.Status = 'scheduled'
        AND wo.PlannedStartTime <= date('now', '+7 day')
    GROUP BY 
        i.ItemID, i.Name, i.Category, i.Quantity, i.ReorderLevel, i.LeadTime, s.Name
    HAVING 
        ProjectedBalance < i.ReorderLevel OR ProjectedBalance < 0
    ORDER BY 
        ProjectedBalance ASC
    LIMIT 10
    """
    
    result = db_manager.execute_query(material_requirements_query)
    
    if result["success"] and result["row_count"] > 0:
        materials_df = pd.DataFrame(result["rows"])
        
        # Add risk classification
        def classify_risk(row):
            if row['ProjectedBalance'] < 0:
                return 'Critical'
            elif row['ProjectedBalance'] < row['ReorderLevel'] / 2:
                return 'High'
            else:
                return 'Medium'
                
        materials_df['Risk'] = materials_df.apply(classify_risk, axis=1)
        
        # Create visualization
        fig = go.Figure()
        
        # Add current inventory bars
        fig.add_trace(go.Bar(
            x=materials_df['ItemName'],
            y=materials_df['CurrentInventory'],
            name='Current Inventory',
            marker_color='#636EFA'
        ))
        
        # Add required quantity bars
        fig.add_trace(go.Bar(
            x=materials_df['ItemName'],
            y=materials_df['RequiredQuantity'],
            name='Required Quantity',
            marker_color='#EF553B'
        ))
        
        # Add reorder level line
        for i, item in enumerate(materials_df['ItemName']):
            reorder_level = materials_df[materials_df['ItemName'] == item]['ReorderLevel'].values[0]
            fig.add_shape(
                type="line",
                x0=i-0.4,
                x1=i+0.4,
                y0=reorder_level,
                y1=reorder_level,
                line=dict(color="green", width=2, dash="dash")
            )
        
        fig.update_layout(
            title='Critical Material Requirements vs Inventory',
            xaxis_title='Material',
            yaxis_title='Quantity',
            barmode='group',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Show critical materials in detail
        st.write("Critical Materials for Upcoming Production:")
        
        for i, row in materials_df.iterrows():
            if row['Risk'] == 'Critical':
                risk_color = "red"
            elif row['Risk'] == 'High':
                risk_color = "orange"
            else:
                risk_color = "blue"
            
            # Calculate days until depletion
            if row['RequiredQuantity'] > 0:
                days_until_depletion = max(0, int(row['CurrentInventory'] / (row['RequiredQuantity'] / 7)))
            else:
                days_until_depletion = "N/A"
            
            st.markdown(f"""
            **{row['ItemName']}**: <span style='color:{risk_color}'>{row['Risk']} Risk</span>  
            Current: {int(row['CurrentInventory']):,} | Required: {int(row['RequiredQuantity']):,} | Projected Balance: {int(row['ProjectedBalance']):,}  
            Lead Time: {row['LeadTimeInDays']} days | Days Until Depletion: {days_until_depletion} | Supplier: {row['SupplierName']}
            """, unsafe_allow_html=True)
            
            # Add progress/warning bar
            if row['ProjectedBalance'] < 0:
                # If negative balance, show -100%
                st.progress(0.0)
            else:
                # Show percentage of reorder level
                reorder_pct = min(1.0, row['ProjectedBalance'] / row['ReorderLevel'])
                st.progress(reorder_pct)
            
            st.markdown("---")
    else:
        st.info("No critical material requirements found")
    
    # Upcoming maintenance that might impact production
    with st.expander("Upcoming Maintenance (Next 7 Days)", expanded=False):
        maintenance_data = db_manager.get_upcoming_maintenance(days_ahead=7)
        
        if not maintenance_data.empty:
            # Add impact assessment
            maintenance_query = """
            SELECT 
                m.Name as MachineName,
                COUNT(wo.OrderID) as ImpactedOrders
            FROM 
                Machines m
            JOIN 
                WorkOrders wo ON m.MachineID = wo.MachineID
            WHERE 
                wo.Status = 'scheduled'
                AND date(wo.PlannedStartTime) <= date(m.NextMaintenanceDate)
                AND date(wo.PlannedEndTime) >= date(m.NextMaintenanceDate)
            GROUP BY 
                m.Name
            """
            
            result = db_manager.execute_query(maintenance_query)
            
            if result["success"] and result["row_count"] > 0:
                impact_df = pd.DataFrame(result["rows"])
                
                # Merge with maintenance data
                maintenance_df = pd.merge(
                    maintenance_data, 
                    impact_df, 
                    on='MachineName', 
                    how='left'
                )
                
                # Fill NA values
                maintenance_df['ImpactedOrders'] = maintenance_df['ImpactedOrders'].fillna(0)
                
                # Sort by impacted orders and date
                maintenance_df = maintenance_df.sort_values(
                    ['ImpactedOrders', 'DaysUntilMaintenance'], 
                    ascending=[False, True]
                )
                
                # Display table with impact
                st.dataframe(maintenance_df)
            else:
                st.dataframe(maintenance_data)
        else:
            st.info("No upcoming maintenance scheduled")

def get_oee_color(oee_value):
    """Return color based on OEE value"""
    if oee_value >= 85:
        return "#00CC96"  # Good (green)
    elif oee_value >= 60:
        return "#FFA15A"  # Warning (orange)
    else:
        return "#EF553B"  # Poor (red)