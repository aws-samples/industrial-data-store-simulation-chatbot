"""
Interactive explanation utilities for metrics
"""

import streamlit as st
import pandas as pd
import json
from datetime import datetime, timedelta

from shared.database import DatabaseManager
from production_meeting.ai_insights import generate_ai_insight

# Initialize database manager
db_manager = DatabaseManager()

def metric_with_explanation(label, value, key, context, metric_type, delta=None, delta_color="normal", help=None):
    """
    Create a metric with an expandable AI-powered explanation
    
    Args:
        label (str): Metric label
        value (str): Metric value to display
        key (str): Unique key for this metric
        context (str): Context for AI explanation (production, quality, etc.)
        metric_type (str): Type of metric for gathering relevant data
        delta (str/int/float, optional): Delta value (change)
        delta_color (str): Color for delta display
        help (str, optional): Help text for tooltip
    
    Returns:
        None: Displays the metric in Streamlit
    """
    # Create columns for metric and button
    col1, col2 = st.columns([4, 1])
    
    # Display the metric
    with col1:
        st.metric(label=label, value=value, delta=delta, delta_color=delta_color, help=help)
    
    # Add the explanation button
    with col2:
        explain_button = st.button("Explain", key=f"explain_{key}", use_container_width=True)
    
    # Handle explanation request
    if explain_button:
        # Create a contextual query for this specific metric
        query = f"Why is the {label.lower()} {value}? What factors might have contributed to this value?"
        
        # Get data specific to this metric
        metric_data = gather_metric_data(metric_type, context)
        
        # Generate the explanation
        with st.spinner("Generating explanation..."):
            explanation = generate_ai_insight(
                context=context, 
                query=query, 
                dashboard_data=metric_data,
                include_historical=True
            )
            
            # Display the explanation in an expandable container
            with st.expander(f"Explanation for {label}: {value}", expanded=True):
                st.markdown(explanation, unsafe_allow_html=True)
                
                # Add a "Dig deeper" option
                if st.button("Dig deeper", key=f"deeper_{key}"):
                    with st.spinner("Analyzing in more detail..."):
                        # Generate a more detailed explanation
                        deeper_query = f"Provide a detailed analysis of the {label.lower()} metric. What specific factors and relationships in the data explain why it's {value}? Include specific production data points, historical context, and any correlations with other metrics."
                        
                        deeper_explanation = generate_ai_insight(
                            context="all", 
                            query=deeper_query, 
                            include_historical=True
                        )
                        
                        st.markdown(deeper_explanation, unsafe_allow_html=True)

def gather_metric_data(metric_type, context):
    """
    Gather data relevant to a specific metric
    
    Args:
        metric_type (str): Type of metric (completion_rate, defect_rate, oee, etc.)
        context (str): Dashboard context (production, quality, etc.)
        
    Returns:
        dict: Data relevant to this metric
    """
    data = {}
    
    # Production metrics
    if metric_type in ["completion_rate", "planned_quantity", "actual_production"]:
        # Get recent production data
        yesterday_data = db_manager.get_daily_production_summary(days_back=1)
        if not yesterday_data.empty:
            data['production'] = yesterday_data.to_dict(orient='records')
        
        # Get historical production data
        historical_query = """
        SELECT 
            date(wo.ActualEndTime) as ProductionDate,
            SUM(wo.Quantity) as PlannedQuantity,
            SUM(wo.ActualProduction) as ActualProduction,
            ROUND(SUM(wo.ActualProduction) * 100.0 / SUM(wo.Quantity), 2) as CompletionPercentage
        FROM 
            WorkOrders wo
        WHERE 
            wo.Status = 'completed'
            AND wo.ActualEndTime >= date('now', '-14 day')
        GROUP BY 
            date(wo.ActualEndTime)
        ORDER BY 
            ProductionDate
        """
        result = db_manager.execute_query(historical_query)
        if result["success"]:
            data['historical_production'] = result["rows"]
        
        # Get any downtime events that might have affected completion
        downtime_query = """
        SELECT 
            d.Reason as DowntimeReason,
            d.Category as DowntimeCategory,
            SUM(d.Duration) as TotalMinutes
        FROM 
            Downtimes d
        WHERE 
            d.StartTime >= date('now', '-1 day')
        GROUP BY 
            d.Reason, d.Category
        ORDER BY 
            TotalMinutes DESC
        """
        result = db_manager.execute_query(downtime_query)
        if result["success"]:
            data['downtime_events'] = result["rows"]
            
        # Get information about product complexity
        product_query = """
        SELECT 
            p.Name as ProductName, 
            p.StandardProcessTime,
            COUNT(bom.BOMID) as ComponentCount
        FROM 
            Products p
        LEFT JOIN 
            BillOfMaterials bom ON p.ProductID = bom.ProductID
        GROUP BY 
            p.ProductID
        ORDER BY 
            ComponentCount DESC
        """
        result = db_manager.execute_query(product_query)
        if result["success"]:
            data['product_complexity'] = result["rows"]
    
    # OEE metrics
    elif metric_type in ["oee", "availability", "performance", "quality_oee"]:
        # Get OEE data
        oee_query = """
        SELECT 
            m.Type as MachineType,
            ROUND(AVG(oee.OEE) * 100, 2) as AvgOEE,
            ROUND(AVG(oee.Availability) * 100, 2) as AvgAvailability,
            ROUND(AVG(oee.Performance) * 100, 2) as AvgPerformance,
            ROUND(AVG(oee.Quality) * 100, 2) as AvgQuality
        FROM 
            OEEMetrics oee
        JOIN 
            Machines m ON oee.MachineID = m.MachineID
        WHERE 
            oee.Date = date('now', '-1 day')
        GROUP BY 
            m.Type
        """
        result = db_manager.execute_query(oee_query)
        if result["success"]:
            data['oee_metrics'] = result["rows"]
        
        # Get historical OEE data
        historical_query = """
        SELECT 
            date(oee.Date) as MeasurementDate,
            ROUND(AVG(oee.OEE) * 100, 2) as AvgOEE
        FROM 
            OEEMetrics oee
        WHERE 
            oee.Date >= date('now', '-14 day')
        GROUP BY 
            date(oee.Date)
        ORDER BY 
            MeasurementDate
        """
        result = db_manager.execute_query(historical_query)
        if result["success"]:
            data['historical_oee'] = result["rows"]
            
        # Get machine status information
        machine_query = """
        SELECT 
            m.Type as MachineType,
            m.Status,
            COUNT(m.MachineID) as MachineCount,
            AVG(m.EfficiencyFactor) as AvgEfficiency,
            AVG(julianday('now') - julianday(m.LastMaintenanceDate)) as AvgDaysSinceMaintenance
        FROM 
            Machines m
        GROUP BY 
            m.Type, m.Status
        """
        result = db_manager.execute_query(machine_query)
        if result["success"]:
            data['machine_status'] = result["rows"]
    
    # Quality metrics
    elif metric_type in ["defect_rate", "yield_rate", "rework_rate"]:
        # Get quality data
        quality_data = db_manager.get_quality_summary(days_back=1, range_days=1)
        if not quality_data.empty:
            data['quality'] = quality_data.to_dict(orient='records')
        
        # Get defect details
        defects_query = """
        SELECT 
            d.DefectType,
            COUNT(d.DefectID) as DefectCount,
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
            date(qc.Date) = date('now', '-1 day')
        GROUP BY 
            d.DefectType, p.Name, p.Category
        ORDER BY 
            DefectCount DESC
        """
        result = db_manager.execute_query(defects_query)
        if result["success"]:
            data['defects'] = result["rows"]
            
        # Get historical quality data
        historical_query = """
        SELECT 
            date(qc.Date) as InspectionDate,
            COUNT(qc.CheckID) as InspectionCount,
            ROUND(AVG(qc.DefectRate) * 100, 2) as AvgDefectRate,
            ROUND(AVG(qc.YieldRate) * 100, 2) as AvgYieldRate
        FROM 
            QualityControl qc
        WHERE 
            qc.Date >= date('now', '-14 day')
        GROUP BY 
            date(qc.Date)
        ORDER BY 
            InspectionDate
        """
        result = db_manager.execute_query(historical_query)
        if result["success"]:
            data['historical_quality'] = result["rows"]
            
        # Get inspector information
        inspector_query = """
        SELECT 
            e.Name as InspectorName,
            COUNT(qc.CheckID) as InspectionCount,
            ROUND(AVG(qc.DefectRate) * 100, 2) as AvgDefectRate
        FROM 
            QualityControl qc
        JOIN 
            Employees e ON qc.InspectorID = e.EmployeeID
        WHERE 
            qc.Date >= date('now', '-7 day')
        GROUP BY 
            e.EmployeeID
        """
        result = db_manager.execute_query(inspector_query)
        if result["success"]:
            data['inspector_data'] = result["rows"]
    
    # Inventory metrics
    elif metric_type in ["inventory_level", "reorder_level", "lead_time"]:
        # Get inventory alerts
        inventory_alerts = db_manager.get_inventory_alerts()
        if not inventory_alerts.empty:
            data['inventory_alerts'] = inventory_alerts.to_dict(orient='records')
            
        # Get supplier data
        supplier_query = """
        SELECT 
            s.Name as SupplierName,
            s.LeadTime,
            s.ReliabilityScore,
            COUNT(i.ItemID) as ItemCount
        FROM 
            Suppliers s
        JOIN 
            Inventory i ON s.SupplierID = i.SupplierID
        GROUP BY 
            s.SupplierID
        """
        result = db_manager.execute_query(supplier_query)
        if result["success"]:
            data['supplier_data'] = result["rows"]
            
        # Get consumption data
        consumption_query = """
        SELECT 
            i.Name as ItemName,
            AVG(mc.ActualQuantity) as AvgDailyConsumption,
            i.Quantity as CurrentQuantity,
            i.ReorderLevel
        FROM 
            MaterialConsumption mc
        JOIN 
            Inventory i ON mc.ItemID = i.ItemID
        WHERE 
            mc.ConsumptionDate >= date('now', '-30 day')
        GROUP BY 
            i.ItemID
        """
        result = db_manager.execute_query(consumption_query)
        if result["success"]:
            data['consumption_data'] = result["rows"]
    
    # TO DO - add more metrics as needed 
    
    return data