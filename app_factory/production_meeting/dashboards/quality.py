"""
Quality dashboard functionality focused on daily production meetings
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

from app_factory.shared.database import DatabaseManager
from app_factory.shared.db_utils import days_ago, today
from ..ai_insights import generate_ai_insight

# Initialize database manager
db_manager = DatabaseManager()

# Import shared color configuration
from .color_config import (
    DEFAULT_COLORS, QUALITY_COLORS, STATUS_COLORS,
    apply_theme_compatibility
)

def create_enhanced_quality_chart(df, chart_type, x_col, y_col, title, color_col=None):
    """Create enhanced quality charts with better formatting and Streamlit colors"""
    if chart_type == 'bar':
        if color_col:
            fig = px.bar(
                df,
                x=x_col,
                y=y_col,
                color=color_col,
                title=title,
                color_continuous_scale='Reds',
                text=y_col
            )
        else:
            fig = px.bar(
                df,
                x=x_col,
                y=y_col,
                title=title,
                color_discrete_sequence=DEFAULT_COLORS
            )
            
        fig.update_traces(
            texttemplate='%{text}',
            textposition='outside'
        )
        
    elif chart_type == 'horizontal_bar':
        fig = px.bar(
            df,
            y=x_col,
            x=y_col,
            orientation='h',
            color=color_col if color_col else None,
            title=title,
            color_continuous_scale='Reds' if color_col else None,
            color_discrete_sequence=DEFAULT_COLORS if not color_col else None
        )
        
        fig.update_layout(yaxis={'categoryorder':'total ascending'})
        
    # Apply consistent formatting
    fig.update_layout(
        template="plotly",
        height=400,
        title=dict(font=dict(size=16)),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        hovermode='closest'
    )
    
    return fig

def quality_dashboard():
    """Display the quality dashboard optimized for daily production meetings"""
    st.header("⚠️ Quality Overview")
    
    # Create date filters for time-based analysis with more relevant options for daily meetings
    col1, col2 = st.columns([1, 3])
    with col1:
        time_period = st.selectbox(
            "Compare With",
            ["Yesterday", "Last 7 Days", "Last 30 Days"],
            index=0  # Default to Yesterday
        )
        
        if time_period == "Yesterday":
            days_back = 1
            compare_days = 2  # Compare with day before yesterday
        elif time_period == "Last 7 Days":
            days_back = 7
            compare_days = 14  # Compare with previous 7 days
        else:  # Last 30 Days
            days_back = 30
            compare_days = 60  # Compare with previous 30 days

    # Calculate dates for parameterized queries
    yesterday_date = days_ago(1)
    two_days_ago_date = days_ago(2)
    thirty_days_ago_date = days_ago(30)

    # Get yesterday's quality data
    yesterday_quality = db_manager.get_quality_summary(days_back=1, range_days=1)
    
    # Get comparison period quality data (for Yesterday: day before yesterday, for weekly: previous week, etc.)
    comparison_quality = db_manager.get_quality_summary(days_back=compare_days, range_days=days_back)
    
    if not yesterday_quality.empty:
        # Summary metrics - enhanced with targets and trends
        yesterday_defect_rate = yesterday_quality['AvgDefectRate'].mean()
        yesterday_rework_rate = yesterday_quality['AvgReworkRate'].mean()
        yesterday_yield_rate = yesterday_quality['AvgYieldRate'].mean()
        
        # Get comparison metrics for selected period
        if not comparison_quality.empty:
            comparison_defect_rate = comparison_quality['AvgDefectRate'].mean()
            comparison_rework_rate = comparison_quality['AvgReworkRate'].mean()
            comparison_yield_rate = comparison_quality['AvgYieldRate'].mean()
            
            defect_delta = yesterday_defect_rate - comparison_defect_rate
            rework_delta = yesterday_rework_rate - comparison_rework_rate
            yield_delta = yesterday_yield_rate - comparison_yield_rate
        else:
            defect_delta = 0
            rework_delta = 0
            yield_delta = 0
        
        # Display metrics with trends
        metrics_cols = st.columns(3)
        
        # For defects and rework, lower is better (negative delta is good)
        metrics_cols[0].metric(
            "Yesterday's Defect Rate", 
            f"{yesterday_defect_rate:.2f}%", 
            f"{defect_delta:.2f}% vs {time_period}",
            delta_color="inverse"  # Red if increasing, green if decreasing
        )
        
        metrics_cols[1].metric(
            "Yesterday's Rework Rate", 
            f"{yesterday_rework_rate:.2f}%", 
            f"{rework_delta:.2f}% vs {time_period}",
            delta_color="inverse"  # Red if increasing, green if decreasing
        )
        
        # For yield, higher is better (positive delta is good)
        metrics_cols[2].metric(
            "Yesterday's Yield Rate", 
            f"{yesterday_yield_rate:.2f}%", 
            f"{yield_delta:.2f}% vs {time_period}"
        )
        
        # Create tabs for different daily meeting views
        tab1, tab2, tab3 = st.tabs([
            "Top Issues", 
            "Quality Trends", 
            "Work Center Focus"
        ])
        
        with tab1:
            st.subheader("Yesterday's Top Quality Issues")

            # Get yesterday's defects using parameterized query
            from app_factory.shared.db_utils import date_range_start, date_range_end
            yesterday_start = date_range_start(yesterday_date)
            yesterday_end = date_range_end(yesterday_date)

            defects_query = """
            SELECT
                d.DefectType,
                d.Severity,
                COUNT(d.DefectID) as DefectCount,
                SUM(d.Quantity) as TotalQuantity,
                ROUND(AVG(d.Severity), 1) as AvgSeverity,
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
                qc.Date >= :yesterday_start AND qc.Date <= :yesterday_end
            GROUP BY
                d.DefectType
            ORDER BY
                DefectCount DESC
            LIMIT 10
            """

            defect_result = db_manager.execute_query(
                defects_query,
                {"yesterday_start": yesterday_start, "yesterday_end": yesterday_end}
            )
            
            if defect_result["success"] and defect_result["row_count"] > 0:
                defects_df = pd.DataFrame(defect_result["rows"])
                
                # Top Issues and Key Products
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("#### 🚨 Top Defect Types")
                    
                    # Create enhanced horizontal bar chart of defect types
                    fig1 = create_enhanced_quality_chart(
                        df=defects_df,
                        chart_type='horizontal_bar',
                        x_col='DefectType',
                        y_col='DefectCount',
                        title='Yesterday\'s Top Defect Types',
                        color_col='AvgSeverity'
                    )
                    
                    # Add severity indicators
                    fig1.update_traces(
                        texttemplate='%{x}',
                        textposition='outside',
                        hovertemplate='<b>%{y}</b><br>Count: %{x}<br>Avg Severity: %{marker.color:.1f}<extra></extra>'
                    )
                    
                    fig1.update_layout(
                        xaxis_title='Number of Occurrences',
                        yaxis_title='Defect Type',
                        coloraxis_colorbar=dict(title='Avg Severity (1-5)')
                    )
                    
                    st.plotly_chart(fig1, use_container_width=True)
                
                with col2:
                    # Get problem products from yesterday using parameterized query
                    product_query = """
                    SELECT
                        p.Name as ProductName,
                        COUNT(d.DefectID) as DefectCount,
                        ROUND(AVG(qc.DefectRate) * 100, 2) as AvgDefectRate,
                        ROUND(AVG(qc.YieldRate) * 100, 2) as AvgYieldRate
                    FROM
                        Products p
                    JOIN
                        WorkOrders wo ON p.ProductID = wo.ProductID
                    JOIN
                        QualityControl qc ON wo.OrderID = qc.OrderID
                    JOIN
                        Defects d ON qc.CheckID = d.CheckID
                    WHERE
                        qc.Date >= :yesterday_start AND qc.Date <= :yesterday_end
                    GROUP BY
                        p.Name
                    ORDER BY
                        DefectCount DESC
                    LIMIT 5
                    """

                    product_result = db_manager.execute_query(
                        product_query,
                        {"yesterday_start": yesterday_start, "yesterday_end": yesterday_end}
                    )
                    
                    if product_result["success"] and product_result["row_count"] > 0:
                        st.markdown("#### 🔍 Problem Products")
                        
                        products_df = pd.DataFrame(product_result["rows"])
                        
                        # Create enhanced bar chart of problem products
                        fig2 = create_enhanced_quality_chart(
                            df=products_df,
                            chart_type='bar',
                            x_col='ProductName',
                            y_col='DefectCount',
                            title='Yesterday\'s Problem Products',
                            color_col='AvgDefectRate'
                        )
                        
                        fig2.update_traces(
                            hovertemplate='<b>%{x}</b><br>Defects: %{y}<br>Defect Rate: %{marker.color:.1f}%<extra></extra>'
                        )
                        
                        fig2.update_layout(
                            xaxis=dict(tickangle=-45),
                            coloraxis_colorbar=dict(title='Defect Rate (%)')
                        )
                        
                        st.plotly_chart(fig2, use_container_width=True)
                    else:
                        st.info("No product quality data available for yesterday")
                
                # Get specific defect combinations (product + defect type + work center)
                specific_query = """
                SELECT
                    p.Name as ProductName,
                    d.DefectType,
                    wc.Name as WorkCenterName,
                    COUNT(d.DefectID) as DefectCount,
                    ROUND(AVG(d.Severity), 1) as AvgSeverity
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
                    qc.Date >= :yesterday_start AND qc.Date <= :yesterday_end
                GROUP BY
                    p.Name, d.DefectType, wc.Name
                ORDER BY
                    DefectCount DESC
                LIMIT 10
                """

                specific_result = db_manager.execute_query(
                    specific_query,
                    {"yesterday_start": yesterday_start, "yesterday_end": yesterday_end}
                )
                
                if specific_result["success"] and specific_result["row_count"] > 0:
                    st.markdown("#### 🎯 Action Items for Today")
                    
                    specific_df = pd.DataFrame(specific_result["rows"])
                    
                    # Format the dataframe for display
                    display_df = specific_df.copy()
                    display_df['AvgSeverity'] = display_df['AvgSeverity'].round(1)

                    # Display the dataframe (plain styling works in both themes)
                    st.dataframe(display_df, use_container_width=True)
                    
                    # Create actionable suggestions
                    st.markdown("##### Suggested Actions:")
                    
                    # Get top 3 most severe issues
                    top_severe = specific_df.sort_values('AvgSeverity', ascending=False).head(3)
                    
                    for i, row in top_severe.iterrows():
                        action = f"**Investigate {row['DefectType']}** issues with product **{row['ProductName']}** at **{row['WorkCenterName']}** (Severity: {row['AvgSeverity']:.1f})"
                        st.markdown(f"- {action}")
                    
                    # Add general action for most common defect type
                    most_common = defects_df.iloc[0]
                    st.markdown(f"- Plan quality focus on **{most_common['DefectType']}** defects which occurred {most_common['DefectCount']} times yesterday")
            else:
                st.info("No defect data available for yesterday")
        
        with tab2:
            st.subheader("Quality Trends")
            
            # Get daily quality trend data using parameterized query
            trend_query = """
            SELECT
                date(qc.Date) as InspectionDate,
                COUNT(qc.CheckID) as InspectionCount,
                ROUND(AVG(qc.DefectRate) * 100, 2) as AvgDefectRate,
                ROUND(AVG(qc.ReworkRate) * 100, 2) as AvgReworkRate,
                ROUND(AVG(qc.YieldRate) * 100, 2) as AvgYieldRate,
                COUNT(DISTINCT wo.OrderID) as OrderCount
            FROM
                QualityControl qc
            JOIN
                WorkOrders wo ON qc.OrderID = wo.OrderID
            WHERE
                qc.Date >= :thirty_days_ago
            GROUP BY
                date(qc.Date)
            ORDER BY
                InspectionDate
            """

            trend_result = db_manager.execute_query(
                trend_query,
                {"thirty_days_ago": thirty_days_ago_date}
            )
            
            if trend_result["success"] and trend_result["row_count"] > 0:
                trend_df = pd.DataFrame(trend_result["rows"])
                
                # Convert to datetime for better display
                trend_df['InspectionDate'] = pd.to_datetime(trend_df['InspectionDate'])
                
                # Create enhanced quality metrics trend chart
                fig3 = go.Figure()
                
                # Add defect rate line with Streamlit colors
                fig3.add_trace(
                    go.Scatter(
                        x=trend_df['InspectionDate'],
                        y=trend_df['AvgDefectRate'],
                        name='Defect Rate',
                        mode='lines+markers',
                        line=dict(color=DEFAULT_COLORS[0], width=3),  # Red
                        marker=dict(size=8),
                        hovertemplate='<b>Defect Rate</b><br>Date: %{x}<br>Rate: %{y:.2f}%<extra></extra>'
                    )
                )
                
                # Add yield rate line
                fig3.add_trace(
                    go.Scatter(
                        x=trend_df['InspectionDate'],
                        y=trend_df['AvgYieldRate'],
                        name='Yield Rate',
                        mode='lines+markers',
                        line=dict(color=DEFAULT_COLORS[3], width=3),  # Green
                        marker=dict(size=8),
                        yaxis='y2',
                        hovertemplate='<b>Yield Rate</b><br>Date: %{x}<br>Rate: %{y:.2f}%<extra></extra>'
                    )
                )
                
                # Add inspection count as bar chart with transparency
                fig3.add_trace(
                    go.Bar(
                        x=trend_df['InspectionDate'],
                        y=trend_df['InspectionCount'],
                        name='Inspections',
                        marker_color=DEFAULT_COLORS[2],  # Blue
                        opacity=0.3,
                        yaxis='y3',
                        hovertemplate='<b>Inspections</b><br>Date: %{x}<br>Count: %{y}<extra></extra>'
                    )
                )
                
                # Add target lines with annotations
                fig3.add_shape(
                    type="line",
                    x0=trend_df['InspectionDate'].min(),
                    x1=trend_df['InspectionDate'].max(),
                    y0=3,  # Target defect rate
                    y1=3,
                    line=dict(color="red", width=2, dash="dash")
                )
                
                fig3.add_annotation(
                    x=trend_df['InspectionDate'].iloc[-1],
                    y=3.2,
                    text="Target: 3%",
                    showarrow=False,
                    font=dict(color="red", size=12)
                )
                
                # Enhanced layout with multiple y-axes
                fig3.update_layout(
                    title=dict(text='Quality Metrics Trend - Last 30 Days', font=dict(size=16)),
                    xaxis=dict(title='Date'),
                    yaxis=dict(
                        title='Defect Rate (%)',
                        side='left',
                        range=[0, max(10, trend_df['AvgDefectRate'].max() * 1.1)]
                    ),
                    yaxis2=dict(
                        title='Yield Rate (%)',
                        side='right',
                        overlaying='y',
                        range=[min(90, trend_df['AvgYieldRate'].min() * 0.9), 100]
                    ),
                    yaxis3=dict(
                        title='Inspections',
                        side='right',
                        overlaying='y',
                        position=0.85,
                        anchor='free',
                        range=[0, trend_df['InspectionCount'].max() * 1.2]
                    ),
                    template="plotly",
                    height=450,
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="center",
                        x=0.5
                    ),
                    hovermode="x unified"
                )
                
                st.plotly_chart(fig3, use_container_width=True)
                
                # Add 7-day moving average
                if len(trend_df) >= 7:
                    trend_df['DefectRate_7DMA'] = trend_df['AvgDefectRate'].rolling(window=7).mean()
                    trend_df['YieldRate_7DMA'] = trend_df['AvgYieldRate'].rolling(window=7).mean()
                    
                    # Create a line chart for 7-day moving averages
                    fig4 = px.line(
                        trend_df.dropna(),
                        x='InspectionDate',
                        y=['DefectRate_7DMA', 'YieldRate_7DMA'],
                        title='7-Day Moving Average Trends',
                        labels={
                            'InspectionDate': 'Date',
                            'value': 'Rate (%)',
                            'variable': 'Metric'
                        },
                        color_discrete_map={
                            'DefectRate_7DMA': 'red',
                            'YieldRate_7DMA': 'green'
                        },
                        line_shape='spline'
                    )
                    
                    fig4.update_xaxes(
                        rangeslider_visible=True
                    )
                    
                    st.plotly_chart(fig4, use_container_width=True)
            else:
                st.info("Not enough quality data for trend analysis")
        
        with tab3:
            st.subheader("Work Center Focus")

            # Calculate two days ago date range
            two_days_ago_start = date_range_start(two_days_ago_date)
            two_days_ago_end = date_range_end(two_days_ago_date)

            # Get yesterday's work center quality data using parameterized query
            wc_query = """
            SELECT
                wc.Name as WorkCenterName,
                COUNT(qc.CheckID) as InspectionCount,
                ROUND(AVG(qc.DefectRate) * 100, 2) as AvgDefectRate,
                ROUND(AVG(qc.ReworkRate) * 100, 2) as AvgReworkRate,
                ROUND(AVG(qc.YieldRate) * 100, 2) as AvgYieldRate,
                COUNT(DISTINCT wo.OrderID) as OrderCount
            FROM
                WorkCenters wc
            JOIN
                WorkOrders wo ON wc.WorkCenterID = wo.WorkCenterID
            JOIN
                QualityControl qc ON wo.OrderID = qc.OrderID
            WHERE
                qc.Date >= :yesterday_start AND qc.Date <= :yesterday_end
            GROUP BY
                wc.Name
            ORDER BY
                AvgDefectRate DESC
            """

            wc_result = db_manager.execute_query(
                wc_query,
                {"yesterday_start": yesterday_start, "yesterday_end": yesterday_end}
            )

            if wc_result["success"] and wc_result["row_count"] > 0:
                wc_df = pd.DataFrame(wc_result["rows"])

                # Get previous day work center data for comparison
                prev_wc_query = """
                SELECT
                    wc.Name as WorkCenterName,
                    ROUND(AVG(qc.DefectRate) * 100, 2) as AvgDefectRate
                FROM
                    WorkCenters wc
                JOIN
                    WorkOrders wo ON wc.WorkCenterID = wo.WorkCenterID
                JOIN
                    QualityControl qc ON wo.OrderID = qc.OrderID
                WHERE
                    qc.Date >= :two_days_ago_start AND qc.Date <= :two_days_ago_end
                GROUP BY
                    wc.Name
                """

                prev_wc_result = db_manager.execute_query(
                    prev_wc_query,
                    {"two_days_ago_start": two_days_ago_start, "two_days_ago_end": two_days_ago_end}
                )
                
                if prev_wc_result["success"] and prev_wc_result["row_count"] > 0:
                    prev_wc_df = pd.DataFrame(prev_wc_result["rows"])
                    
                    # Merge with current data
                    wc_df = wc_df.merge(
                        prev_wc_df,
                        on='WorkCenterName',
                        how='left',
                        suffixes=('', '_Prev')
                    )
                    
                    # Calculate day-over-day change
                    wc_df['DefectRateChange'] = wc_df['AvgDefectRate'] - wc_df['AvgDefectRate_Prev']
                
                # Create a bar chart with work center performance
                fig5 = px.bar(
                    wc_df,
                    x='WorkCenterName',
                    y='AvgDefectRate',
                    color='AvgDefectRate',
                    title='Yesterday\'s Defect Rate by Work Center',
                    labels={
                        'WorkCenterName': 'Work Center',
                        'AvgDefectRate': 'Defect Rate (%)'
                    },
                    color_continuous_scale='Reds',
                    text_auto='.1f'
                )
                
                # Add target line
                fig5.add_shape(
                    type="line",
                    x0=-0.5,
                    x1=len(wc_df)-0.5,
                    y0=3,  # Target defect rate
                    y1=3,
                    line=dict(color="green", width=2, dash="dash"),
                )
                
                fig5.add_annotation(
                    x=len(wc_df)/2,
                    y=3.5,
                    text="Target: 3.0%",
                    showarrow=False,
                    font=dict(size=12)
                )
                
                # Improve layout
                fig5.update_layout(
                    xaxis_tickangle=-45,
                    uniformtext_minsize=10,
                    uniformtext_mode='hide'
                )
                
                st.plotly_chart(fig5, use_container_width=True)
                
                # Show change from previous day if available
                if 'DefectRateChange' in wc_df.columns:
                    # Sort by largest increase (worst)
                    wc_df = wc_df.sort_values('DefectRateChange', ascending=False)
                    
                    # Create a bar chart of changes
                    fig6 = px.bar(
                        wc_df,
                        x='WorkCenterName',
                        y='DefectRateChange',
                        title='Day-over-day Change in Defect Rate',
                        labels={
                            'WorkCenterName': 'Work Center',
                            'DefectRateChange': 'Change in Defect Rate (pp)'
                        },
                        text_auto='.1f',
                        color='DefectRateChange',
                        color_continuous_scale='RdYlGn_r'
                    )
                    
                    # Add zero line
                    fig6.add_shape(
                        type="line",
                        x0=-0.5,
                        x1=len(wc_df)-0.5,
                        y0=0,
                        y1=0,
                        line=dict(color="gray", width=1),
                    )
                    
                    # Improve layout
                    fig6.update_layout(
                        xaxis_tickangle=-45,
                        uniformtext_minsize=10,
                        uniformtext_mode='hide'
                    )
                    
                    st.plotly_chart(fig6, use_container_width=True)
                
                # Create work center focus table with recommendations
                st.markdown("#### Today's Work Center Focus Areas")
                
                # Determine focus areas
                if 'DefectRateChange' in wc_df.columns:
                    # Focus on work centers with high defect rates OR large increases
                    focus_wc = wc_df[
                        (wc_df['AvgDefectRate'] > 3) |  # Above target
                        (wc_df['DefectRateChange'] > 1)  # Significant increase
                    ].copy()
                else:
                    # Just focus on high defect rates
                    focus_wc = wc_df[wc_df['AvgDefectRate'] > 3].copy()
                
                if not focus_wc.empty:
                    # Sort by defect rate
                    focus_wc = focus_wc.sort_values('AvgDefectRate', ascending=False)
                    
                    # Generate focus recommendations for each work center
                    for i, row in focus_wc.iterrows():
                        with st.expander(f"🔍 {row['WorkCenterName']} - Defect Rate: {row['AvgDefectRate']:.1f}%"):
                            # Get specific defects for this work center using parameterized query
                            wc_defects_query = """
                            SELECT
                                d.DefectType,
                                COUNT(d.DefectID) as DefectCount,
                                AVG(d.Severity) as AvgSeverity,
                                p.Name as ProductName
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
                                qc.Date >= :yesterday_start AND qc.Date <= :yesterday_end
                                AND wc.Name = :work_center_name
                            GROUP BY
                                d.DefectType, p.Name
                            ORDER BY
                                DefectCount DESC
                            LIMIT 5
                            """

                            wc_defects_result = db_manager.execute_query(
                                wc_defects_query,
                                {
                                    "yesterday_start": yesterday_start,
                                    "yesterday_end": yesterday_end,
                                    "work_center_name": row['WorkCenterName']
                                }
                            )
                            
                            if wc_defects_result["success"] and wc_defects_result["row_count"] > 0:
                                wc_defects_df = pd.DataFrame(wc_defects_result["rows"])
                                
                                # Display top defects
                                st.dataframe(wc_defects_df, use_container_width=True)
                                
                                # Generate recommendations
                                if 'DefectRateChange' in row and row['DefectRateChange'] > 1:
                                    st.markdown(f"⚠️ **Significant increase in defect rate** (+{row['DefectRateChange']:.1f}pp vs previous day)")
                                
                                # Top issues
                                if not wc_defects_df.empty:
                                    top_defect = wc_defects_df.iloc[0]
                                    st.markdown(f"🎯 **Focus on {top_defect['DefectType']}** which accounts for {top_defect['DefectCount']} defects")
                                    
                                    if len(wc_defects_df) > 1:
                                        st.markdown("**Additional checks needed for:**")
                                        for j, defect in wc_defects_df.iloc[1:].iterrows():
                                            st.markdown(f"- {defect['DefectType']} on {defect['ProductName']}")
                            else:
                                st.info(f"No specific defect data available for {row['WorkCenterName']}")
                else:
                    st.success("All work centers performing within acceptable limits!")
            else:
                st.info("No work center quality data available for yesterday")
        
        # Add AI-powered quality insights section
        st.subheader("🤖 AI-Powered Quality Insights")
        
        if st.button("Generate Daily Quality Briefing"):
            with st.spinner("Analyzing quality data..."):
                try:
                    # Generate insights using AI from the correct import path
                    from ..ai_insights import generate_ai_insight
                    
                    insight = generate_ai_insight(
                        context="quality",
                        temperature=0.1,
                        include_historical=True
                    )
                    
                    st.markdown(insight, unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"Error generating AI insights: {str(e)}")
                    st.info("Try manually reviewing the quality data visualizations above.")
    else:
        st.info("No quality data available for yesterday")
