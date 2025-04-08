"""
Productivity / personnel dashboard functionality
"""

import streamlit as st
import pandas as pd
import plotly.express as px

from shared.database import DatabaseManager


# Initialize database manager
db_manager = DatabaseManager()

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
            title='Completed Orders by Employee',
            labels={
                'CompletedOrders': 'Number of Orders',
                'EmployeeName': 'Employee',
                'EmployeeRole': 'Role'
            }
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
                title='Production by Employee Role',
                hover_data=['CompletedOrders']
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
                title='Production by Shift',
                labels={
                    'TotalProduction': 'Total Units',
                    'ShiftName': 'Shift',
                    'AvgOrderHours': 'Avg Hours per Order'
                },
                color_continuous_scale='Blues'
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Detailed employee data
        with st.expander("Employee Productivity Details", expanded=False):
            st.dataframe(productivity_df)
    else:
        st.info("No productivity data available for the last 30 days")