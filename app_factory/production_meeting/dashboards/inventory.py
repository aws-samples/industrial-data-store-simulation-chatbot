"""
Inventory dashboard functionality
"""

import streamlit as st
import plotly.express as px


from shared.database import DatabaseManager

# Initialize database manager
db_manager = DatabaseManager()

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
