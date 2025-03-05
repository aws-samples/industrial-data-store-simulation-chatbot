"""
AI-powered insights and analysis for the Production Meeting
"""

import streamlit as st
import pandas as pd
import json
from datetime import datetime, timedelta
import time

from shared.database import DatabaseManager
from shared.bedrock_utils import get_bedrock_client, get_available_bedrock_models

# Initialize database manager
db_manager = DatabaseManager()

def generate_ai_insight(context, query=None, dashboard_data=None, model_id=None, temperature=0.1):
    """
    Generate AI insights based on dashboard data
    
    Args:
        context (str): The context for the AI (production, quality, etc.)
        query (str, optional): Specific question to answer, if any
        dashboard_data (dict, optional): Preloaded dashboard data
        model_id (str, optional): Bedrock model ID to use
        temperature (float, optional): Temperature for generation
        
    Returns:
        str: AI-generated insight
    """
    # Get client
    client = get_bedrock_client()
    
    # Get model ID if not provided
    if not model_id:
        # Default to a lightweight model like Claude 3 Haiku or Nova Micro
        available_models = get_available_bedrock_models()
        preferred_models = ["anthropic.claude-3-haiku-20240307-v1:0", "us.amazon.nova-micro-v1:0"]
        
        # Find first available preferred model
        for model in preferred_models:
            if any(m['id'] == model for m in available_models):
                model_id = model
                break
        
        # If no preferred model found, use first available
        if not model_id and available_models:
            model_id = available_models[0]['id']
        
        # Fallback default
        if not model_id:
            model_id = "anthropic.claude-3-haiku-20240307-v1:0"
    
    # Collect data for the specific context if not provided
    if not dashboard_data:
        dashboard_data = {}
        
        if context in ['production', 'summary', 'all']:
            # Get production data
            yesterday_data = db_manager.get_daily_production_summary(days_back=1)
            if not yesterday_data.empty:
                dashboard_data['production'] = yesterday_data.to_dict(orient='records')
                
            # Get work order status
            work_order_status = db_manager.get_work_order_status()
            if not work_order_status.empty:
                dashboard_data['work_orders'] = work_order_status.to_dict(orient='records')
        
        if context in ['machines', 'equipment', 'all']:
            # Get machine status
            machine_status = db_manager.get_machine_status_summary()
            if not machine_status.empty:
                dashboard_data['machines'] = machine_status.to_dict(orient='records')
                
            # Get upcoming maintenance
            maintenance_data = db_manager.get_upcoming_maintenance(days_ahead=7)
            if not maintenance_data.empty:
                dashboard_data['maintenance'] = maintenance_data.to_dict(orient='records')
        
        if context in ['quality', 'all']:
            # Get quality data
            quality_data = db_manager.get_quality_summary(days_back=1, range_days=30)
            if not quality_data.empty:
                dashboard_data['quality'] = quality_data.to_dict(orient='records')
                
            # Get top defects
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
                qc.Date >= date('now', '-30 day')
            GROUP BY 
                d.DefectType
            ORDER BY 
                DefectCount DESC
            LIMIT 10
            """
            
            result = db_manager.execute_query(defects_query)
            if result["success"] and result["row_count"] > 0:
                dashboard_data['defects'] = result["rows"]
        
        if context in ['inventory', 'all']:
            # Get inventory alerts
            inventory_alerts = db_manager.get_inventory_alerts()
            if not inventory_alerts.empty:
                dashboard_data['inventory_alerts'] = inventory_alerts.to_dict(orient='records')
    
    # Create prompt for the model based on context
    if query:
        # User-provided query
        prompt = f"""
        You are an AI Manufacturing Analyst for an e-bike production facility. Based on the following manufacturing data, 
        please answer this specific question:
        
        QUESTION: {query}
        
        DATA:
        {json.dumps(dashboard_data, indent=2)}
        
        Provide a concise, informative, and fact-based answer focusing on the most important insights 
        related to the question. If the data doesn't provide sufficient information to answer the question, 
        clearly state what's missing. Use bullet points where appropriate.
        """
    else:
        # Generate context-specific insights
        if context == 'production':
            prompt = """
            You are an AI Manufacturing Analyst for an e-bike production facility. Based on the production data provided,
            give a short, insightful analysis of:
            
            1. Production performance against targets
            2. Key bottlenecks or issues to be aware of
            3. Recommendations for improving throughput or efficiency
            
            Be concise but specific. Use bullet points for key insights. Focus on actionable information
            and patterns rather than just repeating the data.
            """
            
        elif context == 'machines':
            prompt = """
            You are an AI Manufacturing Analyst for an e-bike production facility. Based on the equipment data provided,
            give a short, insightful analysis of:
            
            1. Machine availability and performance
            2. Critical maintenance issues or upcoming concerns
            3. Recommendations for improving equipment reliability and efficiency
            
            Be concise but specific. Use bullet points for key insights. Focus on actionable information
            and patterns rather than just repeating the data.
            """
            
        elif context == 'quality':
            prompt = """
            You are an AI Manufacturing Analyst for an e-bike production facility. Based on the quality data provided,
            give a short, insightful analysis of:
            
            1. Quality metrics and defect patterns
            2. Critical quality issues to address
            3. Recommendations for improving quality and reducing defects
            
            Be concise but specific. Use bullet points for key insights. Focus on actionable information
            and patterns rather than just repeating the data.
            """
            
        elif context == 'inventory':
            prompt = """
            You are an AI Manufacturing Analyst for an e-bike production facility. Based on the inventory data provided,
            give a short, insightful analysis of:
            
            1. Critical inventory shortages or concerns
            2. Inventory trends and reordering priorities
            3. Recommendations for inventory management
            
            Be concise but specific. Use bullet points for key insights. Focus on actionable information
            and patterns rather than just repeating the data.
            """
            
        elif context == 'summary':
            prompt = """
            You are an AI Manufacturing Analyst for an e-bike production facility. Based on all the data provided,
            give a concise daily production meeting summary covering:
            
            1. Overall production status and key metrics
            2. Critical issues requiring immediate attention
            3. Top recommendations for today's focus
            
            Be very concise - this should be readable in under 30 seconds. Use bullet points for key insights.
            Focus on actionable information a production manager needs to know right now.
            """
            
        else:  # 'all' or any other value
            prompt = """
            You are an AI Manufacturing Analyst for an e-bike production facility. Based on all the data provided,
            give a comprehensive analysis of the current manufacturing operations, including:
            
            1. Production performance and key metrics
            2. Equipment status and maintenance concerns
            3. Quality issues and defect patterns
            4. Inventory status and potential shortages
            5. Recommended actions and priorities
            
            Be concise but thorough. Use bullet points for key insights. Focus on actionable information
            and patterns rather than just repeating the data.
            """
    
    # Add data to prompt
    if context != 'summary':
        prompt += f"\n\nDATA:\n{json.dumps(dashboard_data, indent=2)}"
    
    # Call Bedrock model
    try:
        with st.spinner("Generating AI insights..."):
            start_time = time.time()
            
            response = client.converse(
                modelId=model_id,
                messages=[
                    {"role": "user", "content": [{"text": prompt}]}
                ],
                inferenceConfig={
                    "maxTokens": 4096,
                    "temperature": temperature
                }
            )
            
            # Extract response text
            output = ""
            for content in response["output"]["message"]["content"]:
                if "text" in content:
                    output += content["text"]
            
            elapsed_time = time.time() - start_time
            
            # Add subtle attribution
            output += f"\n\n<small><i>Generated in {elapsed_time:.1f}s</i></small>"
            
            return output
            
    except Exception as e:
        return f"Error generating insights: {str(e)}\n\nPlease try again or check your AWS credentials and permissions."

def display_ai_insights_tab():
    """Display the AI Insights tab in the production meeting"""
    st.header("🤖 AI Insights & Analysis")
    
    col1, col2 = st.columns([3, 1])
    
    with col2:
        # Model selection sidebar
        st.subheader("AI Settings")
        
        # Get available models
        try:
            available_models = get_available_bedrock_models()
            
            # Format model options
            model_options = []
            model_ids = []
            
            for model in available_models:
                model_name = f"{model['provider']} - {model['name']}"
                model_options.append(model_name)
                model_ids.append(model['id'])
            
            # Default to lightweight models
            default_model = "anthropic.claude-3-haiku-20240307-v1:0"
            default_index = 0
            
            if default_model in model_ids:
                default_index = model_ids.index(default_model)
            
            selected_option = st.selectbox(
                'AI Model:',
                options=model_options,
                index=default_index if model_options else 0,
                help="Select model for generating insights"
            )
            
            if model_options:
                selected_index = model_options.index(selected_option)
                model_id = model_ids[selected_index]
            else:
                model_id = default_model
                
        except Exception as e:
            st.warning(f"Could not load available models. Using default model.")
            model_id = "anthropic.claude-3-haiku-20240307-v1:0"
        
        # Temperature control
        temperature = st.slider(
            "Temperature",
            min_value=0.0,
            max_value=1.0,
            value=0.1,
            step=0.1,
            help="Lower values produce more consistent output, higher values more creative"
        )
        
        # Context selector
        context = st.radio(
            "Analysis Focus",
            options=["Daily Summary", "Production", "Equipment", "Quality", "Inventory", "Comprehensive"],
            index=0,
        )
        
        # Map selection to context value
        context_map = {
            "Daily Summary": "summary",
            "Production": "production",
            "Equipment": "machines",
            "Quality": "quality",
            "Inventory": "inventory",
            "Comprehensive": "all"
        }
        
        selected_context = context_map[context]
        
        # Generate button
        generate_button = st.button("Generate Insights", use_container_width=True)
    
    with col1:
        # Custom query section
        st.subheader("Ask a specific question")
        
        custom_query = st.text_input(
            "Ask about production data",
            placeholder="Example: What are the top quality issues we should focus on today?",
            help="Ask a specific question about production, quality, equipment, or inventory"
        )
        
        query_button = st.button("Ask Question", use_container_width=True)
        
        # Store which tab should be active
        if "active_ai_tab" not in st.session_state:
            st.session_state.active_ai_tab = 0
            
        # Set active tab when buttons are clicked
        if generate_button:
            st.session_state.active_ai_tab = 0
        if query_button and custom_query:
            st.session_state.active_ai_tab = 1
            
        # Tab selection
        tabs = st.tabs(["AI Insights", "Custom Query Results", "Meeting Summary"])
        
        # Tab 1: Generated insights
        with tabs[0]:
            if "ai_insights" not in st.session_state:
                st.session_state.ai_insights = ""
                
            if generate_button:
                with st.spinner("Generating insights..."):
                    insight = generate_ai_insight(
                        context=selected_context,
                        model_id=model_id,
                        temperature=temperature
                    )
                    st.session_state.ai_insights = insight
            
            if st.session_state.active_ai_tab == 0:
                if st.session_state.ai_insights:
                    st.markdown(st.session_state.ai_insights, unsafe_allow_html=True)
                else:
                    st.info("Click 'Generate Insights' to create an AI analysis of the production data")
        
        # Tab 2: Custom query results
        with tabs[1]:
            if "custom_query_result" not in st.session_state:
                st.session_state.custom_query_result = ""
                st.session_state.custom_query_text = ""
                
            if query_button and custom_query:
                with st.spinner(f"Analyzing: {custom_query}"):
                    result = generate_ai_insight(
                        context="all",  # For queries, analyze all available data
                        query=custom_query,
                        model_id=model_id,
                        temperature=temperature
                    )
                    st.session_state.custom_query_result = result
                    st.session_state.custom_query_text = custom_query
            
            if st.session_state.active_ai_tab == 1:
                if st.session_state.custom_query_result:
                    st.success("Query processed successfully")
                    st.subheader(f"Query: {st.session_state.custom_query_text}")
                    st.markdown(st.session_state.custom_query_result, unsafe_allow_html=True)
                else:
                    st.info("Enter a question and click 'Ask Question' to get insights on specific aspects of the production data")
        
        # Tab 3: Meeting summary
        with tabs[2]:
            if "meeting_summary" not in st.session_state:
                st.session_state.meeting_summary = ""
                
            # Generate meeting summary button
            summary_button = st.button("Generate Meeting Summary", use_container_width=True)
            
            if summary_button:
                with st.spinner("Generating comprehensive meeting summary..."):
                    summary = generate_ai_insight(
                        context="summary",
                        model_id=model_id,
                        temperature=temperature
                    )
                    st.session_state.meeting_summary = summary
                    st.session_state.active_ai_tab = 2
            
            if st.session_state.active_ai_tab == 2:
                if st.session_state.meeting_summary:
                    st.markdown(st.session_state.meeting_summary, unsafe_allow_html=True)
                    
                    # Options to export or use the summary
                    st.download_button(
                        "Download Summary",
                        st.session_state.meeting_summary,
                        f"meeting_summary_{datetime.now().strftime('%Y%m%d')}.md",
                        "text/markdown",
                        key="download_ai_summary"
                    )
                    
                    if st.button("Copy to Meeting Notes", use_container_width=True):
                        if "meeting_data" in st.session_state:
                            current_notes = st.session_state.meeting_data.get("notes", "")
                            ai_summary = st.session_state.meeting_summary.split("<small>")[0].strip()  # Remove timing info
                            
                            # Add the AI summary to existing notes
                            if current_notes:
                                separator = "\n\n--- AI Generated Summary ---\n\n"
                                if separator not in current_notes:
                                    new_notes = current_notes + separator + ai_summary
                                else:
                                    # Replace existing AI summary
                                    parts = current_notes.split(separator)
                                    new_notes = parts[0] + separator + ai_summary
                            else:
                                new_notes = "--- AI Generated Summary ---\n\n" + ai_summary
                            
                            st.session_state.meeting_data["notes"] = new_notes
                            st.success("AI summary added to meeting notes!")
                else:
                    st.info("Click 'Generate Meeting Summary' to create a comprehensive summary for your production meeting")

def provide_tab_insights(tab_name):
    """
    Generate AI insights for a specific dashboard tab
    
    Args:
        tab_name (str): Name of the tab (production, machines, quality, inventory)
    """
    # Skip if AI generation is disabled
    if not st.session_state.get("enable_tab_insights", True):
        return
    
    # Generate insights
    with st.expander("🤖 AI Insights for this dashboard", expanded=False):
        if f"{tab_name}_insights" not in st.session_state:
            st.session_state[f"{tab_name}_insights"] = ""
            
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.info("AI can analyze this data to highlight important patterns and issues")
            
            with col2:
                generate_button = st.button(f"Generate Insights", key=f"gen_{tab_name}", use_container_width=True)
            
            if generate_button:
                with st.spinner(f"Analyzing {tab_name} data..."):
                    insight = generate_ai_insight(context=tab_name)
                    st.session_state[f"{tab_name}_insights"] = insight
                    st.rerun()
        else:
            # Show existing insights
            st.markdown(st.session_state[f"{tab_name}_insights"], unsafe_allow_html=True)
            
            # Allow regeneration
            if st.button(f"Regenerate Insights", key=f"regen_{tab_name}", use_container_width=True):
                with st.spinner(f"Analyzing {tab_name} data..."):
                    insight = generate_ai_insight(context=tab_name)
                    st.session_state[f"{tab_name}_insights"] = insight
                    st.rerun()

if __name__ == "__main__":
    # Test directly
    st.set_page_config(page_title="AI Insights Test", layout="wide")
    st.title("AI Insights Test")
    display_ai_insights_tab()