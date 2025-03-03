"""Streamlit application for MES chatbot"""

import json
import logging
import os
from time import time

import streamlit as st
import pandas as pd
import sqlparse
from dotenv import load_dotenv

from mes_utils import (
    get_bedrock_client,
    create_sql_prompt, 
    create_nlp_prompt,
    extract_sql,
    extract_response_text,
    execute_sql
)

# Configuration
load_dotenv()
proj_dir = os.path.abspath('')
db_path = os.path.join(proj_dir, 'mes.db')

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(page_title="Chat with your MES", page_icon=":factory:")
st.header(":factory: Chat with your MES :factory:")
st.subheader("Ask questions that will be answered by querying the MES")
st.caption("This simulation Manufacturing Execution System (MES) is designed to manage the production process of products. The MES is used to track the production process, maintain the inventory, and ensure the quality of the products.")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "How may I help you today?"}]

if "conversation_history" not in st.session_state:
    # This will store the actual messages we send to the model
    st.session_state.conversation_history = []

# Sidebar configuration
with st.sidebar:
    st.button("Reset Chat", on_click=lambda: st.session_state.clear())
    
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

# Load configuration data
try:
    with open('prompt_instructions.json', 'r', encoding="utf-8") as file:
        data = json.load(file)
        sql_instructions = data['sql_prompt']
        nlp_instructions = data['nlp_prompt']
        
    with open('sample_questions.json', 'r', encoding="utf-8") as file:
        example_questions = json.load(file)
        question_list = list(example_questions.values())
except Exception as e:
    st.error(f"Error loading configuration files: {e}")
    st.stop()

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
            # Initialize response components
            response_messages = []
            client = get_bedrock_client()
            
            # STEP 1: Generate SQL from the question
            sql_start_time = time()
            sql_prompt = create_sql_prompt(user_query, sql_instructions, db_path)
            
            # Call the model to generate SQL
            sql_response = client.converse(
                modelId=model_id,
                messages=[{
                    "role": "user",
                    "content": [{"text": sql_prompt}]
                }],
                inferenceConfig={
                    "maxTokens": 4096,
                    "temperature": temperature
                }
            )
            
            # Extract the text response
            sql_text = sql_response["output"]["message"]["content"][0]["text"]
            sql_running_time = round(time() - sql_start_time, 2)
            logger.info(f"SQL generation time: {sql_running_time}s")
            
            # Log token usage if available
            if "usage" in sql_response:
                logger.info(f"SQL Token usage: {sql_response['usage']}")
            
            # Extract SQL query
            query, has_sql = extract_sql(sql_text)
            
            # STEP 2: Execute SQL and generate natural language response
            if has_sql:
                # Format and display the SQL
                query_fmt = sqlparse.format(query, reindent=True, keyword_case='upper')
                st.text(query_fmt)
                response_messages.append(query_fmt)
                
                # Execute the query
                data = execute_sql(query=query, db_path=db_path)
                
                # Handle SQL execution errors
                trial_count = 0
                while isinstance(data, Exception) and trial_count < 3:
                    error_prompt = f"The previous SQL you generated has the following error: {data}. Please regenerate the SQL that corrects this error."
                    
                    error_response = client.converse(
                        modelId=model_id,
                        messages=[{
                            "role": "user",
                            "content": [{"text": error_prompt}]
                        }],
                        inferenceConfig={
                            "maxTokens": 4096,
                            "temperature": temperature
                        }
                    )
                    
                    error_text = error_response["output"]["message"]["content"][0]["text"]
                    st.text(error_text)
                    response_messages.append(error_text)
                    
                    # Extract and try the corrected SQL
                    query, has_sql = extract_sql(error_text)
                    if has_sql:
                        query_fmt = sqlparse.format(query, reindent=True, keyword_case='upper')
                        data = execute_sql(query=query, db_path=db_path)
                    
                    trial_count += 1
                
                # If we got valid data, display it and generate explanation
                if isinstance(data, pd.DataFrame):
                    st.dataframe(data.head(50), hide_index=True)
                    response_messages.append(data.head(50))
                    
                    # Generate natural language explanation
                    nlp_start_time = time()
                    nlp_prompt = create_nlp_prompt(data, user_query, query, nlp_instructions)
                    
                    nlp_response = client.converse(
                        modelId=model_id,
                        messages=[{
                            "role": "user",
                            "content": [{"text": nlp_prompt}]
                        }],
                        inferenceConfig={
                            "maxTokens": 4096,
                            "temperature": temperature
                        }
                    )
                    
                    nlp_text = nlp_response["output"]["message"]["content"][0]["text"]
                    final_response = extract_response_text(nlp_text)
                    nlp_running_time = round(time() - nlp_start_time, 2)
                    total_running_time = round(time() - sql_start_time, 2)
                    
                    # Add timing information
                    final_response += f'\n\nSQL generation time: {sql_running_time}s\nNLP generation time: {nlp_running_time}s\nTotal running time: {total_running_time}s'
                else:
                    final_response = f"Failed to execute SQL query after multiple attempts. Error: {data}"
            else:
                final_response = "I couldn't generate a valid SQL query from your question. Can you please provide more details or rephrase?"
            
            # Display the final response
            st.write(final_response.replace('$', '\\$'))
            response_messages.append(final_response)
    
    # Add all assistant responses to the message history
    for msg in response_messages:
        st.session_state.messages.append({"role": "assistant", "content": msg})