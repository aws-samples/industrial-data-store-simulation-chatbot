"""
Meeting report generation for production meetings
"""

import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

from shared.database import DatabaseManager

# Initialize database manager
db_manager = DatabaseManager()

class ReportGenerator:
    """Generator for meeting reports and summaries"""
    
    def __init__(self):
        """Initialize the report generator"""
        # Create the reports directory if it doesn't exist
        self.reports_dir = Path("reports")
        self.reports_dir.mkdir(exist_ok=True, parents=True)
    
    def save_meeting_report(self, meeting_data):
        """
        Save meeting data to a JSON file
        
        Args:
            meeting_data (dict): Meeting data including date, notes, attendees, etc.
            
        Returns:
            str: Path to the saved report file
        """
        # Generate filename based on meeting date
        filename = f"production_meeting_{meeting_data['date']}.json"
        filepath = self.reports_dir / filename
        
        try:
            # Save meeting data to file
            with open(filepath, 'w') as f:
                json.dump(meeting_data, f, indent=2)
            
            return str(filepath)
        except Exception as e:
            print(f"Error saving meeting report: {e}")
            return None
    
    def load_meeting_report(self, meeting_date):
        """
        Load a meeting report from file
        
        Args:
            meeting_date (str): Meeting date in YYYY-MM-DD format
            
        Returns:
            dict: Meeting data or None if not found
        """
        filename = f"production_meeting_{meeting_date}.json"
        filepath = self.reports_dir / filename
        
        if not filepath.exists():
            return None
        
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading meeting report: {e}")
            return None
    
    def list_available_reports(self):
        """
        Get a list of all available meeting reports
        
        Returns:
            list: List of meeting dates with available reports
        """
        reports = []
        
        for file in self.reports_dir.glob("production_meeting_*.json"):
            try:
                # Extract date from filename
                date_str = file.stem.replace("production_meeting_", "")
                reports.append(date_str)
            except:
                pass
        
        # Sort by date (newest first)
        reports.sort(reverse=True)
        
        return reports
    
    def generate_meeting_summary(self, meeting_date, meeting_data, include_data=True):
        """
        Generate a markdown summary of the meeting
        
        Args:
            meeting_date (str): Meeting date in YYYY-MM-DD format
            meeting_data (dict): Meeting data including notes, attendees, etc.
            include_data (bool): Whether to include production data in the summary
            
        Returns:
            str: Markdown formatted meeting summary
        """
        # Start with header
        summary = f"""
        # Production Meeting Summary - {meeting_date}
        
        **Status:** {meeting_data.get('meeting_status', 'Unknown')}  
        **Attendees:** {meeting_data.get('attendees', 'Not recorded')}
        
        """
        
        # Add production data if requested
        if include_data:
            # Yesterday's production data
            yesterday_data = db_manager.get_daily_production_summary(days_back=1)
            
            if not yesterday_data.empty:
                total_planned = yesterday_data['PlannedQuantity'].sum()
                total_actual = yesterday_data['ActualProduction'].sum()
                completion_rate = (total_actual / total_planned * 100) if total_planned > 0 else 0
                
                summary += f"""
                ## Production Performance
                - Yesterday's completion rate: {completion_rate:.1f}% ({total_actual} of {total_planned} units)
                """
            
            # Machine status
            machine_status = db_manager.get_machine_status_summary()
            
            if not machine_status.empty:
                total_machines = machine_status['TotalMachines'].sum()
                running_machines = machine_status['Running'].sum()
                availability = running_machines / total_machines * 100 if total_machines > 0 else 0
                machines_in_maintenance = machine_status['Maintenance'].sum()
                
                summary += f"""
                - Current machine availability: {availability:.1f}% ({running_machines} of {total_machines} machines running)
                - {machines_in_maintenance} machines currently in maintenance
                """
            
            # Quality data
            quality_data = db_manager.get_quality_summary(days_back=1)
            
            if not quality_data.empty:
                avg_defect_rate = quality_data['AvgDefectRate'].mean()
                avg_yield_rate = quality_data['AvgYieldRate'].mean()
                
                summary += f"""
                - Quality yield rate: {avg_yield_rate:.1f}% (defect rate: {avg_defect_rate:.1f}%)
                """
            
            # Inventory alerts
            inventory_alerts = db_manager.get_inventory_alerts()
            inventory_alert_count = len(inventory_alerts) if not inventory_alerts.empty else 0
            
            summary += f"""
                - {inventory_alert_count} inventory items below reorder level
                """
        
        # Add action items
        if meeting_data.get('action_items'):
            summary += """
            ## Action Items
            """
            
            for item in meeting_data['action_items']:
                summary += f"""
                - {item['description']} (Owner: {item['owner']}, Due: {item['due_date']}, Status: {item['status']})
                """
        
        # Add notes
        if meeting_data.get('notes'):
            summary += f"""
            ## Notes
            {meeting_data['notes']}
            """
        
        return summary.replace("        ", "")  # Remove leading spaces from the heredoc
    
    def generate_weekly_summary(self, end_date=None):
        """
        Generate a weekly summary report
        
        Args:
            end_date (str): End date in YYYY-MM-DD format (defaults to today)
            
        Returns:
            str: Markdown formatted weekly summary
        """
        if end_date is None:
            end_date = datetime.now().date()
        elif isinstance(end_date, str):
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
        
        # Calculate start date (7 days before end date)
        start_date = end_date - timedelta(days=6)
        
        # Convert to strings for SQL
        end_date_str = end_date.strftime('%Y-%m-%d')
        start_date_str = start_date.strftime('%Y-%m-%d')
        
        # Header
        summary = f"""
        # Weekly Production Summary
        **Period:** {start_date_str} to {end_date_str}
        
        """
        
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
            
            # Calculate weekly totals
            total_planned = weekly_production['PlannedQuantity'].sum()
            total_actual = weekly_production['ActualProduction'].sum()
            total_scrap = weekly_production['ScrapQuantity'].sum()
            avg_completion = weekly_production['CompletionPercentage'].mean()
            
            summary += f"""
            ## Production Summary
            - **Total Planned Production:** {int(total_planned):,} units
            - **Total Actual Production:** {int(total_actual):,} units
            - **Average Completion Rate:** {avg_completion:.1f}%
            - **Total Scrap:** {int(total_scrap):,} units ({(total_scrap/total_planned*100 if total_planned > 0 else 0):.1f}% of planned)
            
            ### Daily Production Trend
            """
            
            # Add daily data
            summary += "| Date | Planned | Actual | Completion % |\n"
            summary += "|------|---------|--------|-------------|\n"
            
            for _, row in weekly_production.iterrows():
                summary += f"| {row['ProductionDate']} | {int(row['PlannedQuantity']):,} | {int(row['ActualProduction']):,} | {row['CompletionPercentage']}% |\n"
        else:
            summary += "No production data available for this period.\n"
        
        # Quality data
        weekly_quality_query = f"""
        SELECT 
            p.Category as ProductCategory,
            COUNT(qc.CheckID) as InspectionCount,
            ROUND(AVG(qc.DefectRate) * 100, 2) as AvgDefectRate,
            ROUND(AVG(qc.ReworkRate) * 100, 2) as AvgReworkRate,
            ROUND(AVG(qc.YieldRate) * 100, 2) as AvgYieldRate,
            SUM(CASE WHEN qc.Result = 'pass' THEN 1 ELSE 0 END) as PassCount,
            SUM(CASE WHEN qc.Result = 'fail' THEN 1 ELSE 0 END) as FailCount,
            SUM(CASE WHEN qc.Result = 'rework' THEN 1 ELSE 0 END) as ReworkCount
        FROM 
            QualityControl qc
        JOIN 
            WorkOrders wo ON qc.OrderID = wo.OrderID
        JOIN 
            Products p ON wo.ProductID = p.ProductID
        WHERE 
            qc.Date BETWEEN '{start_date_str}' AND '{end_date_str} 23:59:59'
        GROUP BY 
            p.Category
        ORDER BY 
            InspectionCount DESC
        """
        
        result = db_manager.execute_query(weekly_quality_query)
        if result["success"] and result["row_count"] > 0:
            weekly_quality = pd.DataFrame(result["rows"])
            
            summary += f"""
            ## Quality Summary
            """
            
            # Add quality data by product category
            summary += "| Product Category | Inspections | Pass Rate | Defect Rate | Rework Rate |\n"
            summary += "|-----------------|------------|-----------|-------------|-------------|\n"
            
            for _, row in weekly_quality.iterrows():
                pass_rate = row['PassCount'] / row['InspectionCount'] * 100 if row['InspectionCount'] > 0 else 0
                summary += f"| {row['ProductCategory']} | {int(row['InspectionCount']):,} | {pass_rate:.1f}% | {row['AvgDefectRate']}% | {row['AvgReworkRate']}% |\n"
            
            # Get top defects
            top_defects_query = f"""
            SELECT 
                d.DefectType,
                COUNT(d.DefectID) as DefectCount,
                AVG(d.Severity) as AvgSeverity,
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
                qc.Date BETWEEN '{start_date_str}' AND '{end_date_str} 23:59:59'
            GROUP BY 
                d.DefectType
            ORDER BY 
                DefectCount DESC
            LIMIT 5
            """
            
            result = db_manager.execute_query(top_defects_query)
            if result["success"] and result["row_count"] > 0:
                top_defects = pd.DataFrame(result["rows"])
                
                summary += f"""
                ### Top 5 Defect Types
                """
                
                for _, row in top_defects.iterrows():
                    summary += f"- **{row['DefectType']}** ({row['DefectCount']} occurrences, Avg Severity: {row['AvgSeverity']:.1f}/5) in {row['ProductCategory']}\n"
        
        # Equipment performance
        weekly_oee_query = f"""
        SELECT 
            m.Type as MachineType,
            AVG(oee.Availability) * 100 as AvgAvailability,
            AVG(oee.Performance) * 100 as AvgPerformance,
            AVG(oee.Quality) * 100 as AvgQuality,
            AVG(oee.OEE) * 100 as AvgOEE,
            COUNT(DISTINCT m.MachineID) as MachineCount
        FROM 
            OEEMetrics oee
        JOIN 
            Machines m ON oee.MachineID = m.MachineID
        WHERE 
            oee.Date BETWEEN '{start_date_str}' AND '{end_date_str} 23:59:59'
        GROUP BY 
            m.Type
        ORDER BY 
            AvgOEE DESC
        """
        
        result = db_manager.execute_query(weekly_oee_query)
        if result["success"] and result["row_count"] > 0:
            weekly_oee = pd.DataFrame(result["rows"])
            
            summary += f"""
            ## Equipment Performance
            """
            
            # Add OEE data by machine type
            summary += "| Machine Type | # Machines | Availability | Performance | Quality | OEE |\n"
            summary += "|-------------|------------|--------------|-------------|---------|-----|\n"
            
            for _, row in weekly_oee.iterrows():
                summary += f"| {row['MachineType']} | {int(row['MachineCount']):,} | {row['AvgAvailability']:.1f}% | {row['AvgPerformance']:.1f}% | {row['AvgQuality']:.1f}% | {row['AvgOEE']:.1f}% |\n"
            
            # Overall OEE
            overall_availability = weekly_oee['AvgAvailability'].mean()
            overall_performance = weekly_oee['AvgPerformance'].mean()
            overall_quality = weekly_oee['AvgQuality'].mean()
            overall_oee = overall_availability * overall_performance * overall_quality / 10000
            
            summary += f"""
            ### Overall OEE: {overall_oee:.1f}%
            - Availability: {overall_availability:.1f}%
            - Performance: {overall_performance:.1f}%
            - Quality: {overall_quality:.1f}%
            """
            
            # Downtime events
            downtime_query = f"""
            SELECT 
                d.Reason as DowntimeReason,
                d.Category as DowntimeCategory,
                COUNT(d.DowntimeID) as EventCount,
                SUM(d.Duration) as TotalMinutes,
                AVG(d.Duration) as AvgDuration
            FROM 
                Downtimes d
            WHERE 
                d.StartTime BETWEEN '{start_date_str}' AND '{end_date_str} 23:59:59'
            GROUP BY 
                d.Reason, d.Category
            ORDER BY 
                TotalMinutes DESC
            LIMIT 5
            """
            
            result = db_manager.execute_query(downtime_query)
            if result["success"] and result["row_count"] > 0:
                downtimes = pd.DataFrame(result["rows"])
                
                summary += f"""
                ### Top Downtime Reasons
                """
                
                for _, row in downtimes.iterrows():
                    hours = row['TotalMinutes'] / 60
                    summary += f"- **{row['DowntimeReason']}** ({row['DowntimeCategory']}): {hours:.1f} hours total across {int(row['EventCount'])} events\n"
        
        # Generate timestamp
        summary += f"""
        
        ---
        *Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}*
        """
        
        return summary.replace("        ", "")  # Remove leading spaces from the heredoc
    
    def export_to_pdf(self, markdown_content, output_file=None):
        """
        Export markdown content to PDF (placeholder function)
        
        In a real implementation, this would use a library like reportlab,
        weasyprint, or pdfkit to convert markdown to PDF.
        
        Args:
            markdown_content (str): Markdown content
            output_file (str): Output file path
            
        Returns:
            str: Path to the PDF file
        """
        # This is a placeholder - in a real implementation, would convert to PDF
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"report_{timestamp}.md"
        
        output_path = self.reports_dir / output_file
        
        with open(output_path, 'w') as f:
            f.write(markdown_content)
        
        return str(output_path)

def display_report_generator(meeting_date=None, meeting_data=None):
    """
    Streamlit component for generating and viewing reports
    
    Args:
        meeting_date (str): Current meeting date
        meeting_data (dict): Current meeting data
    """
    st.subheader("📄 Meeting Reports")
    
    # Initialize report generator
    generator = ReportGenerator()
    
    # Create tabs for different report options
    tab1, tab2, tab3 = st.tabs(["Current Meeting", "Weekly Report", "Past Reports"])
    
    # Tab 1: Current meeting summary
    with tab1:
        st.write("Generate a summary for the current meeting")
        
        include_data = st.checkbox("Include production data in summary", value=True)
        
        if st.button("Generate Meeting Summary"):
            if meeting_date and meeting_data:
                with st.spinner("Generating meeting summary..."):
                    summary = generator.generate_meeting_summary(meeting_date, meeting_data, include_data)
                    st.markdown(summary)
                    
                    # Provide download link
                    st.download_button(
                        "Download Summary",
                        summary,
                        f"meeting_summary_{meeting_date}.md",
                        "text/markdown",
                        key="download_meeting_summary"
                    )
                    
                    # Save option
                    if st.button("Save Meeting Report"):
                        filepath = generator.save_meeting_report(meeting_data)
                        if filepath:
                            st.success(f"Meeting report saved to {filepath}")
                        else:
                            st.error("Failed to save meeting report")
            else:
                st.warning("No meeting data available. Please fill in meeting details first.")
    
    # Tab 2: Weekly report
    with tab2:
        st.write("Generate a weekly summary report")
        
        end_date = st.date_input(
            "Week Ending",
            value=datetime.now().date(),
            key="weekly_report_date"
        )
        
        if st.button("Generate Weekly Report"):
            with st.spinner("Generating weekly report..."):
                summary = generator.generate_weekly_summary(end_date)
                st.markdown(summary)
                
                # Provide download link
                st.download_button(
                    "Download Weekly Report",
                    summary,
                    f"weekly_report_{end_date.strftime('%Y%m%d')}.md",
                    "text/markdown",
                    key="download_weekly_report"
                )
    
    # Tab 3: Past reports
    with tab3:
        st.write("View past meeting reports")
        
        # Get available reports
        reports = generator.list_available_reports()
        
        if reports:
            selected_report = st.selectbox(
                "Select a past report",
                options=reports,
                key="past_report_select"
            )
            
            if selected_report:
                # Load the selected report
                report_data = generator.load_meeting_report(selected_report)
                
                if report_data:
                    st.write(f"**Meeting Date:** {selected_report}")
                    st.write(f"**Status:** {report_data.get('meeting_status', 'Unknown')}")
                    st.write(f"**Attendees:** {report_data.get('attendees', 'Not recorded')}")
                    
                    if report_data.get('notes'):
                        st.subheader("Meeting Notes")
                        st.write(report_data['notes'])
                    
                    if report_data.get('action_items'):
                        st.subheader("Action Items")
                        for item in report_data['action_items']:
                            st.markdown(f"""
                            **{item['description']}**  
                            Owner: {item['owner']} | Priority: {item['priority']} | Due: {item['due_date']} | Status: {item['status']}
                            """)
                    
                    # Generate summary option
                    if st.button("Generate Summary from this Report"):
                        summary = generator.generate_meeting_summary(
                            selected_report, report_data, include_data=True
                        )
                        st.markdown(summary)
                        
                        # Provide download link
                        st.download_button(
                            "Download Summary",
                            summary,
                            f"meeting_summary_{selected_report}.md",
                            "text/markdown",
                            key="download_past_summary"
                        )
                else:
                    st.error(f"Could not load report for {selected_report}")
        else:
            st.info("No past reports available")

# For testing the module directly
if __name__ == "__main__":
    st.set_page_config(page_title="Report Generator", layout="wide")
    st.title("Meeting Report Generator Test")
    
    # Sample meeting data for testing
    test_meeting_data = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "attendees": "John Smith, Jane Doe, Bob Johnson",
        "meeting_status": "Completed",
        "notes": "This is a test meeting with sample notes.\n\n- Discussed production issues\n- Reviewed quality metrics\n- Assigned action items",
        "action_items": [
            {
                "id": 1,
                "description": "Investigate machine downtime",
                "owner": "John Smith",
                "priority": "High",
                "due_date": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"),
                "status": "Open"
            },
            {
                "id": 2,
                "description": "Order replacement parts",
                "owner": "Jane Doe",
                "priority": "Medium",
                "due_date": (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d"),
                "status": "In Progress"
            }
        ]
    }
    
    display_report_generator(test_meeting_data["date"], test_meeting_data)