"""
Inventory dashboard
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import datetime, timedelta

from app_factory.shared.database import DatabaseManager
from app_factory.shared.db_utils import days_ago

# Initialize database manager
db_manager = DatabaseManager()

# Import shared color configuration
from .color_config import (
    DEFAULT_COLORS, PRIORITY_COLORS, STATUS_COLORS, apply_theme_compatibility
)

def create_enhanced_inventory_chart(df, x_col, y_cols, title, chart_type='bar'):
    """Create enhanced inventory charts with better formatting"""
    if chart_type == 'bar' and isinstance(y_cols, list):
        fig = px.bar(
            df,
            x=x_col,
            y=y_cols,
            barmode='group',
            title=title,
            color_discrete_sequence=DEFAULT_COLORS
        )
        
        # Add data labels
        fig.update_traces(
            texttemplate='%{y:,.0f}',
            textposition='outside'
        )
        
    elif chart_type == 'horizontal_bar':
        fig = px.bar(
            df,
            y=x_col,
            x=y_cols[0] if isinstance(y_cols, list) else y_cols,
            orientation='h',
            title=title,
            color_discrete_sequence=DEFAULT_COLORS
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

def inventory_dashboard():
    """Display the enhanced inventory dashboard"""
    st.header("📦 Inventory Status")
    
    # Get inventory alerts
    inventory_alerts = db_manager.get_inventory_alerts()
    
    # Get all inventory items for the complete inventory view
    all_inventory_query = """
    SELECT 
        i.ItemID,
        i.Name as ItemName,
        i.Category as Category,
        i.Quantity as CurrentQuantity,
        i.ReorderLevel,
        i.LeadTime as LeadTimeInDays,
        s.Name as SupplierName,
        CASE 
            WHEN i.Quantity < i.ReorderLevel THEN i.ReorderLevel - i.Quantity
            ELSE 0
        END as ShortageAmount,
        CASE 
            WHEN i.Quantity < i.ReorderLevel * 0.5 THEN 'Critical'
            WHEN i.Quantity < i.ReorderLevel THEN 'Low'
            WHEN i.Quantity < i.ReorderLevel * 1.5 THEN 'Adequate'
            ELSE 'Well-Stocked'
        END as StockStatus
    FROM 
        Inventory i
    LEFT JOIN 
        Suppliers s ON i.SupplierID = s.SupplierID
    ORDER BY 
        CASE 
            WHEN i.Quantity < i.ReorderLevel THEN 1
            ELSE 2
        END,
        ShortageAmount DESC
    """
    
    all_inventory_result = db_manager.execute_query(all_inventory_query)
    all_inventory = pd.DataFrame(all_inventory_result["rows"]) if all_inventory_result["success"] else pd.DataFrame()
    
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
        
        # Display critical shortage items
        st.subheader("Critical Shortage Items")
        
        # Sort by shortage amount
        critical_items_df = inventory_alerts.sort_values('ShortageAmount', ascending=False).head(10)
        
        # Create enhanced inventory levels chart
        fig = create_enhanced_inventory_chart(
            df=critical_items_df,
            x_col='ItemName',
            y_cols=['CurrentQuantity', 'ReorderLevel'],
            title='Critical Items: Current vs. Reorder Levels'
        )
        
        # Update colors to be more meaningful
        fig.update_traces(
            marker_color=[DEFAULT_COLORS[0], DEFAULT_COLORS[2]],  # Red for current, Blue for reorder
            selector=dict(type='bar')
        )
        
        # Enhanced formatting
        fig.update_layout(
            xaxis=dict(tickangle=-45, title='Inventory Items'),
            yaxis=dict(title='Quantity', dtick=max(1, critical_items_df[['CurrentQuantity', 'ReorderLevel']].max().max() // 10)),
            hovermode='x unified'
        )
        
        # Add shortage indicators
        for i, row in critical_items_df.iterrows():
            if row['CurrentQuantity'] < row['ReorderLevel']:
                shortage = row['ReorderLevel'] - row['CurrentQuantity']
                fig.add_annotation(
                    x=row['ItemName'],
                    y=row['CurrentQuantity'] + shortage/2,
                    text=f"Short: {shortage:.0f}",
                    showarrow=True,
                    arrowhead=2,
                    arrowcolor="red",
                    font=dict(color="red", size=10)
                )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Changed from "All Inventory Alerts" to "All Inventory Levels"
        with st.expander("All Inventory Levels", expanded=False):
            # Use the complete inventory data instead of just alerts
            if not all_inventory.empty:
                st.dataframe(all_inventory)
            else:
                st.info("No inventory data available")
            
        st.subheader("Days of Supply Analysis")
        
        # Get consumption data to calculate days of supply
        thirty_days_ago = days_ago(30)

        consumption_query = """
        SELECT
            i.ItemID,
            i.Name as ItemName,
            i.Category as ItemCategory,
            i.Quantity as CurrentQuantity,
            i.ReorderLevel,
            AVG(mc.ActualQuantity) as AvgDailyConsumption
        FROM
            Inventory i
        LEFT JOIN
            MaterialConsumption mc ON i.ItemID = mc.ItemID
        WHERE
            i.Quantity < i.ReorderLevel
            AND mc.ConsumptionDate >= :thirty_days_ago
        GROUP BY
            i.ItemID, i.Name, i.Category, i.Quantity, i.ReorderLevel
        ORDER BY
            (i.Quantity / CASE WHEN AVG(mc.ActualQuantity) > 0 THEN AVG(mc.ActualQuantity) ELSE 999999 END) ASC
        LIMIT 10
        """

        result = db_manager.execute_query(consumption_query, {"thirty_days_ago": thirty_days_ago})
        
        if result["success"] and result["row_count"] > 0:
            consumption_df = pd.DataFrame(result["rows"])
            
            # Calculate days of supply
            consumption_df['DaysOfSupply'] = np.where(
                consumption_df['AvgDailyConsumption'] > 0,
                consumption_df['CurrentQuantity'] / consumption_df['AvgDailyConsumption'],
                float('inf')  # Infinite days if no consumption
            )
            
            # Replace infinite values with a large number for display purposes
            consumption_df['DaysOfSupply'] = consumption_df['DaysOfSupply'].replace(float('inf'), 90)
            
            # Create enhanced days of supply visualization
            fig = go.Figure()
            
            # Create color mapping based on urgency
            colors = []
            for days in consumption_df['DaysOfSupply']:
                if days < 5:
                    colors.append(DEFAULT_COLORS[0])  # Red - Critical
                elif days < 10:
                    colors.append(DEFAULT_COLORS[4])  # Yellow - Warning
                else:
                    colors.append(DEFAULT_COLORS[3])  # Green - Good
            
            # Add horizontal bars for days of supply
            fig.add_trace(go.Bar(
                y=consumption_df['ItemName'],
                x=consumption_df['DaysOfSupply'].clip(upper=30),  # Clip at 30 days for better visualization
                orientation='h',
                name='Days of Supply',
                marker_color=colors,
                text=consumption_df['DaysOfSupply'].apply(lambda x: f"{x:.1f} days" if x < 30 else "30+ days"),
                textposition='outside',
                hovertemplate='<b>%{y}</b><br>Days of Supply: %{x:.1f}<br>Status: %{text}<extra></extra>'
            ))
            
            # Add reference zones with better styling
            fig.add_vrect(
                x0=0, x1=5,
                fillcolor="red", opacity=0.1,
                layer="below", line_width=0,
                annotation_text="Critical Zone", annotation_position="top left"
            )
            
            fig.add_vrect(
                x0=5, x1=10,
                fillcolor="orange", opacity=0.1,
                layer="below", line_width=0,
                annotation_text="Warning Zone", annotation_position="top left"
            )
            
            fig.add_vrect(
                x0=10, x1=30,
                fillcolor="green", opacity=0.1,
                layer="below", line_width=0,
                annotation_text="Safe Zone", annotation_position="top left"
            )
            
            # Add vertical reference lines
            fig.add_vline(x=5, line_dash="dash", line_color="red", line_width=2)
            fig.add_vline(x=10, line_dash="dash", line_color="orange", line_width=2)
            
            # Enhanced layout
            fig.update_layout(
                title=dict(text='Days of Supply Analysis - Critical Items', font=dict(size=16)),
                xaxis_title='Days of Supply Remaining',
                yaxis_title='Inventory Items',
                template="plotly",
                height=450,
                margin=dict(l=150, r=50, t=80, b=50),
                xaxis=dict(range=[0, 30]),
                yaxis={'categoryorder':'total ascending'},
                showlegend=False
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Display details for these critical items
            with st.expander("Critical Items Details", expanded=False):
                # Add formatted display of critical items
                for i, row in consumption_df.iterrows():
                    days = row['DaysOfSupply']
                    
                    if days < float('inf'):
                        if days < 5:
                            urgency = "🔴 Critical"
                            color = "red"
                        elif days < 10:
                            urgency = "🟠 Warning"
                            color = "orange"
                        else:
                            urgency = "🟢 Adequate"
                            color = "green"
                            
                        st.markdown(f"""
                        **{row['ItemName']}** ({row['ItemCategory']}) - <span style='color:{color}'>{urgency}</span>  
                        Current Quantity: {int(row['CurrentQuantity']):,} | Daily Usage: {row['AvgDailyConsumption']:.1f} | Days Remaining: {days:.1f}
                        """, unsafe_allow_html=True)
                        
                        # Add progress bar to visualize days of supply
                        if days < 30:
                            st.progress(min(days / 30, 1.0))
                        else:
                            st.progress(1.0)
                        
                        st.markdown("---")
                    else:
                        st.markdown(f"""
                        **{row['ItemName']}** ({row['ItemCategory']}) - 🟢 No Recent Usage  
                        Current Quantity: {int(row['CurrentQuantity']):,} | No consumption in last 30 days
                        """)
                        st.progress(1.0)
                        st.markdown("---")
        else:
            st.info("No consumption data available to calculate days of supply")
    else:
        st.success("No inventory items are below reorder level")