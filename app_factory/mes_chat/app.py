"""MES Chatbot application - adapted from the original Chat.py"""

import json
import logging
import os
import time
import concurrent.futures
from datetime import datetime
from pathlib import Path

import streamlit as st
import pandas as pd
from dotenv import load_dotenv
import plotly.express as px

# Import shared modules
from shared.database import DatabaseManager, get_tool_config
from shared.bedrock_utils import get_bedrock_client, get_available_bedrock_models

# Configuration
load_dotenv()
proj_dir = os.path.abspath('')
db_path = os.path.join(proj_dir, 'mes.db')

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize tools
db_tool = DatabaseManager(db_path)
tool_config = get_tool_config()

# Function to convert dataframe to CSV for download
def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

# Function to execute query with timeout
def execute_query_with_timeout(db_tool, sql_query, timeout=60):
    """Execute a query with a timeout to prevent long-running queries"""
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(db_tool.execute_query, sql_query)
        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            executor._threads.clear()
            concurrent.futures.thread._threads_queues.clear()
            return {
                "success": False,
                "error": f"Query execution timed out after {timeout} seconds. Try a more specific or optimized query."
            }

# Function to detect chart-worthy data in result
def detect_chart_opportunity(df):
    """Detect if the data would benefit from visualization"""
    if len(df) < 2 or len(df.columns) < 2:
        return False
    
    # Check for numeric columns that might be good for plotting
    numeric_cols = df.select_dtypes(include=['number']).columns
    if len(numeric_cols) == 0:
        return False
    
    # Check for potential dimension columns (strings, dates, etc.)
    dimension_cols = df.select_dtypes(exclude=['number']).columns
    if len(dimension_cols) == 0:
        return False
    
    # Check if we have enough rows to make a meaningful chart
    if len(df) < 3:
        return False
    
    return True

# Function to create appropriate chart
def create_chart(df):
    """Create an appropriate chart based on the data structure"""
    # Identify potential dimension and measure columns
    numeric_cols = df.select_dtypes(include=['number']).columns
    dimension_cols = df.select_dtypes(exclude=['number']).columns
    
    if len(dimension_cols) == 0 or len(numeric_cols) == 0:
        return None
    
    # Choose dimension column - prefer columns with "Date", "Time", "Name", "ID" in the name
    dimension_col = None
    for col in dimension_cols:
        col_lower = col.lower()
        if any(term in col_lower for term in ["date", "time", "day", "month", "year"]):
            dimension_col = col
            break
    if dimension_col is None:
        for col in dimension_cols:
            col_lower = col.lower()
            if any(term in col_lower for term in ["name", "id", "type", "category"]):
                dimension_col = col
                break
    if dimension_col is None:
        dimension_col = dimension_cols[0]
    
    # Choose measure column - prefer aggregated values like "count", "total", "sum", "avg"
    measure_col = None
    for col in numeric_cols:
        col_lower = col.lower()
        if any(term in col_lower for term in ["count", "total", "sum", "avg", "rate", "percent"]):
            measure_col = col
            break
    if measure_col is None:
        measure_col = numeric_cols[0]
    
    # Determine chart type based on data characteristics
    if len(df) <= 10:  # Small number of categories
        if "percent" in measure_col.lower() or "rate" in measure_col.lower():
            # Create a pie chart for percentage data
            fig = px.pie(df, names=dimension_col, values=measure_col, title=f"{measure_col} by {dimension_col}")
        else:
            # Create a bar chart
            fig = px.bar(df, x=dimension_col, y=measure_col, title=f"{measure_col} by {dimension_col}")
    else:
        # Check if dimension might be time-based
        if any(term in dimension_col.lower() for term in ["date", "time", "day", "month", "year"]):
            try:
                # Try to convert to datetime for a time series chart
                df[dimension_col] = pd.to_datetime(df[dimension_col])
                fig = px.line(df, x=dimension_col, y=measure_col, title=f"{measure_col} over Time")
            except:
                # Fall back to bar chart if conversion fails
                fig = px.bar(df, x=dimension_col, y=measure_col, title=f"{measure_col} by {dimension_col}")
        else:
            # Default to bar chart with scrolling for many categories
            fig = px.bar(df, x=dimension_col, y=measure_col, title=f"{measure_col} by {dimension_col}")
            fig.update_layout(xaxis={'categoryorder':'total descending'})
    
    # Improve chart appearance
    fig.update_layout(
        template="plotly_white",
        xaxis_title=dimension_col,
        yaxis_title=measure_col,
        legend_title="Legend",
        height=400
    )
    
    return fig

def has_retrieved_schema(conversation):
    """Check if the model has already retrieved the schema"""
    for message in conversation:
        if message["role"] == "user" and len(message["content"]) > 0:
            for content in message["content"]:
                if "toolResult" in content:
                    tool_result = content["toolResult"]
                    # Find tool results where schema was returned successfully
                    if tool_result.get("toolUseId", "").startswith("tooluse_") and "status" not in tool_result:
                        for content_item in tool_result.get("content", []):
                            if "json" in content_item:
                                # This appears to be schema data
                                return True
    
    return False

def enforce_schema_first(response, client, model_id, temperature, conversation):
    """Enforce that get_schema is called before execute_sql"""
    
    if response["stopReason"] == "tool_use":
        tool_requests = response["output"]["message"]["content"]
        
        # Check if the model is trying to execute SQL without getting schema first
        for tool_request in tool_requests:
            if "toolUse" in tool_request:
                tool_use = tool_request["toolUse"]
                
                # If trying to execute SQL as first tool, redirect to get schema
                if tool_use["name"] == "execute_sql" and not has_retrieved_schema(conversation):
                    logger.warning("Model attempted to execute SQL without getting schema first. Redirecting to get schema.")
                    
                    # Add the assistant message to the conversation
                    conversation.append(response["output"]["message"])
                    
                    # Create a tool error response that instructs to get schema first
                    tool_result = {
                        "toolUseId": tool_use["toolUseId"],
                        "content": [{"text": "Error: You must get the database schema first to understand the available tables and columns before executing SQL queries."}],
                        "status": "error"
                    }
                    
                    tool_result_message = {
                        "role": "user",
                        "content": [
                            {
                                "toolResult": tool_result
                            }
                        ]
                    }
                    conversation.append(tool_result_message)
                    
                    # Let the model try again
                    new_response = client.converse(
                        modelId=model_id,
                        messages=conversation,
                        toolConfig=tool_config,
                        inferenceConfig={
                            "maxTokens": 4096,
                            "temperature": temperature
                        }
                    )
                    
                    return new_response, conversation
    
    return response, conversation

# Define a function to handle tool requests
def handle_tool_request(client, tool, model_id, temperature, conversation, query_timeout=60):
    """Handle tool requests from the model"""
    tool_use = tool["toolUse"]
    tool_use_id = tool_use["toolUseId"]
    tool_name = tool_use["name"]
    
    logger.info(f"Tool request received: {tool_name}, ID: {tool_use_id}")
    
    # Store tool responses for later display in the assistant message
    tool_response = {
        "type": tool_name,
        "data": None
    }
    
    # Execute the appropriate tool
    if tool_name == "execute_sql":
        sql_query = tool_use["input"]["sql_query"]
        
        # Save SQL for display
        tool_response["sql_query"] = sql_query
        
        # Execute the SQL query with timeout
        start_time = time.time()
        result = execute_query_with_timeout(db_tool, sql_query, timeout=query_timeout)
        elapsed_time = time.time() - start_time
        
        if result["success"]:
            tool_response["success"] = True
            tool_response["execution_time"] = elapsed_time
            tool_response["row_count"] = result["row_count"]
            
            # Convert to dataframe for display
            if result["row_count"] > 0:
                df = pd.DataFrame(result["rows"])
                tool_response["dataframe"] = df
                
                # Check if data is suitable for visualization
                if detect_chart_opportunity(df):
                    try:
                        chart = create_chart(df)
                        if chart:
                            tool_response["chart"] = chart
                    except Exception as e:
                        logger.error(f"Error creating chart: {e}")
                
                # Save the dataframe as part of the conversation for reference
                st.session_state.last_query_result = df
                
                # Add to query history
                st.session_state.query_history.append({
                    "timestamp": datetime.now(),
                    "sql": sql_query,
                    "result": df,
                    "row_count": result["row_count"]
                })
            
            # Prepare the tool result response
            tool_result = {
                "toolUseId": tool_use_id,
                "content": [{"json": result}]
            }
        else:
            tool_response["success"] = False
            tool_response["error"] = result["error"]
            tool_response["execution_time"] = elapsed_time
            
            # Prepare the error response
            tool_result = {
                "toolUseId": tool_use_id,
                "content": [{"text": f"Error executing SQL: {result['error']}"}],
                "status": "error"
            }
    
    elif tool_name == "get_schema":
        # Get the database schema
        schema = db_tool.get_schema()
        
        # Save schema info for display
        # Filter out metadata entry when counting columns
        total_tables = len([k for k in schema.keys() if k != "__metadata__"])
        total_columns = sum(len(table_info.get("columns", [])) 
                          for table_name, table_info in schema.items() 
                          if table_name != "__metadata__")
        
        tool_response["data"] = {
            "total_tables": total_tables,
            "total_columns": total_columns,
            "schema": schema
        }
        
        # Prepare the tool result response
        tool_result = {
            "toolUseId": tool_use_id,
            "content": [{"json": schema}]
        }
    
    else:
        # Unknown tool
        logger.error(f"Unknown tool requested: {tool_name}")
        
        tool_response["success"] = False
        tool_response["error"] = f"Unknown tool: {tool_name}"
        
        tool_result = {
            "toolUseId": tool_use_id,
            "content": [{"text": f"Unknown tool: {tool_name}"}],
            "status": "error"
        }
    
    # Add the tool result to the conversation
    tool_result_message = {
        "role": "user",
        "content": [
            {
                "toolResult": tool_result
            }
        ]
    }
    conversation.append(tool_result_message)
    
    # Send the tool result to the model
    response = client.converse(
        modelId=model_id,
        messages=conversation,
        toolConfig=tool_config,
        inferenceConfig={
            "maxTokens": 4096,
            "temperature": temperature
        }
    )
    
    return response, conversation, tool_response

# Define a function to reset the chat
def reset_chat():
    """Reset the chat state"""
    st.session_state.messages = [{"role": "assistant", "content": "Welcome to MES Insight Chat! How can I help you analyze your manufacturing data today?"}]
    st.session_state.model_conversation = []
    st.session_state.last_query_result = None

def run_mes_chat():
    """Main function to run the MES chat interface"""
    
    # Page configuration
    st.header(":brain: MES Insight Chat :brain:")
    st.markdown("""
    This interactive chatbot helps you analyze data from our Manufacturing Execution System (MES).
    Ask questions about production processes, inventory, machine status, quality control, and more.
    """)
    
    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "Welcome to MES Insight Chat! How can I help you analyze your manufacturing data today?"}]
    
    if "model_conversation" not in st.session_state:
        # This will store the messages in the format needed for the Bedrock converse API
        st.session_state.model_conversation = []
        
    if "last_query_result" not in st.session_state:
        # This will store the last query result for reference
        st.session_state.last_query_result = None
        
    if "query_history" not in st.session_state:
        # Store history of queries and results
        st.session_state.query_history = []
    
    # Split layout into sidebar and main content
    # Sidebar configuration
    with st.sidebar:
        st.subheader("⚙️ MES Insight Settings")
        
        # Reset chat button
        st.button("🔄 Reset Chat", on_click=reset_chat, use_container_width=True)
        
        # Return to main menu button
        if st.button("🏠 Return to Main Menu", use_container_width=True):
            st.session_state.app_mode = None
            st.experimental_rerun()
        
        st.divider()
        
        # Model settings
        st.subheader("Model Configuration")
        temperature = st.slider(
            label='Temperature',
            min_value=0.0,
            max_value=1.0,
            value=0.1,
            step=0.01,
            help="Higher values make output more creative, lower values more deterministic",
            key='temperature'
        )
        
        # Get available bedrock models with tool use capability
        try:
            # Get all available models that support tool use
            available_models = get_available_bedrock_models()
            
            # Format models for display in selectbox
            model_options = []
            model_ids = []
            
            # Group models by provider
            models_by_provider = {}
            for model in available_models:
                provider = model['provider']
                if provider not in models_by_provider:
                    models_by_provider[provider] = []
                models_by_provider[provider].append(model)
            
            # Create formatted options with provider groups
            for provider in sorted(models_by_provider.keys()):
                for model in models_by_provider[provider]:
                    # Format as "Provider - Model Name"
                    display_name = f"{provider} - {model['name']}"
                    model_options.append(display_name)
                    model_ids.append(model['id'])
            
            # If no models found, provide sensible defaults
            if not model_options:
                model_options = ["Anthropic - Claude 3 Haiku", "Anthropic - Claude 3 Sonnet", 
                                "Amazon - Nova Micro", "Amazon - Nova Lite"]
                model_ids = ["anthropic.claude-3-haiku-20240307-v1:0", "anthropic.claude-3-sonnet-20240229-v1:0",
                            "us.amazon.nova-micro-v1:0", "us.amazon.nova-lite-v1:0"]
            
            # Find the default model to select (prefer Claude 3 Haiku if available)
            default_index = 0  # Default to first model if preferred models not found
            preferred_models = ["anthropic.claude-3-haiku-20240307-v1:0", "us.amazon.nova-micro-v1:0"]
            
            for preferred_id in preferred_models:
                if preferred_id in model_ids:
                    default_index = model_ids.index(preferred_id)
                    break
            
            # Present model selection to user
            selected_option = st.selectbox(
                'Select AI Model:',
                options=model_options,
                index=default_index,
                key='model_display',
                help="Select from models that support tool use and are enabled for your account"
            )
            
            # Get the actual model ID from the selected option
            selected_index = model_options.index(selected_option)
            model_id = model_ids[selected_index]
            
        except Exception as e:
            logging.error(f"Error setting up model selection: {e}")
            # Fallback to static model selection
            model_id = st.selectbox(
                'Select AI Model:',
                ["anthropic.claude-3-haiku-20240307-v1:0", 
                "anthropic.claude-3-sonnet-20240229-v1:0",
                "us.amazon.nova-micro-v1:0", 
                "us.amazon.nova-lite-v1:0", 
                "us.amazon.nova-pro-v1:0"],
                index=0,
                key='model_id',
                help="Different models have different capabilities and speeds"
            )
        
        query_timeout = st.slider(
            label='Query Timeout (seconds)',
            min_value=10,
            max_value=120,
            value=60,
            step=5,
            help="Maximum time allowed for SQL queries to execute",
            key='query_timeout'
        )
        
        st.divider()
        
        # Show query history
        if st.session_state.query_history:
            st.subheader("Recent Queries")
            for i, query in enumerate(st.session_state.query_history[-5:]):
                with st.expander(f"Query {i+1}: {query['row_count']} rows", expanded=False):
                    st.code(query['sql'], language="sql")
                    st.text(f"Time: {query['timestamp'].strftime('%H:%M:%S')}")
        
        st.divider()
        
        # About section
        with st.expander("ℹ️ About MES Insight Chat"):
            st.markdown("""
            This chat interface connects to a Manufacturing Execution System (MES) database 
            for an e-bike manufacturer. It allows you to query and analyze:
            
            - Production work orders and schedules
            - Inventory levels and material consumption
            - Machine performance and maintenance
            - Quality control metrics and defects
            - Employee productivity and assignments
            
            The system uses AI to translate your natural language questions into SQL 
            queries that retrieve the relevant data from the MES database.
            """)
    
    # Main panel with chat interface
    main_col = st.container()
    
    with main_col:
        # Load example questions
        try:
            questions_path = Path(__file__).parent.parent / 'data' / 'sample_questions.json'
            if not questions_path.exists():
                questions_path = Path('sample_questions.json')  # Fallback to original location
                
            with open(questions_path, 'r', encoding="utf-8") as file:
                question_data = json.load(file)
                question_list = list(question_data['general'].values())
                category_questions = question_data['categories']
        except Exception as e:
            st.error(f"Error loading example questions: {e}")
            question_list = []
            category_questions = {}
    
        # Example questions in categorized buttons
        st.subheader("Example Questions")
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("##### 🏭 Production")
            for q in category_questions.get("🏭 Production", []):
                if st.button(q, key=f"prod_{q}", use_container_width=True):
                    st.session_state.messages.append({"role": "user", "content": q})
                    # Set query flag for processing later
                    st.session_state["process_query"] = q
                    st.rerun()
                    
            st.markdown("##### 🔧 Machines")
            for q in category_questions.get("🔧 Machines", []):
                if st.button(q, key=f"mach_{q}", use_container_width=True):
                    st.session_state.messages.append({"role": "user", "content": q})
                    # Set query flag for processing later
                    st.session_state["process_query"] = q
                    st.rerun()
        
        with col2:
            st.markdown("##### 📦 Inventory")
            for q in category_questions.get("📦 Inventory", []):
                if st.button(q, key=f"inv_{q}", use_container_width=True):
                    st.session_state.messages.append({"role": "user", "content": q})
                    # Set query flag for processing later
                    st.session_state["process_query"] = q
                    st.rerun()
                    
            st.markdown("##### ⚠️ Quality")
            for q in category_questions.get("⚠️ Quality", []):
                if st.button(q, key=f"qual_{q}", use_container_width=True):
                    st.session_state.messages.append({"role": "user", "content": q})
                    # Set query flag for processing later
                    st.session_state["process_query"] = q
                    st.rerun()
                    
        st.divider()
        
        # Chat history container
        st.subheader("💬 Conversation")
        
        # Initialize process_query if it doesn't exist
        if "process_query" not in st.session_state:
            st.session_state["process_query"] = None
        
        # Display chat history
        for i, message in enumerate(st.session_state.messages):
            if message["role"] == "user":
                with st.chat_message("user"):
                    st.write(message["content"])
            else:
                with st.chat_message("assistant"):
                    # Check if this message has structured content
                    if isinstance(message["content"], dict) and "text" in message["content"]:
                        # Display the text part
                        st.markdown(message["content"]["text"], unsafe_allow_html=True)
                        
                        # Display any tool output components
                        if "tool_responses" in message["content"]:
                            for tool_response in message["content"]["tool_responses"]:
                                # Handle schema response
                                if tool_response["type"] == "get_schema":
                                    if tool_response["data"]:
                                        st.success(f"Retrieved schema for {tool_response['data']['total_tables']} tables")
                                        st.info(f"Database schema contains {tool_response['data']['total_tables']} tables with {tool_response['data']['total_columns']} total columns")
                                        with st.expander("View detailed schema", expanded=False):
                                            st.json(tool_response["data"]["schema"])
                                
                                # Handle SQL query response
                                elif tool_response["type"] == "execute_sql":
                                    # Show SQL query
                                    st.code(tool_response["sql_query"], language="sql")
                                    
                                    if tool_response.get("success", False):
                                        st.success(f"Query executed successfully in {tool_response['execution_time']:.2f}s - {tool_response['row_count']} rows returned")
                                        
                                        # Show dataframe if available
                                        if "dataframe" in tool_response and not tool_response["dataframe"].empty:
                                            # Display results in tabs for different views
                                            result_tabs = st.tabs(["Data Table", "Chart View", "Export"])
                                            
                                            with result_tabs[0]:
                                                st.dataframe(tool_response["dataframe"], hide_index=True, use_container_width=True)
                                            
                                            with result_tabs[1]:
                                                if "chart" in tool_response:
                                                    st.plotly_chart(tool_response["chart"], use_container_width=True)
                                                else:
                                                    st.info("This data doesn't appear suitable for visualization or has too few rows/columns.")
                                            
                                            with result_tabs[2]:
                                                # Add CSV download button
                                                csv = convert_df_to_csv(tool_response["dataframe"])
                                                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                                st.download_button(
                                                    "Download as CSV",
                                                    csv,
                                                    f"mes_query_result_{timestamp}.csv",
                                                    "text/csv",
                                                    key=f'download_csv_{i}_{timestamp}'
                                                )
                                    else:
                                        st.error(f"SQL Error: {tool_response.get('error', 'Unknown error')}")
                        
                        # Display follow-up suggestions if available
                        if "suggested_questions" in message["content"] and message["content"]["suggested_questions"]:
                            st.markdown("##### Suggested Follow-ups:")
                            cols = st.columns(min(len(message["content"]["suggested_questions"]), 2))
                            for j, q in enumerate(message["content"]["suggested_questions"]):
                                with cols[j % 2]:
                                    if st.button(q, key=f"followup_{i}_{j}", use_container_width=True):
                                        st.session_state.messages.append({"role": "user", "content": q})
                                        st.session_state["process_query"] = q
                                        st.rerun()
                    else:
                        # For simple string content
                        st.markdown(message["content"], unsafe_allow_html=True)
                        
        # Add the input box at the bottom
        user_input = st.chat_input("Ask a question about your manufacturing data...")
        
        if user_input:
            st.session_state.messages.append({"role": "user", "content": user_input})
            st.session_state["process_query"] = user_input
            st.rerun()
    
    # Process query if needed
    if st.session_state["process_query"]:
        # Get the query to process
        query = st.session_state["process_query"]
        
        # Create a spinner while processing
        with st.spinner(f"Processing query: {query}"):
            # Start timer
            start_time = time.time()
            
            # Get client
            client = get_bedrock_client()
            
            # Create system prompt introducing the MES system
            system_prompt = """You are an expert manufacturing analyst for a Manufacturing Execution System (MES) for an e-bike manufacturing facility.
    
    Your role is to help users extract insights by querying the MES database that tracks:
    - Products (e-bikes, components, and parts)
    - Work Orders (production jobs with schedules and status)
    - Inventory (raw materials, components, and stock levels)
    - Work Centers (manufacturing areas like Frame Fabrication, Wheel Production)
    - Machines (equipment with efficiency metrics and maintenance records)
    - Quality Control (inspection results, defects, and yield rates)
    - Material Consumption (component usage tracking)
    - Downtime Events (machine issues and reasons)
    - OEE Metrics (Overall Equipment Effectiveness measurements)
    - Employees (operators, technicians, and managers)
    
    IMPORTANT GUIDELINES:
    1. ALWAYS use the get_schema tool FIRST to understand the database structure.
    2. Write efficient SQL queries - prefer JOINs to retrieve related data in a single query.
    3. For questions about trends or patterns, include visualizable metrics.
    4. For inventory questions, consider reorder levels and stock status.
    5. For quality questions, look at defect types and rates.
    6. For machine questions, consider OEE metrics and maintenance schedules.
    7. For production questions, consider work order status and schedule adherence.
    
    FORMAT YOUR RESPONSES:
    1. First, briefly restate what you understood from the question
    2. Present a concise summary of the key findings
    3. Add relevant details or observations beneath your summary
    4. If applicable, suggest follow-up questions the user might want to ask
    
    Keep your explanations clear and relevant to manufacturing operations. Avoid excessive technical jargon when explaining results.
    """
            
            # Add the user message to the conversation history for the model
            user_message = {
                "role": "user",
                "content": [{"text": query}]
            }
            
            # Maintain conversation history
            if not st.session_state.model_conversation:
                model_conversation = [user_message]
            else:
                model_conversation = st.session_state.model_conversation + [user_message]
            
            # First model call - this may result in tool use
            response = client.converse(
                modelId=model_id,
                messages=model_conversation,
                system=[{"text": system_prompt}],
                toolConfig=tool_config,
                inferenceConfig={
                    "maxTokens": 4096,
                    "temperature": temperature
                }
            )
            
            # Force schema retrieval before SQL execution
            response, conversation = enforce_schema_first(response, client, model_id, temperature, model_conversation.copy())
            
            # Process the response, which may involve tool use
            stop_reason = response["stopReason"]
            conversation = model_conversation.copy()
            
            # Store tool responses for structured message
            tool_responses = []
            
            # Handle tool use requests as needed
            while stop_reason == "tool_use":
                # Get the tool request
                tool_requests = response["output"]["message"]["content"]
                
                # Add the assistant message to the conversation
                conversation.append(response["output"]["message"])
                
                # Process each tool request
                for tool_request in tool_requests:
                    if "toolUse" in tool_request:
                        # Handle the tool request
                        response, conversation, tool_response = handle_tool_request(
                            client, tool_request, model_id, temperature, conversation, 
                            query_timeout=st.session_state.query_timeout
                        )
                        
                        # Store the tool response
                        tool_responses.append(tool_response)
                        
                        # Check if we need to process another tool request
                        stop_reason = response["stopReason"]
            
            # Extract the final text response
            final_message = response["output"]["message"]
            conversation.append(final_message)
            
            # Display the final text response
            final_text = ""
            for content_block in final_message["content"]:
                if "text" in content_block:
                    final_text += content_block["text"]
            
            # Add elapsed time
            elapsed_time = round(time.time() - start_time, 2)
            final_text_with_time = f"{final_text}\n\n<small><i>Response time: {elapsed_time}s</i></small>"
            
            # Extract any follow-up suggestions
            suggested_questions = []
            try:
                # Look for follow-up questions section
                if "follow-up" in final_text.lower():
                    follow_up_section = final_text.split("follow-up")[-1].split("\n\n")[0]
                    for line in follow_up_section.split("\n"):
                        if "?" in line and len(line) > 15:
                            # Clean up the question
                            question = line.strip()
                            question = question.replace("- ", "")
                            question = question.strip()
                            if question:
                                suggested_questions.append(question)
            except:
                pass
            
            # Create a structured response object
            structured_response = {
                "text": final_text_with_time,
                "tool_responses": tool_responses,
                "suggested_questions": suggested_questions
            }
            
            # Update conversation state
            st.session_state.model_conversation = conversation
            
            # Add to message history
            st.session_state.messages.append({"role": "assistant", "content": structured_response})
            
            # Clear the process flag
            st.session_state["process_query"] = None
            
            # Force UI update
            st.rerun()

# This allows the module to be run directly for testing
if __name__ == "__main__":
    # Set page config
    st.set_page_config(
        page_title="MES Insight Chat", 
        page_icon="⚙️",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    run_mes_chat()