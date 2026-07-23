"""
Production Meeting Dashboard - Daily lean meeting tool with AI-first analytics
"""

import streamlit as st
from datetime import datetime, timedelta

from app_factory.shared.database import DatabaseManager
from app_factory.shared.db_utils import days_ago

# Import production meeting modules
from .dashboards import (
    production_summary_dashboard,
    equipment_status_dashboard,
    quality_dashboard,
    inventory_dashboard,
    add_root_cause_analysis,
)

from .ai_insights import display_ai_insights_tab
from .analysis_cache_manager import AnalysisCacheManager


@st.cache_resource
def _get_db_manager() -> DatabaseManager:
    """Shared DatabaseManager instance across Streamlit reruns."""
    return DatabaseManager()


@st.cache_resource
def _get_cache_manager() -> AnalysisCacheManager:
    return AnalysisCacheManager()


db_manager = _get_db_manager()
cache_manager = _get_cache_manager()


@st.cache_data(ttl=300)
def get_top_issues():
    """Query database for top issues to display in the AI summary card."""
    issues = []

    # Calculate dates for parameterized queries
    fourteen_days_ago = days_ago(14)
    seven_days_ago = days_ago(7)

    # Quality issues from last 14 days
    quality_query = """
        SELECT
            COUNT(*) as defect_count,
            AVG(d.Severity) as avg_severity,
            d.DefectType
        FROM Defects d
        JOIN QualityControl qc ON d.CheckID = qc.CheckID
        WHERE qc.Date >= :fourteen_days_ago
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
               SUM(COALESCE(d.Duration,
                            (strftime('%s', 'now') - strftime('%s', d.StartTime)) / 60)) as total_downtime_mins
        FROM Machines m
        JOIN Downtimes d ON m.MachineID = d.MachineID
        WHERE d.StartTime >= :seven_days_ago
        GROUP BY m.MachineID
        ORDER BY total_downtime_mins DESC
        LIMIT 3
    """

    try:
        # Get quality issues
        quality_result = db_manager.execute_query(quality_query, {"fourteen_days_ago": fourteen_days_ago})
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
        equipment_result = db_manager.execute_query(equipment_query, {"seven_days_ago": seven_days_ago})
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


def extract_actionable_summary(raw_summary: str) -> str:
    """Extract only the actionable bullet points from AI-generated summary.

    The AI may include preamble text, metadata, and follow-up sections.
    This function extracts just the executive summary bullet points.
    """
    if not raw_summary:
        return ""

    lines = raw_summary.split('\n')
    actionable_lines = []
    in_actionable_section = False
    found_next_review = False

    for line in lines:
        stripped = line.strip()

        # Start capturing when we see bullet points with emoji indicators
        if stripped.startswith('•') and any(emoji in stripped for emoji in ['🔴', '🟠', '🟢']):
            in_actionable_section = True
            actionable_lines.append(line)
        # Also capture INTEGRATED INSIGHTS, OWNERS, NEXT REVIEW sections
        elif in_actionable_section and stripped.startswith('**') and any(
            keyword in stripped.upper() for keyword in ['INTEGRATED', 'OWNERS', 'NEXT REVIEW']
        ):
            if 'NEXT REVIEW' in stripped.upper():
                found_next_review = True
            actionable_lines.append(line)
        # Continue capturing lines that are part of the current section
        elif in_actionable_section and stripped and not stripped.startswith('#') and not stripped.startswith('---'):
            # Stop at metadata sections or follow-up action items
            if any(stop_phrase in stripped for stop_phrase in [
                'Meeting Action Items', 'Analysis Metadata', 'Original Query',
                'Processing Type', 'Coordination Level', 'FORMAT REQUIREMENTS',
                'Based on this analysis', 'following items should be tracked'
            ]):
                break
            # If we've seen NEXT REVIEW and hit a new section, stop
            if found_next_review and (stripped.startswith('##') or stripped.startswith('- [')):
                break
            actionable_lines.append(line)
        # Allow blank lines within the actionable section, but stop after NEXT REVIEW + blank
        elif in_actionable_section and not stripped:
            if found_next_review:
                break  # Stop at first blank line after NEXT REVIEW
            actionable_lines.append(line)

    # Clean up trailing blank lines
    while actionable_lines and not actionable_lines[-1].strip():
        actionable_lines.pop()

    return '\n'.join(actionable_lines)


def remove_status_emojis(text: str) -> str:
    """Remove status emojis from text for a more professional appearance."""
    # Replace status emojis with text indicators
    replacements = [
        ('🔴 ', '[CRITICAL] '),
        ('🟠 ', '[WARNING] '),
        ('🟢 ', '[OK] '),
        ('🔴', '[CRITICAL]'),
        ('🟠', '[WARNING]'),
        ('🟢', '[OK]'),
        ('📊 ', ''),
        ('📊', ''),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    return text


# Follow-up question the Investigate button pre-fills into MES Chat, per domain
_INVESTIGATE_PROMPTS = {
    'production': "Investigate this production issue from today's briefing: {headline}. Query the work order data to find the root cause and quantify the impact.",
    'quality': "Investigate this quality issue from today's briefing: {headline}. Analyze defect types, affected machines, and root causes in the quality data.",
    'equipment': "Investigate this equipment issue from today's briefing: {headline}. Check downtime history, OEE trends, and maintenance schedule for the machines involved.",
    'inventory': "Investigate this inventory issue from today's briefing: {headline}. Check stock levels, consumption rates, lead times, and supplier data.",
}


def _render_briefing_item(item: dict, key: str):
    """Render one structured briefing item as a colored callout with an Investigate button."""
    severity = item.get('severity', 'warning')
    domain = item.get('domain', 'production')
    headline = item.get('headline', '')
    action = item.get('action', '')

    body = f"**{domain.title()}** — {headline}"
    if action:
        body += f"\n\n→ {action}"

    col_text, col_btn = st.columns([5, 1])
    with col_text:
        if severity == 'critical':
            st.error(body, icon="🔴")
        elif severity == 'warning':
            st.warning(body, icon="🟠")
        else:
            st.success(body, icon="🟢")
    with col_btn:
        if st.button("Investigate", key=key, use_container_width=True):
            prompt = _INVESTIGATE_PROMPTS.get(domain, "Investigate: {headline}").format(headline=headline)
            st.session_state.switch_to_chat = prompt
            st.session_state.app_mode = "mes_chat"
            st.rerun()


_STATUS_BANNERS = {
    'critical': ("🔴 Plant status: CRITICAL — immediate action needed", st.error),
    'attention_needed': ("🟠 Plant status: ATTENTION NEEDED", st.warning),
    'normal': ("🟢 Plant status: NORMAL — no critical issues", st.success),
}


def display_ai_summary_card():
    """AI Daily Briefing — the hero of the dashboard, expanded by default."""

    cached = cache_manager.get_latest_analysis(max_age_hours=48)

    with st.expander("🤖 AI Daily Briefing", expanded=True):
        col1, col2 = st.columns([2, 1])

        with col1:
            if cached:
                analyses = cached.get('analyses', {})
                exec_entry = analyses.get('executive_summary', {})
                structured = exec_entry.get('structured')
                raw_summary = exec_entry.get('analysis', '')

                if structured:
                    # Overall status banner
                    banner_text, banner_fn = _STATUS_BANNERS.get(
                        structured.get('overall_status', 'attention_needed'),
                        _STATUS_BANNERS['attention_needed'],
                    )
                    banner_fn(banner_text)

                    # One colored callout per briefing item, critical first
                    severity_order = {'critical': 0, 'warning': 1, 'good': 2}
                    items = sorted(
                        structured.get('items', []),
                        key=lambda it: severity_order.get(it.get('severity'), 1),
                    )
                    for idx, item in enumerate(items):
                        _render_briefing_item(item, key=f"investigate_{idx}")

                    if structured.get('next_review'):
                        st.caption(f"**Next review:** {structured['next_review']}")
                elif raw_summary:
                    # Legacy free-text cache: extract bullets + strip emojis
                    exec_summary = extract_actionable_summary(raw_summary)
                    st.markdown(
                        remove_status_emojis(exec_summary) if exec_summary else raw_summary
                    )
                else:
                    st.info("Executive summary not available. Run `make run-analysis` to generate fresh insights.")

                # AWS story caption
                generated_at = cached.get('generated_at', '')
                exec_time = cached.get('total_execution_time', 0)
                num_analyses = len(analyses)
                time_str = generated_at[11:16] if len(generated_at) >= 16 else generated_at
                st.caption(
                    f"Powered by **Amazon Bedrock** (Claude Sonnet 5) + **Strands Agents** — "
                    f"{num_analyses} agents analyzed 11 MES tables in {exec_time:.0f}s "
                    f"(overnight run at {time_str})"
                )
            else:
                st.info("No cached analysis available. Run `make run-analysis` to generate insights.")

        with col2:
            # Deterministic SQL watchlist — labeled so it isn't mistaken for AI output
            st.markdown("**Watchlist** ")
            st.caption("Rule-based SQL checks (not AI)")
            issues = get_top_issues()

            if issues:
                for issue in issues[:3]:
                    severity_label = "[CRITICAL]" if issue['severity'] == 'high' else "[WARNING]"
                    st.markdown(f"{severity_label} **{issue['title']}**")
                    st.caption(issue['detail'])
            else:
                st.success("No critical issues detected")


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

    # Each tab body is a @st.fragment so widget interactions inside one tab
    # don't trigger a full page rerun (which would re-execute all 6 tabs).
    @st.fragment
    def _ai_insights_tab():
        display_ai_insights_tab()

    @st.fragment
    def _production_tab():
        production_summary_dashboard()

    @st.fragment
    def _equipment_tab():
        equipment_status_dashboard()

    @st.fragment
    def _quality_tab():
        quality_dashboard()

    @st.fragment
    def _inventory_tab():
        inventory_dashboard()

    @st.fragment
    def _root_cause_tab():
        add_root_cause_analysis()

    tabs = st.tabs([
        "🤖 AI Insights",
        "📈 Production",
        "🔧 Equipment",
        "⚠️ Quality",
        "📦 Inventory",
        "🔍 Root Cause",
    ])

    with tabs[0]:
        _ai_insights_tab()
    with tabs[1]:
        _production_tab()
    with tabs[2]:
        _equipment_tab()
    with tabs[3]:
        _quality_tab()
    with tabs[4]:
        _inventory_tab()
    with tabs[5]:
        _root_cause_tab()


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

    # Pull live numbers from last night's agent run when available
    cached = cache_manager.get_latest_analysis(max_age_hours=48)
    if cached:
        exec_time = cached.get('total_execution_time', 0)
        num_analyses = len(cached.get('analyses', {}))
        with_ai_text = (
            f"### ✅ WITH AI\n"
            f"* Last night **{num_analyses} agents** produced today's briefing in **{exec_time:.0f} seconds**\n"
            f"* Issues flagged automatically before the meeting started\n"
            f"* Every finding one click away from a deep-dive agent"
        )
    else:
        with_ai_text = "### ✅ WITH AI\n* Instant AI-generated insights\n* Automated issue detection\n* Proactive recommendations"

    with col1:
        st.error("### ❌ WITHOUT AI\n* 60-90 min report preparation\n* Manual data analysis\n* Reactive problem solving")

    with col2:
        st.success(with_ai_text)

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
