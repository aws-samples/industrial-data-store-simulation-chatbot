"""
Production dashboards for the daily production meeting
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

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

def equipment_status_dashboard():
    """Display the equipment status dashboard"""
    st.header("🔧 Equipment Status")
    
    # Get machine status summary
    machine_status = db_manager.get_machine_status_summary()
    
    if not machine_status.empty:
        # Summary metrics for machines
        col1, col2 = st.columns(2)
        
        with col1:
            # Overall equipment status
            total_machines = machine_status['TotalMachines'].sum()
            running_machines = machine_status['Running'].sum()
            idle_machines = machine_status['Idle'].sum()
            maintenance_machines = machine_status['Maintenance'].sum()
            breakdown_machines = machine_status['Breakdown'].sum()
            
            availability = running_machines / total_machines * 100 if total_machines > 0 else 0
            
            # Create gauge chart for availability
            fig = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = availability,
                domain = {'x': [0, 1], 'y': [0, 1]},
                title = {'text': "Machine Availability"},
                gauge = {
                    'axis': {'range': [0, 100]},
                    'bar': {'color': "green"},
                    'steps': [
                        {'range': [0, 50], 'color': "red"},
                        {'range': [50, 80], 'color': "orange"},
                        {'range': [80, 100], 'color': "lightgreen"}
                    ],
                    'threshold': {
                        'line': {'color': "black", 'width': 4},
                        'thickness': 0.75,
                        'value': 85
                    }
                }
            ))
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Status breakdown
            status_data = pd.DataFrame({
                'Status': ['Running', 'Idle', 'Maintenance', 'Breakdown'],
                'Count': [running_machines, idle_machines, maintenance_machines, breakdown_machines]
            })
            
            fig = px.pie(
                status_data,
                values='Count',
                names='Status',
                title='Machine Status Distribution',
                color='Status',
                color_discrete_map={
                    'Running': 'green',
                    'Idle': 'blue',
                    'Maintenance': 'orange',
                    'Breakdown': 'red'
                }
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Machine type breakdown with efficiency
            st.subheader("Machine Performance by Type")
            
            fig = px.bar(
                machine_status,
                x='MachineType',
                y='AvgEfficiency',
                title='Average Efficiency by Machine Type',
                labels={'AvgEfficiency': 'Efficiency (%)', 'MachineType': 'Machine Type'},
                color='AvgEfficiency',
                color_continuous_scale='RdYlGn'
            )
            fig.update_layout(coloraxis_colorbar=dict(title='Efficiency (%)'))
            st.plotly_chart(fig, use_container_width=True)
            
            # Stacked bar chart of machine status by type
            fig = px.bar(
                machine_status,
                x='MachineType',
                y=['Running', 'Idle', 'Maintenance', 'Breakdown'],
                title='Machine Status by Type',
                labels={'value': 'Number of Machines', 'variable': 'Status', 'MachineType': 'Machine Type'},
                color_discrete_map={
                    'Running': 'green',
                    'Idle': 'blue',
                    'Maintenance': 'orange',
                    'Breakdown': 'red'
                }
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No machine status data available")
    
    # Upcoming maintenance
    st.subheader("Upcoming Maintenance")
    
    # Get machines due for maintenance
    maintenance_data = db_manager.get_upcoming_maintenance(days_ahead=7)
    
    if not maintenance_data.empty:
        # Display machines needing maintenance
        st.write(f"**{len(maintenance_data)} machines scheduled for maintenance in the next 7 days:**")
        
        for i, row in maintenance_data.iterrows():
            days_until = float(row['DaysUntilMaintenance'])
            
            # Create color coding based on urgency
            if days_until <= 1:
                severity = "🔴"  # Red for urgent (today or tomorrow)
            elif days_until <= 3:
                severity = "🟠"  # Orange for approaching
            else:
                severity = "🟢"  # Green for scheduled future maintenance
            
            st.markdown(f"""
            {severity} **{row['MachineName']}** ({row['MachineType']}) in {row['WorkCenterName']}  
            **Due:** {row['MaintenanceDate']} ({days_until:.1f} days)  
            **Last Maintenance:** {row['LastMaintenance']}
            """)
            
            # Add a separator between items
            st.markdown("---")
    else:
        st.success("No machines scheduled for maintenance in the next 7 days")

def quality_dashboard():
    """Display the quality dashboard"""
    st.header("⚠️ Quality Overview")
    
    # Get quality data
    quality_data = db_manager.get_quality_summary(days_back=1)
    
    if not quality_data.empty:
        # Summary metrics
        avg_defect_rate = quality_data['AvgDefectRate'].mean()
        avg_rework_rate = quality_data['AvgReworkRate'].mean()
        avg_yield_rate = quality_data['AvgYieldRate'].mean()
        
        # Display metrics
        metrics_cols = st.columns(3)
        metrics_cols[0].metric("Avg Defect Rate", f"{avg_defect_rate:.2f}%")
        metrics_cols[1].metric("Avg Rework Rate", f"{avg_rework_rate:.2f}%")
        metrics_cols[2].metric("Avg Yield Rate", f"{avg_yield_rate:.2f}%")
        
        # Quality by product category
        st.subheader("Quality by Product Category")
        
        # Group by product category
        category_data = quality_data.groupby('ProductCategory').agg({
            'InspectionCount': 'sum',
            'AvgDefectRate': 'mean',
            'AvgReworkRate': 'mean',
            'AvgYieldRate': 'mean',
            'PassCount': 'sum',
            'FailCount': 'sum',
            'ReworkCount': 'sum'
        }).reset_index()
        
        # Create visualization
        fig = px.bar(
            category_data,
            x='ProductCategory',
            y=['AvgDefectRate', 'AvgReworkRate'],
            barmode='group',
            title='Defect and Rework Rates by Product Category',
            labels={
                'value': 'Rate (%)', 
                'variable': 'Metric', 
                'ProductCategory': 'Product Category'
            }
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Product-level quality metrics
        st.subheader("Product-level Quality Metrics")
        
        # Calculate first-pass yield
        quality_data['FirstPassYield'] = quality_data['PassCount'] / quality_data['InspectionCount'] * 100
        
        # Sort by inspection count
        quality_data_sorted = quality_data.sort_values('InspectionCount', ascending=False)
        
        fig = px.scatter(
            quality_data_sorted,
            x='AvgDefectRate',
            y='FirstPassYield',
            size='InspectionCount',
            color='ProductCategory',
            hover_name='ProductName',
            title='Quality Performance by Product',
            labels={
                'AvgDefectRate': 'Defect Rate (%)',
                'FirstPassYield': 'First Pass Yield (%)',
                'InspectionCount': 'Number of Inspections'
            }
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Detailed quality data
        with st.expander("Detailed Quality Data", expanded=False):
            st.dataframe(quality_data)
        
        # Get top defects from yesterday
        defects_query = """
        SELECT 
            d.DefectType,
            d.Severity,
            COUNT(d.DefectID) as DefectCount,
            SUM(d.Quantity) as TotalQuantity,
            AVG(d.Severity) as AvgSeverity,
            p.Name as ProductName,
            p.Category as ProductCategory
        FROM 
            Defects d
        JOIN 
            QualityControl qc ON d.CheckID = qc.CheckID
        JOIN 
            WorkOrders wo ON qc.OrderID = wo.OrderID
        JOIN 
            Products p ON wo.ProductID = p.ProductID
        WHERE 
            qc.Date >= date('now', '-1 day')
        GROUP BY 
            d.DefectType
        ORDER BY 
            DefectCount DESC
        LIMIT 10
        """
        
        result = db_manager.execute_query(defects_query)
        if result["success"] and result["row_count"] > 0:
            st.subheader("Top Defect Types (Last 24 Hours)")
            
            defects_df = pd.DataFrame(result["rows"])
            
            fig = px.bar(
                defects_df,
                x='DefectType',
                y='DefectCount',
                color='AvgSeverity',
                title='Top Defect Types by Frequency',
                labels={
                    'DefectCount': 'Number of Occurrences',
                    'DefectType': 'Defect Type',
                    'AvgSeverity': 'Avg Severity (1-5)'
                },
                color_continuous_scale='Reds'
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No defect data available for the last 24 hours")
    else:
        st.info("No quality data available for yesterday")

def inventory_dashboard():
    """Display the inventory dashboard"""
    st.header("📦 Inventory Status")
    
    # Get inventory alerts
    inventory_alerts = db_manager.get_inventory_alerts()
    
    if not inventory_alerts.empty:
        # Summary metrics
        total_items_below = len(inventory_alerts)
        critical_items = len(inventory_alerts[inventory_alerts['ShortageAmount'] > inventory_alerts['ReorderLevel'] * 0.5])
        
        # Display metrics
        metrics_cols = st.columns(3)
        metrics_cols[0].metric("Items Below Reorder", total_items_below)
        metrics_cols[1].metric("Critical Shortages", critical_items)
        
        # Calculate average lead time for items below reorder
        avg_lead_time = inventory_alerts['LeadTimeInDays'].mean()
        metrics_cols[2].metric("Avg Lead Time", f"{avg_lead_time:.1f} days")
        
        # Display inventory alerts by category
        st.subheader("Inventory Alerts by Category")
        
        # Group by category
        category_alerts = inventory_alerts.groupby('Category').agg({
            'ItemName': 'count',
            'ShortageAmount': 'sum'
        }).reset_index()
        
        category_alerts.columns = ['Category', 'ItemCount', 'TotalShortage']
        
        fig = px.bar(
            category_alerts,
            x='Category',
            y='ItemCount',
            color='TotalShortage',
            title='Inventory Alerts by Category',
            labels={
                'ItemCount': 'Number of Items',
                'Category': 'Category',
                'TotalShortage': 'Total Shortage'
            },
            color_continuous_scale='Reds'
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Display critical shortage items
        st.subheader("Critical Shortage Items")
        
        # Sort by shortage amount
        critical_items_df = inventory_alerts.sort_values('ShortageAmount', ascending=False).head(10)
        
        fig = px.bar(
            critical_items_df,
            x='ItemName',
            y=['CurrentQuantity', 'ReorderLevel'],
            barmode='group',
            title='Inventory Levels vs. Reorder Points',
            labels={
                'value': 'Quantity',
                'variable': 'Metric', 
                'ItemName': 'Item'
            },
            color_discrete_map={
                'CurrentQuantity': 'red',
                'ReorderLevel': 'blue'
            }
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Detailed inventory alerts
        with st.expander("All Inventory Alerts", expanded=False):
            st.dataframe(inventory_alerts)
    else:
        st.success("No inventory items are below reorder level")

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

# Combined dashboard for weekly overview
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

if __name__ == "__main__":
    # Test individual dashboards
    st.set_page_config(page_title="Dashboard Tests", layout="wide")
    
    # Create tabs for testing each dashboard
    tabs = st.tabs(["Production", "Equipment", "Quality", "Inventory", "Productivity", "Weekly"])
    
    with tabs[0]:
        production_summary_dashboard()
    
    with tabs[1]:
        equipment_status_dashboard()
    
    with tabs[2]:
        quality_dashboard()
    
    with tabs[3]:
        inventory_dashboard()
    
    with tabs[4]:
        productivity_dashboard()
    
    with tabs[5]:
        weekly_overview_dashboard()