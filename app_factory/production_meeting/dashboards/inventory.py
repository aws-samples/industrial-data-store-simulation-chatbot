"""
Inventory dashboard
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import datetime, timedelta

from shared.database import DatabaseManager

# Initialize database manager
db_manager = DatabaseManager()

def inventory_dashboard():
    """Display the enhanced inventory dashboard"""
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
        
        # Display inventory alerts by category - SIMPLIFIED
        st.subheader("Inventory Alerts by Category")
        
        # Group by category to get total shortage amount per category
        category_alerts = inventory_alerts.groupby('Category').agg({
            'ShortageAmount': 'sum',
            'ItemName': 'count'
        }).reset_index()
        
        category_alerts.rename(columns={'ShortageAmount': 'TotalShortage', 'ItemName': 'ItemCount'}, inplace=True)
        
        # Simple bar chart showing total shortage amount per category
        fig = px.bar(
            category_alerts,
            x='Category',
            y='TotalShortage',
            title='Total Shortage Amount by Category',
            labels={
                'TotalShortage': 'Total Shortage Amount',
                'Category': 'Category'
            },
            color='Category',
            hover_data=['ItemCount']  # Show item count on hover
        )
        
        # Force y-axis to use integers only
        fig.update_yaxes(dtick=50, tick0=0)
        
        # Add data labels on top of bars
        fig.update_traces(texttemplate='%{y}', textposition='outside')
        
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
            
        st.subheader("Days of Supply Analysis")
        
        # Get consumption data to calculate days of supply
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
            AND mc.ConsumptionDate >= date('now', '-30 day')
        GROUP BY 
            i.ItemID, i.Name, i.Category, i.Quantity, i.ReorderLevel
        ORDER BY 
            (i.Quantity / CASE WHEN AVG(mc.ActualQuantity) > 0 THEN AVG(mc.ActualQuantity) ELSE 999999 END) ASC
        LIMIT 10
        """
        
        result = db_manager.execute_query(consumption_query)
        
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
            
            # Create days of supply visualization
            fig = go.Figure()
            
            # Add horizontal bars for days of supply
            fig.add_trace(go.Bar(
                y=consumption_df['ItemName'],
                x=consumption_df['DaysOfSupply'].clip(upper=90),  # Clip at 90 days for better visualization
                orientation='h',
                name='Days of Supply',
                marker_color=consumption_df['DaysOfSupply'].apply(lambda x: 
                    'red' if x < 5 else 
                    'orange' if x < 10 else 
                    'green'
                )
            ))
            
            # Add vertical lines for reference
            fig.add_shape(
                type="line",
                x0=5, y0=-0.5,
                x1=5, y1=len(consumption_df) - 0.5,
                line=dict(color="red", width=2, dash="dash")
            )
            
            fig.add_shape(
                type="line",
                x0=10, y0=-0.5,
                x1=10, y1=len(consumption_df) - 0.5,
                line=dict(color="orange", width=2, dash="dash")
            )
            
            # Add annotations
            fig.add_annotation(
                x=5, y=len(consumption_df),
                text="Critical (5 days)",
                showarrow=False,
                yshift=10,
                font=dict(color="red")
            )
            
            fig.add_annotation(
                x=10, y=len(consumption_df),
                text="Warning (10 days)",
                showarrow=False,
                yshift=10,
                font=dict(color="orange")
            )
            
            # Update layout
            fig.update_layout(
                title='Days of Supply for Critical Items',
                xaxis_title='Days of Supply',
                yaxis_title='Item',
                height=400,
                margin=dict(l=20, r=20, t=50, b=20),
                xaxis=dict(range=[0, 30])  # 30 days
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