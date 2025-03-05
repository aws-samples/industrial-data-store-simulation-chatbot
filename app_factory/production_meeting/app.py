"""
Production Meeting Dashboard - Daily lean meeting tool
"""

import streamlit as st
import pandas as pd
import numpy as np
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

# Import shared modules
from shared.database import DatabaseManager

# Import production meeting modules
from production_meeting.dashboards import (
    production_summary_dashboard,
    equipment_status_dashboard,
    quality_dashboard,
    inventory_dashboard,
    productivity_dashboard,
    weekly_overview_dashboard
)
from production_meeting.action_tracker import display_action_tracker
from production_meeting.report import display_report_generator

# Initialize database manager
db_manager = DatabaseManager()

def run_production_meeting():
    """Main function for the Production Meeting Dashboard"""
    
    # Set up the page header
    st.title("📊 Daily Production Meeting Dashboard")
    
    # Initialize session state for meeting data
    if "meeting_data" not in st.session_state:
        st.session_state.meeting_data = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "action_items": [],
            "notes": "",
            "attendees": "",
            "meeting_status": "Not Started",  # Not Started, In Progress, Completed
            "selected_section": "summary"
        }
    
    # Top control bar
    control_cols = st.columns([1, 2, 2, 1, 1])
    
    with control_cols[0]:
        meeting_date = st.date_input(
            "Meeting Date",
            value=datetime.strptime(st.session_state.meeting_data["date"], "%Y-%m-%d"),
            key="meeting_date"
        )
        st.session_state.meeting_data["date"] = meeting_date.strftime("%Y-%m-%d")
    
    with control_cols[1]:
        st.text_input(
            "Attendees",
            value=st.session_state.meeting_data["attendees"],
            key="attendees",
            placeholder="List meeting attendees"
        )
        st.session_state.meeting_data["attendees"] = st.session_state.attendees
    
    with control_cols[2]:
        # Time controls
        start_time = datetime.now().replace(hour=9, minute=0, second=0)
        meeting_duration = st.slider(
            "Meeting Duration (minutes)",
            min_value=5,
            max_value=30,
            value=15,
            step=5,
            key="meeting_duration"
        )
        
        # Calculate end time
        end_time = start_time + timedelta(minutes=meeting_duration)
        st.write(f"⏰ Meeting Time: {start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}")
    
    with control_cols[3]:
        meeting_status = st.selectbox(
            "Meeting Status",
            options=["Not Started", "In Progress", "Completed"],
            index=["Not Started", "In Progress", "Completed"].index(st.session_state.meeting_data["meeting_status"]),
            key="meeting_status"
        )
        st.session_state.meeting_data["meeting_status"] = meeting_status
    
    with control_cols[4]:
        if st.button("🏠 Return to Main Menu", use_container_width=True):
            st.session_state.app_mode = None
            st.rerun()
    
    # Main navigation tabs
    tabs = st.tabs([
        "📈 Production Summary", 
        "🔧 Equipment Status", 
        "⚠️ Quality Issues",
        "📦 Inventory Alerts",
        "👥 Productivity",
        "📋 Action Items",
        "📝 Meeting Notes",
        "📄 Reports"
    ])
    
    # Tab 1: Production Summary
    with tabs[0]:
        production_summary_dashboard()
    
    # Tab 2: Equipment Status
    with tabs[1]:
        equipment_status_dashboard()
    
    # Tab 3: Quality Issues
    with tabs[2]:
        quality_dashboard()
    
    # Tab 4: Inventory Alerts
    with tabs[3]:
        inventory_dashboard()
    
    # Tab 5: Productivity
    with tabs[4]:
        productivity_dashboard()
    
    # Tab 6: Action Items
    with tabs[5]:
        display_action_tracker(st.session_state.meeting_data["date"])
    
    # Tab 7: Meeting Notes
    with tabs[6]:
        st.header("📝 Meeting Notes")
        
        # Meeting notes input
        notes = st.text_area(
            "Meeting Notes",
            value=st.session_state.meeting_data["notes"],
            height=300,
            key="meeting_notes"
        )
        st.session_state.meeting_data["notes"] = notes
        
        # Weekly overview section
        with st.expander("Weekly Performance Overview", expanded=False):
            weekly_overview_dashboard()
    
    # Tab 8: Reports
    with tabs[7]:
        display_report_generator(
            meeting_date=st.session_state.meeting_data["date"], 
            meeting_data=st.session_state.meeting_data
        )

# This allows the module to be run directly for testing
if __name__ == "__main__":
    # Set page config
    st.set_page_config(
        page_title="Production Meeting Dashboard", 
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    run_production_meeting()