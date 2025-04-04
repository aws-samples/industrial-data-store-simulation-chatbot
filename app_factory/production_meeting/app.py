"""
Production Meeting Dashboard - Daily lean meeting tool with enhanced AI analytics
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
    weekly_overview_dashboard,
    add_process_flow_visualization,
    add_root_cause_analysis,
)
from production_meeting.action_tracker import display_action_tracker
from production_meeting.report import display_report_generator
from production_meeting.ai_insights import (
    display_ai_insights_tab, 
    provide_tab_insights,
    generate_predictive_insights,
    generate_decision_intelligence,
    generate_narrative_summary,
    add_conversational_analysis
)

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
    
    # Initialize session state for AI settings
    if "enable_tab_insights" not in st.session_state:
        st.session_state.enable_tab_insights = True
    
    # Top control bar
    control_cols = st.columns([1, 2, 1, 1, 1, 1])
    
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
            "Duration (min)",
            min_value=5,
            max_value=30,
            value=15,
            step=5,
            key="meeting_duration"
        )
        
        # Calculate end time
        end_time = start_time + timedelta(minutes=meeting_duration)
        st.write(f"⏰ {start_time.strftime('%H:%M')}-{end_time.strftime('%H:%M')}")
    
    with control_cols[3]:
        meeting_status = st.selectbox(
            "Status",
            options=["Not Started", "In Progress", "Completed"],
            index=["Not Started", "In Progress", "Completed"].index(st.session_state.meeting_data["meeting_status"]),
            key="meeting_status"
        )
        st.session_state.meeting_data["meeting_status"] = meeting_status
    
    with control_cols[4]:
        # Toggle for AI insights
        ai_enabled = st.checkbox(
            "Tab Insights", 
            value=st.session_state.enable_tab_insights,
            help="Enable/disable AI insights in dashboard tabs"
        )
        st.session_state.enable_tab_insights = ai_enabled
    
    with control_cols[5]:
        if st.button("🏠 Main Menu", use_container_width=True):
            st.session_state.app_mode = None
            st.rerun()
    
    # Main navigation tabs 
    tabs = st.tabs([
        "📈 Production Summary", 
        "🔧 Equipment Status", 
        "⚠️ Quality Issues",
        "📦 Inventory Alerts",
        "👥 Productivity",
        "🔄 Process Flow",
        "🔍 Root Cause Analysis", 
        "🤖 AI Insights",
        "📋 Action Items",
        "📝 Meeting Notes",
        "📄 Reports"
    ])
    
    # Tab 1: Production Summary
    with tabs[0]:
        production_summary_dashboard()
        provide_tab_insights("production")
    
    # Tab 2: Equipment Status
    with tabs[1]:
        equipment_status_dashboard()
        provide_tab_insights("machines")
    
    # Tab 3: Quality Issues
    with tabs[2]:
        quality_dashboard()
        provide_tab_insights("quality")
    
    # Tab 4: Inventory Alerts
    with tabs[3]:
        inventory_dashboard()
        provide_tab_insights("inventory")
    
    # Tab 5: Productivity
    with tabs[4]:
        productivity_dashboard()
    
    # Tab 6: Process Flow
    with tabs[5]:
        add_process_flow_visualization()
    
    # Tab 7: Root Cause Analysis
    with tabs[6]:
        add_root_cause_analysis()
    
    # Tab 8: AI Insights - Enhanced with structured selection options
    with tabs[7]:
        # Let user select which type of AI analysis to show
        analysis_type = st.radio(
            "Select Analysis Type:",
            options=[
                "General Insights", 
                "Predictive Analysis", 
                "Decision Intelligence", 
                "Data Storytelling", 
                "Conversational Q&A"
            ],
            horizontal=True
        )
        
        if analysis_type == "General Insights":
            display_ai_insights_tab()
        elif analysis_type == "Predictive Analysis":
            generate_predictive_insights()
        elif analysis_type == "Decision Intelligence":
            generate_decision_intelligence()
        elif analysis_type == "Data Storytelling":
            generate_narrative_summary()
        else:  # Conversational Q&A
            add_conversational_analysis()
    
    # Tab 9: Action Items
    with tabs[8]:
        display_action_tracker(st.session_state.meeting_data["date"])
    
    # Tab 10: Meeting Notes
    with tabs[9]:
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
    
    # Tab 11: Reports
    with tabs[10]:
        report_options = st.radio(
            "Report Type:",
            options=["Standard Report", "AI-Enhanced Executive Summary"],
            horizontal=True
        )
        
        if report_options == "Standard Report":
            display_report_generator(
                meeting_date=st.session_state.meeting_data["date"], 
                meeting_data=st.session_state.meeting_data
            )
        else:
            st.subheader("AI-Enhanced Executive Summary")
            st.info("This summary combines production data with AI analysis for executive review")
            
            if st.button("Generate Executive Summary", use_container_width=True):
                with st.spinner("Analyzing data and generating executive summary..."):
                    # Simply call the narrative summary function - it already provides what we need
                    generate_narrative_summary()

def show_welcome_screen():
    """Display welcome screen with demo introduction"""
    st.title("🏭 Manufacturing Operations Hub")
    st.subheader("AI-Enhanced Production Analytics Demo")
    
    st.markdown("""
    This demonstration showcases how AI can transform daily production meetings from lengthy report reviews into 
    focused decision sessions. The application features:
    
    - **Real-time KPIs and Metrics** - All the critical numbers at your fingertips
    - **Automated Analysis** - Let AI find patterns and insights in your data
    - **Root Cause Exploration** - Dig deeper into quality and production issues
    - **Predictive Insights** - See potential issues before they happen
    """)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.info("### BEFORE\n* 60-90 min manual report preparation\n* Reactive problem solving\n* Focus on what happened")
    
    with col2:
        st.success("### AFTER\n* Automatic data analysis\n* Proactive issue detection\n* Focus on why and what's next")
    
    with col3:
        st.button("Launch Production Meeting Demo", use_container_width=True, key="launch_demo",
                on_click=lambda: setattr(st.session_state, 'show_welcome', False))

# for testing
if __name__ == "__main__":
    # Set page config
    st.set_page_config(
        page_title="Manufacturing Operations Hub", 
        page_icon="🏭",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    if "show_welcome" not in st.session_state:
        st.session_state.show_welcome = True
    
    # Show either welcome screen or main application
    if st.session_state.show_welcome:
        show_welcome_screen()
    else:
        run_production_meeting()