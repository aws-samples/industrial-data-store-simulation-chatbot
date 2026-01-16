"""
Equipment dashboard functionality with downtime impact and maintenance effectiveness
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

from app_factory.shared.database import DatabaseManager
from app_factory.shared.db_utils import days_ago, today, date_diff_days

# Initialize database manager
db_manager = DatabaseManager()

# Import shared color configuration
from .color_config import (
    DEFAULT_COLORS, STATUS_COLORS, get_performance_color,
    get_status_color_map, apply_theme_compatibility
)

def create_enhanced_equipment_gauge(availability_pct, title="Machine Availability"):
    """Create enhanced gauge for equipment availability - theme compatible"""
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=availability_pct,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': title, 'font': {'size': 16}},
        delta={'reference': 85, 'increasing': {'color': "#00CC96"}, 'decreasing': {'color': "#EF553B"}},
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 1},
            'bar': {'color': get_performance_color(availability_pct), 'thickness': 0.3},
            'borderwidth': 1,
            'steps': [
                {'range': [0, 50], 'color': 'rgba(239, 85, 59, 0.3)'},   # Red with transparency
                {'range': [50, 80], 'color': 'rgba(255, 161, 90, 0.3)'}, # Orange with transparency
                {'range': [80, 100], 'color': 'rgba(0, 204, 150, 0.3)'} # Green with transparency
            ],
            'threshold': {
                'line': {'color': "#EF553B", 'width': 4},
                'thickness': 0.75,
                'value': 85
            }
        }
    ))

    fig.update_layout(
        height=350,
        margin=dict(l=20, r=20, t=60, b=20)
    )

    return fig

def equipment_status_dashboard():
    """Display the enhanced equipment status dashboard"""
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
            
            # Create enhanced gauge chart for availability
            fig = create_enhanced_equipment_gauge(
                availability_pct=availability,
                title="Overall Machine Availability"
            )
            
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
                color_discrete_map=get_status_color_map(['Running', 'Idle', 'Maintenance', 'Breakdown']),
                hole=0.4  # Donut chart for better readability
            )
            
            # Enhanced formatting
            fig.update_traces(
                textposition='inside',
                textinfo='percent+label',
                textfont_size=12
            )
            
            fig.update_layout(
                template="plotly",
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
            # Machine type breakdown with efficiency
            st.subheader("Machine Performance by Type")
            
            fig = px.bar(
                machine_status,
                x='MachineType',
                y='AvgEfficiency',
                title='Average Efficiency by Machine Type',
                labels={'AvgEfficiency': 'Efficiency (%)', 'MachineType': 'Machine Type'},
                color='AvgEfficiency',
                color_continuous_scale='RdYlGn',
                text='AvgEfficiency'
            )
            
            # Enhanced formatting
            fig.update_traces(
                texttemplate='%{text:.1f}%',
                textposition='outside'
            )
            
            fig.update_layout(
                template="plotly",
                height=400,
                title=dict(font=dict(size=16)),
                coloraxis_colorbar=dict(title='Efficiency (%)'),
                xaxis=dict(tickangle=-45),
                hovermode='x'
            )
            
            # Add target line at 85%
            fig.add_shape(
                type="line",
                x0=-0.5,
                x1=len(machine_status)-0.5,
                y0=85,
                y1=85,
                line=dict(color="red", width=2, dash="dash")
            )
            
            fig.add_annotation(
                x=len(machine_status)/2,
                y=87,
                text="Target: 85%",
                showarrow=False,
                font=dict(color="red", size=12)
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Enhanced stacked bar chart of machine status by type
            fig = px.bar(
                machine_status,
                x='MachineType',
                y=['Running', 'Idle', 'Maintenance', 'Breakdown'],
                title='Machine Status Distribution by Type',
                labels={'value': 'Number of Machines', 'variable': 'Status', 'MachineType': 'Machine Type'},
                color_discrete_map=get_status_color_map(['Running', 'Idle', 'Maintenance', 'Breakdown'])
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
            
            # Add data labels for better readability
            fig.update_traces(
                texttemplate='%{y}',
                textposition='inside'
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No machine status data available")
    
    # NEW: Downtime Impact Analysis
    st.subheader("🔍 Downtime Impact Analysis")
    
    # Get downtime data with production impact
    seven_days_ago = days_ago(7)

    downtime_query = """
    SELECT
        m.Name as MachineName,
        m.Type as MachineType,
        d.Reason as DowntimeReason,
        d.Category as DowntimeCategory,
        d.Duration as DurationMinutes,
        m.NominalCapacity as UnitsPerHour,
        (d.Duration / 60.0 * m.NominalCapacity) as EstimatedLostUnits
    FROM
        Downtimes d
    JOIN
        Machines m ON d.MachineID = m.MachineID
    WHERE
        d.StartTime >= :seven_days_ago
    ORDER BY
        EstimatedLostUnits DESC
    LIMIT 10
    """

    result = db_manager.execute_query(downtime_query, {"seven_days_ago": seven_days_ago})
    
    if result["success"] and result["row_count"] > 0:
        downtime_df = pd.DataFrame(result["rows"])
        
        # Create visualization of production impact
        fig = px.bar(
            downtime_df,
            x='MachineName',
            y='EstimatedLostUnits',
            color='DowntimeCategory',
            title='Estimated Production Impact of Downtime (Last 7 Days)',
            labels={
                'EstimatedLostUnits': 'Estimated Lost Units',
                'MachineName': 'Machine',
                'DowntimeCategory': 'Downtime Category'
            },
            color_discrete_map={
                'planned': 'blue',
                'unplanned': 'red'
            },
            hover_data=['DurationMinutes', 'DowntimeReason', 'MachineType']
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Calculate and display total impact
        total_lost_units = downtime_df['EstimatedLostUnits'].sum()
        total_downtime_minutes = downtime_df['DurationMinutes'].sum()
        
        cols = st.columns(2)
        cols[0].metric("Total Lost Production", f"{int(total_lost_units):,} units")
        cols[1].metric("Total Downtime", f"{total_downtime_minutes:.0f} minutes")
        
        # Show most impactful downtime reasons
        reason_impact = downtime_df.groupby('DowntimeReason').agg({
            'EstimatedLostUnits': 'sum',
            'DurationMinutes': 'sum'
        }).reset_index().sort_values('EstimatedLostUnits', ascending=False)
        
        st.subheader("Most Impactful Downtime Reasons")
        
        # Create Pareto chart of downtime reasons
        fig = go.Figure()
        
        # Add bars for lost units
        fig.add_trace(go.Bar(
            x=reason_impact['DowntimeReason'],
            y=reason_impact['EstimatedLostUnits'],
            name='Lost Units'
        ))
        
        # Add cumulative percentage line
        reason_impact['CumulativeLostUnits'] = reason_impact['EstimatedLostUnits'].cumsum()
        reason_impact['CumulativePercentage'] = reason_impact['CumulativeLostUnits'] / reason_impact['EstimatedLostUnits'].sum() * 100
        
        fig.add_trace(go.Scatter(
            x=reason_impact['DowntimeReason'],
            y=reason_impact['CumulativePercentage'],
            name='Cumulative %',
            mode='lines+markers',
            line=dict(color='red', width=2),
            yaxis='y2'
        ))
        
        # Update layout with second y-axis
        fig.update_layout(
            title='Pareto Analysis of Downtime Impact',
            yaxis=dict(title='Lost Units'),
            yaxis2=dict(
                title='Cumulative %',
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
        
        # Add 80% line (Pareto principle)
        fig.add_shape(
            type="line",
            x0=-0.5,
            x1=len(reason_impact)-0.5,
            y0=80,
            y1=80,
            line=dict(color="gray", width=1, dash="dash"),
            yref='y2'
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No downtime data available for impact analysis")
        
    # NEW: Maintenance Effectiveness Analysis
    st.subheader("🛠️ Maintenance Effectiveness")

    # Get data on machine breakdowns after maintenance
    # Calculate DaysSinceMaintenance in Python instead of using julianday
    today_str = today()

    maintenance_query = """
    SELECT
        m.Name as MachineName,
        m.Type as MachineType,
        MAX(m.LastMaintenanceDate) as LastMaintenance,
        COUNT(d.DowntimeID) as BreakdownsAfterMaintenance
    FROM
        Machines m
    LEFT JOIN
        Downtimes d ON m.MachineID = d.MachineID AND
                        d.StartTime > m.LastMaintenanceDate AND
                        d.Category = 'unplanned'
    GROUP BY
        m.MachineID, m.Name, m.Type
    HAVING
        LastMaintenance IS NOT NULL
    ORDER BY
        BreakdownsAfterMaintenance DESC
    LIMIT 10
    """

    result = db_manager.execute_query(maintenance_query)

    if result["success"] and result["row_count"] > 0:
        maintenance_df = pd.DataFrame(result["rows"])
        # Calculate DaysSinceMaintenance in Python (replaces julianday)
        maintenance_df['DaysSinceMaintenance'] = maintenance_df['LastMaintenance'].apply(
            lambda x: date_diff_days(today_str, x[:10]) if x else 0
        )
        
        # Create visualization of maintenance effectiveness
        fig = px.scatter(
            maintenance_df,
            x='DaysSinceMaintenance',
            y='BreakdownsAfterMaintenance',
            color='MachineType',
            size='BreakdownsAfterMaintenance',
            hover_data=['MachineName', 'LastMaintenance'],
            title='Machine Reliability After Maintenance',
            labels={
                'DaysSinceMaintenance': 'Days Since Maintenance',
                'BreakdownsAfterMaintenance': 'Number of Breakdowns',
                'MachineType': 'Machine Type'
            }
        )
        
        # Add reference quadrants
        fig.add_shape(
            type="rect",
            x0=0, y0=0,
            x1=30, y1=1,
            line=dict(color="green", width=1),
            fillcolor="rgba(0,255,0,0.1)"
        )
        
        fig.add_shape(
            type="rect",
            x0=30, y0=0,
            x1=90, y1=1,
            line=dict(color="yellow", width=1),
            fillcolor="rgba(255,255,0,0.1)"
        )
        
        fig.add_shape(
            type="rect",
            x0=0, y0=1,
            x1=90, y1=10,
            line=dict(color="red", width=1),
            fillcolor="rgba(255,0,0,0.1)"
        )
        
        # Add annotations
        fig.add_annotation(
            x=15, y=0.5,
            text="Good: Recent Maintenance, Few Breakdowns",
            showarrow=False,
            font=dict(size=10)
        )
        
        fig.add_annotation(
            x=60, y=0.5,
            text="Warning: Aging Maintenance, Few Breakdowns",
            showarrow=False,
            font=dict(size=10)
        )
        
        fig.add_annotation(
            x=45, y=5,
            text="Critical: Multiple Breakdowns After Maintenance",
            showarrow=False,
            font=dict(size=10)
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Show machines with concerning maintenance effectiveness
        st.subheader("Machines Needing Maintenance Improvement")
        
        concern_machines = maintenance_df[maintenance_df['BreakdownsAfterMaintenance'] > 1].sort_values(
            'BreakdownsAfterMaintenance', ascending=False
        )
        
        if not concern_machines.empty:
            for i, row in concern_machines.head(5).iterrows():
                st.markdown(f"""
                ⚠️ **{row['MachineName']}** ({row['MachineType']})  
                **Breakdowns after maintenance:** {int(row['BreakdownsAfterMaintenance'])}  
                **Last maintenance:** {row['LastMaintenance']} ({row['DaysSinceMaintenance']:.1f} days ago)
                
                **Recommendation:** Review maintenance procedures for this machine type
                """)
                st.markdown("---")
        else:
            st.success("All machines showing good maintenance effectiveness!")
    else:
        st.info("No maintenance effectiveness data available")
    
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
