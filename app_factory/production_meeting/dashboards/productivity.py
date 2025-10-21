"""
Productivity / personnel dashboard functionality
"""

import streamlit as st
import pandas as pd
import plotly.express as px

from app_factory.shared.database import DatabaseManager

# Initialize database manager
db_manager = DatabaseManager()

# Import shared color configuration
from .color_config import STREAMLIT_COLORS, apply_theme_compatibility

def productivity_dashboard():
    """Display employee productivity dashboard"""
    st.header("👥 Productivity Dashboard")
    
    # Get employee productivity data
    productivity_query = """
    SELECT 
        e.Name as EmployeeName,
        e.Role as EmployeeRole,
        s.Name as ShiftName,
        COUNT(DISTINCT wo.OrderID) as CompletedOrders,
        SUM(wo.ActualProduction) as TotalProduction,
        ROUND(AVG(julianday(wo.ActualEndTime) - julianday(wo.ActualStartTime)) * 24, 2) as AvgOrderHours,
        MAX(wo.ActualEndTime) as LastCompletedOrder
    FROM 
        Employees e
    JOIN 
        WorkOrders wo ON e.EmployeeID = wo.EmployeeID
    JOIN 
        Shifts s ON e.ShiftID = s.ShiftID
    WHERE 
        wo.Status = 'completed'
        AND wo.ActualEndTime >= date('now', '-30 day')
    GROUP BY 
        e.EmployeeID
    ORDER BY 
        CompletedOrders DESC
    LIMIT 10
    """
    
    result = db_manager.execute_query(productivity_query)
    if result["success"] and result["row_count"] > 0:
        productivity_df = pd.DataFrame(result["rows"])
        
        # Create bar chart of completed orders by employee
        st.subheader("Top Employees by Completed Orders (Last 30 Days)")
        
        fig = px.bar(
            productivity_df,
            x='EmployeeName',
            y='CompletedOrders',
            color='EmployeeRole',
            title='Top Employee Performance - Completed Orders (Last 30 Days)',
            labels={
                'CompletedOrders': 'Number of Orders',
                'EmployeeName': 'Employee',
                'EmployeeRole': 'Role'
            },
            color_discrete_sequence=STREAMLIT_COLORS,
            text='CompletedOrders'
        )
        
        # Enhanced formatting
        fig.update_traces(
            texttemplate='%{text}',
            textposition='outside'
        )
        
        fig.update_layout(
            template="plotly_white",
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
            hovermode='x'
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Employee productivity metrics
        col1, col2 = st.columns(2)
        
        with col1:
            # Production by role
            role_data = productivity_df.groupby('EmployeeRole').agg({
                'CompletedOrders': 'sum',
                'TotalProduction': 'sum'
            }).reset_index()
            
            fig = px.pie(
                role_data,
                values='TotalProduction',
                names='EmployeeRole',
                title='Production Output by Employee Role',
                hover_data=['CompletedOrders'],
                color_discrete_sequence=STREAMLIT_COLORS,
                hole=0.4  # Donut chart for better readability
            )
            
            # Enhanced formatting
            fig.update_traces(
                textposition='inside', 
                textinfo='percent+label',
                textfont_size=12,
                marker=dict(line=dict(color='#FFFFFF', width=2)),
                hovertemplate='<b>%{label}</b><br>Production: %{value:,.0f}<br>Orders: %{customdata[0]}<br>Percentage: %{percent}<extra></extra>'
            )
            
            fig.update_layout(
                template="plotly_white",
                height=350,
                title=dict(font=dict(size=14)),
                legend=dict(
                    orientation="v",
                    yanchor="middle",
                    y=0.5,
                    xanchor="left",
                    x=1.05
                ),
                margin=dict(l=20, r=100, t=60, b=20)
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Production by shift
            shift_data = productivity_df.groupby('ShiftName').agg({
                'CompletedOrders': 'sum',
                'TotalProduction': 'sum',
                'AvgOrderHours': 'mean'
            }).reset_index()
            
            fig = px.bar(
                shift_data,
                x='ShiftName',
                y='TotalProduction',
                color='AvgOrderHours',
                title='Production Output by Shift',
                labels={
                    'TotalProduction': 'Total Units Produced',
                    'ShiftName': 'Shift',
                    'AvgOrderHours': 'Avg Hours per Order'
                },
                color_continuous_scale='Blues',
                text='TotalProduction'
            )
            
            # Enhanced formatting
            fig.update_traces(
                texttemplate='%{text:,.0f}',
                textposition='outside',
                hovertemplate='<b>%{x}</b><br>Production: %{y:,.0f}<br>Avg Hours/Order: %{marker.color:.1f}<extra></extra>'
            )
            
            fig.update_layout(
                template="plotly_white",
                height=400,
                title=dict(font=dict(size=16)),
                coloraxis_colorbar=dict(title='Avg Hours per Order'),
                hovermode='x'
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Detailed employee data
        with st.expander("Employee Productivity Details", expanded=False):
            st.dataframe(productivity_df)
    else:
        st.info("No productivity data available for the last 30 days")