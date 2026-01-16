"""
Production Meeting Dashboard - Daily lean meeting tool with AI-first analytics
"""

import streamlit as st
from datetime import datetime, timedelta

# Import shared modules
import sys
import os
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)
from app_factory.shared.database import DatabaseManager

# Import production meeting modules
from .dashboards import (
    production_summary_dashboard,
    equipment_status_dashboard,
    quality_dashboard,
    inventory_dashboard,
    add_root_cause_analysis,
)

from .ai_insights import (
    display_ai_insights_tab,
    provide_tab_insights,
    generate_predictive_insights
)
from .analysis_cache_manager import AnalysisCacheManager

# Initialize managers
db_manager = DatabaseManager()
cache_manager = AnalysisCacheManager()


def get_top_issues():
    """Query database for top issues to display in the AI summary card"""
    issues = []

    # Quality issues from last 14 days
    quality_query = """
        SELECT
            COUNT(*) as defect_count,
            AVG(d.Severity) as avg_severity,
            d.DefectType
        FROM Defects d
        JOIN QualityControl qc ON d.CheckID = qc.CheckID
        WHERE qc.Date >= date('now', '-14 day')
        GROUP BY d.DefectType
        ORDER BY defect_count DESC
        LIMIT 3
    """

    # Critical inventory
    inventory_query = """
        SELECT Name, Quantity, ReorderLevel,
               ROUND(100.0 * (ReorderLevel - Quantity) / ReorderLevel, 1) as shortage_pct
        FROM Inventory
        WHERE Quantity < ReorderLevel
        ORDER BY shortage_pct DESC
        LIMIT 3
    """

    # Equipment with most downtime
    equipment_query = """
        SELECT m.Name, m.Type, COUNT(d.DowntimeID) as downtime_events,
               SUM(d.Duration) as total_downtime_mins
        FROM Machines m
        JOIN Downtimes d ON m.MachineID = d.MachineID
        WHERE d.StartTime >= date('now', '-7 day')
        GROUP BY m.MachineID
        ORDER BY total_downtime_mins DESC
        LIMIT 3
    """

    try:
        # Get quality issues
        quality_result = db_manager.execute_query(quality_query)
        if quality_result.get('success') and quality_result.get('rows'):
            top_defect = quality_result['rows'][0]
            issues.append({
                'type': 'quality',
                'severity': 'high' if top_defect['avg_severity'] and top_defect['avg_severity'] > 3 else 'medium',
                'title': f"Quality: {top_defect['DefectType']}",
                'detail': f"{int(top_defect['defect_count'])} defects in last 14 days"
            })

        # Get inventory issues
        inventory_result = db_manager.execute_query(inventory_query)
        if inventory_result.get('success') and inventory_result.get('rows'):
            for row in inventory_result['rows']:
                issues.append({
                    'type': 'inventory',
                    'severity': 'high' if row['shortage_pct'] and row['shortage_pct'] > 50 else 'medium',
                    'title': f"Inventory: {row['Name']}",
                    'detail': f"{int(row['Quantity'])} units (reorder: {int(row['ReorderLevel'])})"
                })

        # Get equipment issues
        equipment_result = db_manager.execute_query(equipment_query)
        if equipment_result.get('success') and equipment_result.get('rows'):
            top_equipment = equipment_result['rows'][0]
            if top_equipment['total_downtime_mins'] and top_equipment['total_downtime_mins'] > 60:
                issues.append({
                    'type': 'equipment',
                    'severity': 'high' if top_equipment['total_downtime_mins'] > 300 else 'medium',
                    'title': f"Equipment: {top_equipment['Name']}",
                    'detail': f"{int(top_equipment['downtime_events'])} downtime events, {int(top_equipment['total_downtime_mins'])} mins total"
                })
    except Exception as e:
        pass  # Silently handle errors - issues panel is not critical

    return issues[:5]  # Return top 5 issues


def display_ai_summary_card():
    """Display AI summary card at top of dashboard with cached insights"""

    # Try to load cached analysis
    cached = cache_manager.get_latest_analysis(max_age_hours=48)

    with st.container():
        st.subheader("🤖 AI Daily Briefing")

        col1, col2 = st.columns([2, 1])

        with col1:
            if cached:
                generated_at = cached.get('generated_at', 'Unknown')
                st.caption(f"Last updated: {generated_at}")

                # Show executive summary if available
                analyses = cached.get('analyses', {})
                if 'executive_summary' in analyses:
                    summary = analyses['executive_summary'].get('analysis', '')
                    if summary:
                        st.markdown(summary[:500] + "..." if len(summary) > 500 else summary)
                elif 'production_overview' in analyses:
                    overview = analyses['production_overview'].get('analysis', '')
                    if overview:
                        st.markdown(overview[:500] + "..." if len(overview) > 500 else overview)
                else:
                    st.info("No cached analysis available. Use the 'Ask AI' tab to generate insights.")
            else:
                st.info("No cached analysis available. Use the 'Ask AI' tab to generate insights.")

        with col2:
            # Top Issues panel
            st.markdown("**⚠️ Top Issues Today**")
            issues = get_top_issues()

            if issues:
                for issue in issues[:3]:
                    severity_color = "🔴" if issue['severity'] == 'high' else "🟡"
                    st.markdown(f"{severity_color} **{issue['title']}**")
                    st.caption(issue['detail'])
            else:
                st.success("No critical issues detected")


def display_ask_ai_tab():
    """Display the Ask AI tab with text input for questions"""
    st.header("🤖 Ask AI")
    st.markdown("Ask questions about your production data and get AI-powered insights.")

    # Question input
    user_question = st.text_input(
        "What would you like to know?",
        placeholder="e.g., Why did quality drop last week? What's causing the bottleneck?",
        key="ai_question"
    )

    col1, col2 = st.columns([1, 4])

    with col1:
        ask_button = st.button("Ask AI", type="primary", use_container_width=True)

    with col2:
        # Quick question buttons
        quick_questions = [
            "What should we discuss today?",
            "What are the top quality issues?",
            "Which equipment needs attention?"
        ]
        quick_cols = st.columns(len(quick_questions))
        for i, q in enumerate(quick_questions):
            if quick_cols[i].button(q, key=f"quick_{i}"):
                user_question = q
                ask_button = True

    if ask_button and user_question:
        with st.spinner("Analyzing your question..."):
            # Use the existing AI insights function
            insights = provide_tab_insights("general", {"query": user_question})
            if insights:
                st.markdown("### Answer")
                st.markdown(insights)
            else:
                st.warning("Unable to generate insights. Please try again.")

    st.markdown("---")

    # Analysis options
    st.subheader("Detailed Analysis")

    analysis_type = st.radio(
        "Select analysis type:",
        options=["General Insights", "Predictive Analysis"],
        horizontal=True,
        key="analysis_type_radio"
    )

    if analysis_type == "General Insights":
        display_ai_insights_tab()
    else:
        generate_predictive_insights()


def run_production_meeting():
    """Main function for the Production Meeting Dashboard"""

    # Set up the page header
    st.title("📊 Daily Production Meeting")

    # Initialize session state
    if "meeting_data" not in st.session_state:
        st.session_state.meeting_data = {
            "date": datetime.now().strftime("%Y-%m-%d"),
        }

    # Simplified top control bar
    control_cols = st.columns([1, 1, 1, 1])

    with control_cols[0]:
        meeting_date = st.date_input(
            "Meeting Date",
            value=datetime.strptime(st.session_state.meeting_data["date"], "%Y-%m-%d"),
            key="meeting_date"
        )
        st.session_state.meeting_data["date"] = meeting_date.strftime("%Y-%m-%d")

    with control_cols[1]:
        # Time display
        st.write(f"⏰ {datetime.now().strftime('%H:%M')}")
        st.caption("Current time")

    with control_cols[2]:
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    with control_cols[3]:
        if st.button("🏠 Main Menu", use_container_width=True):
            st.session_state.app_mode = None
            st.rerun()

    # AI Summary Card at top
    display_ai_summary_card()

    st.markdown("---")

    # Simplified navigation tabs (removed Weekly, Productivity, Meeting Notes, Reports)
    tabs = st.tabs([
        "📈 Production",
        "🔧 Equipment",
        "⚠️ Quality",
        "📦 Inventory",
        "🔍 Root Cause",
        "🤖 Ask AI"
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

    # Tab 5: Root Cause Analysis
    with tabs[4]:
        add_root_cause_analysis()

    # Tab 6: Ask AI (renamed from AI Insights)
    with tabs[5]:
        display_ask_ai_tab()


def show_welcome_screen():
    """Display welcome screen with demo introduction"""
    st.title("🏭 Manufacturing Operations Hub")
    st.subheader("AI-Enhanced Production Analytics Demo")

    st.markdown("""
    This demonstration showcases how **agentic AI** can transform daily lean meetings:

    - **AI Daily Briefing** - Start each meeting with AI-generated insights
    - **Top Issues Detection** - AI identifies what needs attention
    - **Ask AI Anything** - Natural language questions about your data
    - **Predictive Analysis** - See potential issues before they happen
    """)

    col1, col2 = st.columns(2)

    with col1:
        st.error("### ❌ WITHOUT AI\n* 60-90 min report preparation\n* Manual data analysis\n* Reactive problem solving")

    with col2:
        st.success("### ✅ WITH AI\n* Instant AI-generated insights\n* Automated issue detection\n* Proactive recommendations")

    st.button("Launch Demo", use_container_width=True, key="launch_demo",
            on_click=lambda: setattr(st.session_state, 'show_welcome', False))


# for testing
if __name__ == "__main__":
    st.set_page_config(
        page_title="Manufacturing Operations Hub",
        page_icon="🏭",
        layout="wide",
        initial_sidebar_state="collapsed"
    )

    if "show_welcome" not in st.session_state:
        st.session_state.show_welcome = True

    if st.session_state.show_welcome:
        show_welcome_screen()
    else:
        run_production_meeting()
