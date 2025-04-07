"""
Quality dashboard functionality
"""

import streamlit as st
import pandas as pd
import plotly.express as px

from shared.database import DatabaseManager
from production_meeting.utils.interactive_explanations import metric_with_explanation

# Initialize database manager
db_manager = DatabaseManager()

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
