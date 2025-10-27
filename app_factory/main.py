"""
Main entry point for the MES Demo Application
Allows selection between MES Chat and Production Meeting modes
"""

import streamlit as st
import os
import sys
from pathlib import Path

# Add the current directory to the path so we can import modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the app modules
from mes_chat.chat_interface import run_mes_chat
from production_meeting.dashboard import run_production_meeting

# Page configuration
st.set_page_config(
    page_title="Manufacturing Operations Hub",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    """Main application entry point"""
    
    # App selector logic
    if 'app_mode' not in st.session_state:
        st.session_state.app_mode = None
    
    # Run the selected app or show homepage
    if st.session_state.app_mode == "mes_chat":
        run_mes_chat()
    elif st.session_state.app_mode == "production_meeting":
        run_production_meeting()
    else:
        # Show homepage content only when no app is selected
        # Application header
        col1, col2 = st.columns([1, 5])
        
        with col1:
            st.image("https://upload.wikimedia.org/wikipedia/commons/9/93/Amazon_Web_Services_Logo.svg", width=80)
            
        with col2:
            st.title("🏭 Manufacturing Operations Hub")
        
        st.markdown("""
        Welcome to the Manufacturing Operations Hub for your e-bike manufacturing facility.
        Choose from the following applications:
        """)
        
        # Application selector using native Streamlit components
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("⚙️ MES Insight Chat")
            st.write("""
            Interactive chat interface for MES data analysis. Ask questions about production, inventory, 
            machine status, quality control, and more using natural language.
            
            **Use this when:** You need to analyze specific MES data or investigate issues.
            """)
            
            if st.button("Launch MES Chat", key="launch_mes", use_container_width=True):
                st.session_state.app_mode = "mes_chat"
                st.rerun()
        
        with col2:
            st.subheader("📊 Daily Production Meeting")
            st.write("""
            Structured interface for daily lean meetings with production KPIs, issue tracking, 
            and performance metrics focused on today's operations.
            
            **Use this when:** Running daily stand-up meetings, shift handovers, 
            or production status reviews.
            """)
            
            if st.button("Launch Production Meeting", key="launch_prod", use_container_width=True):
                st.session_state.app_mode = "production_meeting"
                st.rerun()

        # Footer
        st.divider()
        st.caption("E-bike Manufacturing Facility Demo • MES & Production Meeting Simulator")

if __name__ == "__main__":
    main()