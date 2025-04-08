"""
Production summary dashboard functionality
"""

import streamlit as st
import pandas as pd
import plotly.express as px

from shared.database import DatabaseManager

# Initialize database manager
db_manager = DatabaseManager()

def production_summary_dashboard():
    """Display the production summary dashboard"""
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
            completion_rate = (total_actual / total_planned * 100) if total_planned > 0 else 0
            
            # Display metrics
            metrics_cols = st.columns(3)
            metrics_cols[0].metric("Planned Units", f"{int(total_planned):,}")
            metrics_cols[1].metric("Actual Units", f"{int(total_actual):,}")
            metrics_cols[2].metric("Completion Rate", f"{completion_rate:.1f}%")
            
            # Show production by product
            st.subheader("Production by Product")
            
            # Create visualization
            fig = px.bar(
                yesterday_data, 
                x='ProductName', 
                y=['PlannedQuantity', 'ActualProduction'],
                barmode='group',
                title='Planned vs Actual Production',
                labels={'value': 'Units', 'variable': 'Metric', 'ProductName': 'Product'}
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Show detailed data
            with st.expander("Detailed Production Data", expanded=False):
                st.dataframe(yesterday_data)
        else:
            st.info("No production data available for yesterday")
    
    with col2:
        st.subheader("Today's Plan")
        
        # Get current work order status
        work_order_status = db_manager.get_work_order_status()
        
        if not work_order_status.empty:
            # Create status pie chart
            fig = px.pie(
                work_order_status,
                values='OrderCount',
                names='Status',
                title='Work Order Status Distribution',
                color='Status',
                color_discrete_map={
                    'scheduled': 'lightblue',
                    'in_progress': 'orange',
                    'completed': 'green',
                    'cancelled': 'red'
                }
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Add metrics for work orders
            metrics_cols = st.columns(3)
            
            in_progress = work_order_status[work_order_status['Status'] == 'in_progress']['OrderCount'].sum() if 'in_progress' in work_order_status['Status'].values else 0
            
            scheduled = work_order_status[work_order_status['Status'] == 'scheduled']['OrderCount'].sum() if 'scheduled' in work_order_status['Status'].values else 0
            
            total_quantity = work_order_status['TotalQuantity'].sum()
            
            metrics_cols[0].metric("Orders In Progress", f"{int(in_progress):,}")
            metrics_cols[1].metric("Scheduled Orders", f"{int(scheduled):,}")
            metrics_cols[2].metric("Total Planned Units", f"{int(total_quantity):,}")
            
            # Show detailed data
            with st.expander("Work Order Status Details", expanded=False):
                st.dataframe(work_order_status)
        else:
            st.info("No work order data available")
    
    # Production issues/bottlenecks
    st.subheader("⚠️ Production Issues & Bottlenecks")
    
    # Get any downtime events from today and yesterday
    downtime_query = """
    SELECT 
        m.Name as MachineName,
        m.Type as MachineType,
        d.Reason as DowntimeReason,
        d.Category as DowntimeCategory,
        d.StartTime,
        d.EndTime,
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
        
        # Display summary
        st.write(f"**Top downtime events in the last 24 hours:**")
        
        for i, row in enumerate(result["rows"]):
            with st.container():
                st.markdown(f"""
                **Issue {i+1}:** {row['MachineName']} ({row['MachineType']})  
                **Reason:** {row['DowntimeReason']} ({row['DowntimeCategory']})  
                **Duration:** {row['DurationMinutes']} minutes  
                **Description:** {row['Description']}
                """)
                st.markdown("---")
    else:
        st.success("No significant downtime events in the last 24 hours")
