"""Streamlit application for MES chatbot with tool use"""

import json
import logging
import os
import time

import streamlit as st
import pandas as pd
from dotenv import load_dotenv
import boto3

from mes_tools import DatabaseQueryTool, get_tool_config

# Configuration
load_dotenv()
proj_dir = os.path.abspath('')
db_path = os.path.join(proj_dir, 'mes.db')

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize tools
db_tool = DatabaseQueryTool(db_path)
tool_config = get_tool_config()

# Page configuration
st.set_page_config(page_title="Chat with your MES", page_icon=":factory:")
st.header(":factory: Chat with your MES :factory:")
st.subheader("Ask questions that will be answered by querying the MES")
st.caption("This simulation Manufacturing Execution System (MES) is designed to manage the production process of products. The MES is used to track the production process, maintain the inventory, and ensure the quality of the products.")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "How may I help you today?"}]

if "model_conversation" not in st.session_state:
    # This will store the messages in the format needed for the Bedrock converse API
    st.session_state.model_conversation = []
    
if "last_query_result" not in st.session_state:
    # This will store the last query result for reference
    st.session_state.last_query_result = None

# Create Bedrock client
def get_bedrock_client():
    """Create a bedrock-runtime client"""
    return boto3.client(
        service_name='bedrock-runtime',
        region_name=os.getenv("AWS_REGION", "us-east-1"),
        endpoint_url=f'https://bedrock-runtime.{os.getenv("AWS_REGION", "us-east-1")}.amazonaws.com',
    )

# Define a function to reset the chat
def reset_chat():
    """Reset the chat state"""
    st.session_state.messages = [{"role": "assistant", "content": "How may I help you today?"}]
    st.session_state.model_conversation = []
    st.session_state.last_query_result = None

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
def handle_tool_request(client, tool, model_id, temperature, conversation):
    """Handle tool requests from the model"""
    tool_use = tool["toolUse"]
    tool_use_id = tool_use["toolUseId"]
    tool_name = tool_use["name"]
    
    logger.info(f"Tool request received: {tool_name}, ID: {tool_use_id}")
    
    # Execute the appropriate tool
    if tool_name == "execute_sql":
        sql_query = tool_use["input"]["sql_query"]
        # Execute the SQL query
        result = db_tool.execute_query(sql_query)
        
        # Format the tool result
        if result["success"]:
            # Show SQL and results in the chat
            query_result = f"Executing SQL: {sql_query}\n\nResults: {len(result['rows'])} rows returned"
            with st.status(query_result, expanded=True):
                if result["row_count"] > 0:
                    df = pd.DataFrame(result["rows"])
                    st.dataframe(df, hide_index=True)
                    
                    # Save the dataframe as part of the conversation for reference
                    st.session_state.last_query_result = df
                else:
                    st.info("Query returned no results")
            
            # Prepare the tool result response
            tool_result = {
                "toolUseId": tool_use_id,
                "content": [{"json": result}]
            }
        else:
            # Show error in the chat
            st.error(f"SQL Error: {result['error']}")
            
            # Prepare the error response
            tool_result = {
                "toolUseId": tool_use_id,
                "content": [{"text": f"Error executing SQL: {result['error']}"}],
                "status": "error"
            }
    
    elif tool_name == "get_schema":
        # Get the database schema
        schema = db_tool.get_schema()
        
        # Show schema in the chat
        with st.status("Getting database schema...", expanded=False):
            st.json(schema)
        
        # Prepare the tool result response
        tool_result = {
            "toolUseId": tool_use_id,
            "content": [{"json": schema}]
        }
    
    else:
        # Unknown tool
        logger.error(f"Unknown tool requested: {tool_name}")
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
    
    return response, conversation

# Sidebar configuration
with st.sidebar:
    st.button("Reset Chat", on_click=reset_chat)
    
    temperature = st.slider(
        label='Model Temperature',
        min_value=0.0,
        max_value=1.0,
        value=0.1,
        step=0.01,
        key='temperature'
    )
    
    model_id = st.selectbox(
        'Select Model:',
        ["anthropic.claude-3-haiku-20240307-v1:0", 
         "anthropic.claude-3-sonnet-20240229-v1:0",
         "us.amazon.nova-micro-v1:0", 
         "us.amazon.nova-lite-v1:0", 
         "us.amazon.nova-pro-v1:0"],
        index=0,
        key='model_id'
    )

# Load example questions
try:
    with open('sample_questions.json', 'r', encoding="utf-8") as file:
        example_questions = json.load(file)
        question_list = list(example_questions.values())
except Exception as e:
    st.error(f"Error loading example questions: {e}")
    question_list = []

# Example questions dropdown
question = st.selectbox("Example Questions:", [""] + question_list, key="question_select")
if question and question != st.session_state.get("last_selected_question", ""):
    st.session_state.messages.append({"role": "user", "content": question})
    st.session_state["last_selected_question"] = question

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if isinstance(message["content"], pd.DataFrame):
            st.dataframe(message["content"], hide_index=True)
        else:
            st.write(message["content"])

# Handle user input
if prompt := st.chat_input("Ask a question about your MES data"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

# Process last user message
last_msg = st.session_state.messages[-1] if st.session_state.messages else None
if last_msg and last_msg["role"] == "user":
    user_query = last_msg["content"]
    
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            start_time = time.time()
            client = get_bedrock_client()
            
            # Create system prompt introducing the MES system
            system_prompt = """You are an assistant for a Manufacturing Execution System (MES).
            The MES database contains information about manufacturing processes, machines, work orders, products, and quality control.
            
            IMPORTANT: ALWAYS use the get_schema tool FIRST to understand the database structure before attempting any SQL queries.
            Never try to guess table or column names. Only write SQL queries after you have examined the schema.
            
            Follow this exact sequence for every database question:
            1. FIRST use get_schema to retrieve and carefully examine the database structure
            2. ONLY THEN use execute_sql to run appropriate queries based on the schema you received
            3. Provide a comprehensive, human-friendly response that explains the data in detail
            
            Your final response should:
            - Clearly summarize all the information retrieved from the database
            - Present data in a structured way, using lists or tables when appropriate
            - Highlight important patterns or insights
            - Answer the user's original question completely
            
            Always make sure your final answer is comprehensive and doesn't just state that you ran a query."""
            
            # Add the user message to the conversation history for the model
            user_message = {
                "role": "user",
                "content": [{"text": user_query}]
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
                        response, conversation = handle_tool_request(
                            client, tool_request, model_id, temperature, conversation
                        )
                        
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
            
            # Display the complete, detailed answer
            elapsed_time = round(time.time() - start_time, 2)
            final_text += f"\n\nTotal processing time: {elapsed_time}s"
            
            # Format and display the response
            st.markdown(final_text)
            
            # Display the query results again if available (for reference)
            if st.session_state.last_query_result is not None and not st.session_state.last_query_result.empty:
                with st.expander("View last query result data", expanded=False):
                    st.dataframe(st.session_state.last_query_result)
            
            # Update the conversation history
            st.session_state.model_conversation = conversation
            st.session_state.messages.append({"role": "assistant", "content": final_text})