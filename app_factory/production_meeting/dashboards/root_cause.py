"""
RCA dashboard functionality
"""

import streamlit as st
import pandas as pd
import plotly.express as px

from shared.database import DatabaseManager

# Initialize database manager
db_manager = DatabaseManager()

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
