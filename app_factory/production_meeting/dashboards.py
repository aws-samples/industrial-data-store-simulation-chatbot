"""
Production dashboards for the daily production meeting
"""

import streamlit as st
import pandas as pd
import numpy as np
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
    """Display the quality dashboard with improved product-level metrics"""
    st.header("⚠️ Quality Overview")
    
    # Get quality data (looking at a 30-day window to ensure we have data)
    quality_data = db_manager.get_quality_summary(days_back=1, range_days=30)
    
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
        
        # Add timeframe clarification
        st.caption("Data shown represents the last 30 days of quality inspections")
        
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
        
        # Product-level quality metrics - IMPROVED VISUALIZATION
        st.subheader("Product-level Quality Performance")
        
        # Sort products by defect rate (descending) to focus on problem areas
        product_quality = quality_data.sort_values('AvgDefectRate', ascending=False)
        
        # Calculate first pass yield for each product
        product_quality['FirstPassYield'] = (product_quality['PassCount'] / product_quality['InspectionCount'] * 100).round(1)
        
        # Create a simpler, more actionable visualization
        col1, col2 = st.columns([3, 2])
        
        with col1:
            # Top 10 products by defect rate
            top_products = product_quality.head(10)
            
            # Create a horizontal bar chart for defect rates
            fig = px.bar(
                top_products,
                y='ProductName',
                x='AvgDefectRate',
                orientation='h',
                color='AvgDefectRate',
                color_continuous_scale='Reds',
                title='Top 10 Products by Defect Rate',
                labels={
                    'AvgDefectRate': 'Defect Rate (%)',
                    'ProductName': 'Product'
                }
            )
            
            # Add a target line
            fig.add_shape(
                type="line",
                x0=3,  # Target defect rate
                y0=-0.5,
                x1=3,
                y1=len(top_products)-0.5,
                line=dict(color="green", width=2, dash="dash"),
            )
            
            fig.add_annotation(
                x=3,
                y=len(top_products)/2,
                text="Target",
                showarrow=False,
                xanchor="left",
                yanchor="middle"
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Quality metrics table with visual indicators
            st.subheader("Quality Performance")
            
            # Sort by a combination of metrics to highlight overall problematic products
            quality_score = (product_quality['AvgDefectRate'] * 2) - product_quality['FirstPassYield'] / 100
            product_quality['QualityScore'] = quality_score
            
            # Top 10 products with quality issues
            problem_products = product_quality.sort_values('QualityScore', ascending=False).head(8)
            
            # Create a styled dataframe
            metrics_table = pd.DataFrame({
                'Product': problem_products['ProductName'],
                'Category': problem_products['ProductCategory'],
                'Defect Rate': problem_products['AvgDefectRate'].round(1).astype(str) + '%',
                'First Pass': problem_products['FirstPassYield'].round(1).astype(str) + '%',
                'Inspections': problem_products['InspectionCount']
            })
            
            # Add emoji indicators based on defect rate
            def add_indicator(value):
                try:
                    rate = float(value.strip('%'))
                    if rate > 5:
                        return f"🔴 {value}"
                    elif rate > 3:
                        return f"🟠 {value}"
                    else:
                        return f"🟢 {value}"
                except:
                    return value
            
            metrics_table['Defect Rate'] = metrics_table['Defect Rate'].apply(add_indicator)
            
            st.dataframe(metrics_table, use_container_width=True)
        
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

def add_root_cause_analysis():
    """Add root cause analysis based on actual defect data from the database"""
    st.header("🔍 Root Cause Analysis")
    
    # Get defect types from database for selection
    defect_query = """
    SELECT 
        d.DefectType,
        COUNT(d.DefectID) as DefectCount
    FROM 
        Defects d
    JOIN 
        QualityControl qc ON d.CheckID = qc.CheckID
    WHERE 
        qc.Date >= date('now', '-30 day')
    GROUP BY 
        d.DefectType
    ORDER BY 
        DefectCount DESC
    LIMIT 15
    """
    
    result = db_manager.execute_query(defect_query)
    
    if result["success"] and result["row_count"] > 0:
        defect_df = pd.DataFrame(result["rows"])
        
        # Let user select defect type to analyze
        selected_defect = st.selectbox(
            "Select defect type to analyze:",
            options=defect_df['DefectType'].tolist(),
            format_func=lambda x: f"{x} ({defect_df[defect_df['DefectType']==x]['DefectCount'].values[0]} occurrences)"
        )
        
        if st.button("Run Root Cause Analysis"):
            with st.spinner("Analyzing patterns..."):
                # Get detailed data on the selected defect type
                detail_query = f"""
                SELECT 
                    d.DefectType,
                    d.Severity,
                    d.Location,
                    d.RootCause,
                    d.ActionTaken,
                    p.Name as ProductName,
                    p.Category as ProductCategory,
                    wc.Name as WorkCenterName,
                    m.Name as MachineName,
                    m.Type as MachineType,
                    e.Name as EmployeeName,
                    e.Role as EmployeeRole
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
                JOIN 
                    Machines m ON wo.MachineID = m.MachineID
                JOIN 
                    Employees e ON wo.EmployeeID = e.EmployeeID
                WHERE 
                    d.DefectType = '{selected_defect}'
                    AND qc.Date >= date('now', '-30 day')
                """
                
                detail_result = db_manager.execute_query(detail_query)
                
                if detail_result["success"] and detail_result["row_count"] > 0:
                    detail_df = pd.DataFrame(detail_result["rows"])
                    
                    # Analyze patterns in the data
                    
                    # Product distribution
                    product_counts = detail_df['ProductName'].value_counts().reset_index()
                    product_counts.columns = ['ProductName', 'Count']
                    
                    # Machine distribution
                    machine_counts = detail_df['MachineName'].value_counts().reset_index()
                    machine_counts.columns = ['MachineName', 'Count']
                    
                    # Root cause distribution
                    cause_counts = detail_df['RootCause'].value_counts().reset_index()
                    cause_counts.columns = ['RootCause', 'Count']
                    
                    # Location distribution
                    location_counts = detail_df['Location'].value_counts().reset_index()
                    location_counts.columns = ['Location', 'Count']
                    
                    # Display analysis results
                    st.write(f"### Root Cause Analysis: {selected_defect}")
                    
                    # Key metrics
                    st.write(f"**Total occurrences**: {len(detail_df)}")
                    st.write(f"**Average severity**: {detail_df['Severity'].mean():.1f} / 5")
                    
                    # Create columns for distribution charts
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # Product distribution
                        fig1 = px.bar(
                            product_counts.head(5), 
                            x='ProductName', 
                            y='Count',
                            title='Top Products with this Defect'
                        )
                        st.plotly_chart(fig1, use_container_width=True)
                        
                        # Root cause distribution
                        fig3 = px.pie(
                            cause_counts, 
                            values='Count', 
                            names='RootCause',
                            title='Root Causes'
                        )
                        st.plotly_chart(fig3, use_container_width=True)
                    
                    with col2:
                        # Machine distribution
                        fig2 = px.bar(
                            machine_counts.head(5), 
                            x='MachineName', 
                            y='Count',
                            title='Top Machines with this Defect'
                        )
                        st.plotly_chart(fig2, use_container_width=True)
                        
                        # Location distribution
                        fig4 = px.pie(
                            location_counts, 
                            values='Count', 
                            names='Location',
                            title='Defect Locations'
                        )
                        st.plotly_chart(fig4, use_container_width=True)
                    
                    # Identify correlations
                    st.write("### Key Findings")
                    
                    # Report primary product affected
                    if not product_counts.empty:
                        primary_product = product_counts.iloc[0]['ProductName']
                        product_percent = product_counts.iloc[0]['Count'] / product_counts['Count'].sum() * 100
                        st.info(f"**Primary Product**: {primary_product} accounts for {product_percent:.1f}% of these defects")
                    
                    # Report primary machine affected
                    if not machine_counts.empty:
                        primary_machine = machine_counts.iloc[0]['MachineName']
                        machine_percent = machine_counts.iloc[0]['Count'] / machine_counts['Count'].sum() * 100
                        st.info(f"**Primary Machine**: {primary_machine} accounts for {machine_percent:.1f}% of these defects")
                    
                    # Report primary root cause
                    if not cause_counts.empty:
                        primary_cause = cause_counts.iloc[0]['RootCause']
                        cause_percent = cause_counts.iloc[0]['Count'] / cause_counts['Count'].sum() * 100
                        st.info(f"**Primary Root Cause**: {primary_cause} accounts for {cause_percent:.1f}% of these defects")
                    
                    # Get actions taken
                    actions = detail_df['ActionTaken'].value_counts().reset_index()
                    actions.columns = ['Action', 'Count']
                    
                    st.write("### Recommended Actions")
                    
                    # Recommend actions based on data patterns
                    if not actions.empty:
                        st.write("**Based on effective actions taken so far:**")
                        
                        for i, row in actions.head(3).iterrows():
                            effectiveness = row['Count'] / actions['Count'].sum() * 100
                            st.write(f"- **{row['Action']}** (Used in {effectiveness:.1f}% of cases)")
                    
                    # Check for machine maintenance correlation
                    maintenance_query = f"""
                    SELECT 
                        julianday(m.LastMaintenanceDate) - julianday(qc.Date) as DaysSinceMaintenance
                    FROM 
                        Defects d
                    JOIN 
                        QualityControl qc ON d.CheckID = qc.CheckID
                    JOIN 
                        WorkOrders wo ON qc.OrderID = wo.OrderID
                    JOIN 
                        Machines m ON wo.MachineID = m.MachineID
                    WHERE 
                        d.DefectType = '{selected_defect}'
                        AND qc.Date >= date('now', '-30 day')
                    """
                    
                    maintenance_result = db_manager.execute_query(maintenance_query)
                    
                    if maintenance_result["success"] and maintenance_result["row_count"] > 0:
                        maintenance_df = pd.DataFrame(maintenance_result["rows"])
                        
                        avg_days = maintenance_df['DaysSinceMaintenance'].mean()
                        
                        if avg_days > 14:  # If average is more than 2 weeks
                            st.warning(f"**Maintenance Correlation**: Defects occur on average {avg_days:.1f} days after maintenance. Consider reviewing maintenance frequency.")
                else:
                    st.error("Error retrieving defect details")
    else:
        st.info("No defect data available for analysis")

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
        
        # If we have multiple categories, show the bar chart
        if len(category_alerts) > 1:
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
            
            # Force y-axis to use integers only
            fig.update_yaxes(dtick=1, tick0=0)
            
            # Add data labels on top of bars
            fig.update_traces(texttemplate='%{y}', textposition='outside')
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            # For single category or no categories, display a more informative alternative
            cols = st.columns(2)
            
            # First column: Show total items below reorder point
            with cols[0]:
                if not category_alerts.empty:
                    category = category_alerts['Category'].iloc[0]
                    items_count = int(category_alerts['ItemCount'].iloc[0])
                    total_shortage = int(category_alerts['TotalShortage'].iloc[0])
                    
                    st.metric(
                        f"Items Below Reorder ({category})",
                        f"{items_count}",
                        delta=None,
                        delta_color="inverse"
                    )
                    
                    # Add a small gauge or progress visualization
                    st.markdown(f"**Total Shortage Amount: {total_shortage}**")
                    st.progress(min(1.0, total_shortage / 100))  # Scale appropriately
                else:
                    st.metric("Items Below Reorder", "0", delta=None)
            
            # Second column: Show category breakdown if there's at least one category
            with cols[1]:
                if not category_alerts.empty:
                    st.markdown("### Shortage by Category")
                    for _, row in category_alerts.iterrows():
                        st.markdown(f"**{row['Category']}**: {int(row['ItemCount'])} items, {int(row['TotalShortage'])} units short")
                else:
                    st.success("No inventory shortages detected!")
        
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
        
        # Force y-axis to use integers only
        fig.update_yaxes(dtick=10, tick0=0)
        
        # Add data labels on top of bars
        fig.update_traces(texttemplate='%{y}', textposition='outside')
        
        # Adjust layout for better readability
        fig.update_layout(
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
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

def add_process_flow_visualization():
    """Add an interactive view of the production process flow with bottlenecks highlighted based on real data"""
    st.header("🔄 Production Flow Analysis")
    
    # Query work centers from database
    query = """
    SELECT 
        wc.Name, 
        wc.Capacity, 
        wc.CapacityUOM,
        COUNT(m.MachineID) as MachineCount,
        AVG(m.EfficiencyFactor) * 100 as AvgEfficiency,
        SUM(CASE WHEN m.Status = 'running' THEN 1 ELSE 0 END) * 1.0 / COUNT(m.MachineID) as AvailabilityRate
    FROM 
        WorkCenters wc
    JOIN 
        Machines m ON wc.WorkCenterID = m.WorkCenterID
    GROUP BY 
        wc.Name, wc.Capacity, wc.CapacityUOM
    ORDER BY 
        wc.Name
    """
    
    result = db_manager.execute_query(query)
    
    if result["success"]:
        process_df = pd.DataFrame(result["rows"])
        
        # Calculate utilization based on current work orders
        utilization_query = """
        SELECT 
            wc.Name as WorkCenterName,
            COUNT(wo.OrderID) as ActiveOrders,
            SUM(wo.Quantity) as TotalQuantity,
            AVG(julianday(wo.PlannedEndTime) - julianday(wo.PlannedStartTime)) as AvgDuration
        FROM 
            WorkOrders wo
        JOIN 
            WorkCenters wc ON wo.WorkCenterID = wc.WorkCenterID
        WHERE 
            wo.Status IN ('in_progress', 'scheduled')
        GROUP BY 
            wc.Name
        """
        
        util_result = db_manager.execute_query(utilization_query)
        
        if util_result["success"]:
            utilization_df = pd.DataFrame(util_result["rows"])
            
            # Merge with process data
            process_df = process_df.merge(utilization_df, left_on='Name', right_on='WorkCenterName', how='left')
            
            # Fill NAs for work centers with no active orders
            process_df['ActiveOrders'] = process_df['ActiveOrders'].fillna(0)
            process_df['TotalQuantity'] = process_df['TotalQuantity'].fillna(0)
            
            # Calculate utilization - actual method would depend on your specific business logic
            # This is a simplified version
            process_df['Utilization'] = (process_df['ActiveOrders'] / process_df['Capacity']).clip(0, 1)
            
            # Categorize bottlenecks
            process_df['Status'] = 'normal'
            process_df.loc[process_df['Utilization'] > 0.7, 'Status'] = 'warning'
            process_df.loc[process_df['Utilization'] > 0.85, 'Status'] = 'bottleneck'
            
            # Identify the constraint (Theory of Constraints)
            if not process_df.empty:
                bottleneck_row = process_df.loc[process_df['Utilization'].idxmax()]
                bottleneck_name = bottleneck_row['Name']
                bottleneck_utilization = bottleneck_row['Utilization']
                
                st.write(f"### Current System Constraint: {bottleneck_name} (Utilization: {bottleneck_utilization*100:.1f}%)")
                
                # Horizontal utilization chart
                fig = px.bar(process_df, y='Name', x='Utilization', orientation='h',
                            color='Status', color_discrete_map={'normal': 'green', 'warning': 'orange', 'bottleneck': 'red'},
                            title='Process Utilization',
                            labels={'Name': 'Work Center', 'Utilization': 'Utilization Rate'},
                            range_x=[0, 1])
                
                # Add target line
                fig.add_shape(
                    type="line",
                    x0=0.85,
                    y0=-0.5,
                    x1=0.85, 
                    y1=len(process_df) - 0.5,
                    line=dict(color="red", width=2, dash="dash"),
                )
                
                fig.add_annotation(
                    x=0.85,
                    y=len(process_df) / 2,
                    text="Bottleneck<br>Threshold",
                    showarrow=False,
                    xanchor="left",
                    yanchor="middle"
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Get active work orders for the bottleneck
                bottleneck_query = f"""
                SELECT 
                    p.Name as ProductName,
                    wo.Quantity,
                    wo.PlannedStartTime,
                    wo.PlannedEndTime,
                    wo.Status,
                    wo.Priority
                FROM 
                    WorkOrders wo
                JOIN 
                    WorkCenters wc ON wo.WorkCenterID = wc.WorkCenterID
                JOIN 
                    Products p ON wo.ProductID = p.ProductID
                WHERE 
                    wc.Name = '{bottleneck_name}'
                    AND wo.Status IN ('in_progress', 'scheduled')
                ORDER BY 
                    wo.Priority DESC, wo.PlannedStartTime
                LIMIT 5
                """
                
                bottleneck_result = db_manager.execute_query(bottleneck_query)
                
                if bottleneck_result["success"] and bottleneck_result["row_count"] > 0:
                    st.subheader(f"Active Orders at {bottleneck_name}")
                    st.dataframe(pd.DataFrame(bottleneck_result["rows"]))
                    
                # Get machine details for bottleneck
                machines_query = f"""
                SELECT 
                    m.Name as MachineName,
                    m.Status,
                    m.EfficiencyFactor * 100 as Efficiency,
                    m.NextMaintenanceDate
                FROM 
                    Machines m
                JOIN 
                    WorkCenters wc ON m.WorkCenterID = wc.WorkCenterID
                WHERE 
                    wc.Name = '{bottleneck_name}'
                """
                
                machines_result = db_manager.execute_query(machines_query)
                
                if machines_result["success"] and machines_result["row_count"] > 0:
                    st.subheader(f"Machines in {bottleneck_name}")
                    st.dataframe(pd.DataFrame(machines_result["rows"]))
                    
                # Show optimization recommendations
                st.subheader("Bottleneck Analysis")
                
                st.write(f"**Primary constraint**: {bottleneck_name} (Utilization: {bottleneck_utilization*100:.1f}%)")
                
                # Query downtime data to identify potential improvement areas
                downtime_query = f"""
                SELECT 
                    d.Reason,
                    COUNT(d.DowntimeID) as EventCount,
                    AVG(d.Duration) as AvgDuration,
                    SUM(d.Duration) as TotalMinutes
                FROM 
                    Downtimes d
                JOIN 
                    Machines m ON d.MachineID = m.MachineID
                JOIN 
                    WorkCenters wc ON m.WorkCenterID = wc.WorkCenterID
                WHERE 
                    wc.Name = '{bottleneck_name}'
                    AND d.StartTime >= date('now', '-30 day')
                GROUP BY 
                    d.Reason
                ORDER BY 
                    TotalMinutes DESC
                LIMIT 3
                """
                
                downtime_result = db_manager.execute_query(downtime_query)
                
                if downtime_result["success"] and downtime_result["row_count"] > 0:
                    downtime_df = pd.DataFrame(downtime_result["rows"])
                    
                    st.write("**Top downtime reasons:**")
                    
                    for _, row in downtime_df.iterrows():
                        st.write(f"- **{row['Reason']}**: {row['EventCount']} events, avg {row['AvgDuration']:.1f} min each")
                        
                    # Generate optimization recommendations based on actual data
                    st.write("**Optimization options:**")
                    
                    # If maintenance is a top reason
                    if 'Scheduled Maintenance' in downtime_df['Reason'].values or 'Equipment Failure' in downtime_df['Reason'].values:
                        st.info("**Maintenance Optimization**: Review maintenance schedule to minimize impact on production")
                    
                    # If setup/changeover is a top reason
                    if 'Setup/Changeover' in downtime_df['Reason'].values:
                        st.info("**Setup Reduction**: Implement SMED principles to reduce changeover time")
                    
                    # General recommendations
                    st.info("**Capacity Addition**: Consider overtime or additional shift at the bottleneck")
            else:
                st.warning("No process data available")
        else:
            st.error("Error retrieving utilization data")
    else:
        st.error("Error retrieving process data")

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
    tabs = st.tabs([
        "Production", 
        "Equipment", 
        "Quality", 
        "Root Cause Analysis", 
        "Inventory", 
        "Productivity", 
        "Process Flow", 
        "Scenario Comparison", 
        "Weekly"
    ])
    
    with tabs[0]:
        production_summary_dashboard()
    
    with tabs[1]:
        equipment_status_dashboard()
    
    with tabs[2]:
        quality_dashboard()
    
    with tabs[3]:
        add_root_cause_analysis()
    
    with tabs[4]:
        inventory_dashboard()
    
    with tabs[5]:
        productivity_dashboard()
    
    with tabs[6]:
        add_process_flow_visualization()
    
    with tabs[7]:
        add_scenario_comparison()
    
    with tabs[8]:
        weekly_overview_dashboard()