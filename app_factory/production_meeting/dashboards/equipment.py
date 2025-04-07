"""
Equipment dashboard functionality
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from shared.database import DatabaseManager
from production_meeting.utils.interactive_explanations import metric_with_explanation

# Initialize database manager
db_manager = DatabaseManager()

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
