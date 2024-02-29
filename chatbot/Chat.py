"""Python file to serve as the frontend"""

import json
import logging
import os
from time import time

from dotenv import load_dotenv
import pandas as pd
import sqlparse
import streamlit as st

from langchain.prompts import PromptTemplate 
from langchain.chains import ConversationChain
from langchain.llms.bedrock import Bedrock
from langchain.memory import ConversationBufferMemory

from chatbot_lib import (
    generate_nlp_prompt,
    generate_sql_prompt,
    parse_generated_nlp,
    parse_generated_sql,
    query_postgres,
    reset_conversation_agent,
)

# Configuration
load_dotenv()
proj_dir = os.path.abspath('..') 

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Functions
def clear_input():
    if "question" in st.session_state:
        del st.session_state["question"]
    if "messages" in st.session_state:
        del st.session_state["messages"]
    if "selected_question" in st.session_state:
        st.session_state.selected_question = ""
        
        
# Page config
st.set_page_config(page_title="Chat with your MES", page_icon=":factory:")
st.header(":factory: Chat with your MES :factory:")
st.subheader("Ask questions that will be answered by querying the MES")
st.caption("This simulation Manufacturing Execution System (MES) is designed to manage the production process of products. The MES is used to track the production process, maintain the inventory, and ensure the quality of the products. The MES is designed to be used in a manufacturing environment, where products are manufactured, machines are used to produce products, work orders are created and tracked, and quality control is performed.")

# Sidebar
reset = st.sidebar.button("Reset Chat", 
                          on_click=clear_input)
st.sidebar.slider(
    label='Model Temperature',
    min_value=0.,
    max_value=1.,
    value=0.1,
    step=0.01,
    key='temperature'
)
model_id = st.sidebar.selectbox(
    'Select Model ID:',
    ["anthropic.claude-v2:1", "anthropic.claude-v2", "anthropic.claude-instant-v1"],
    index=2, #default to claude instant
    key='model_id'
)

# Load data
with open('prompt_instructions.json', 'r', encoding="utf-8") as file:
    data = json.load(file)
sql_instructions = data['sql_prompt']
nlp_instructions = data['nlp_prompt']

with open('sample_questions.json', 'r', encoding="utf-8") as file:
    example_questions = json.load(file)
question_list = [q for q in example_questions.values()]

with open('postgres_creds.json', 'r', encoding="utf-8") as file:
    creds = json.load(file)

model_kwargs = {
    "max_tokens_to_sample": 8000,
    "temperature": st.session_state.temperature,
}

# initialize state 
if "question" not in st.session_state:
    st.session_state.question = ""
if "messages" not in st.session_state.keys():
    st.session_state.messages = [{"role": "assistant", "content": "How may I help you?"}]

# Use a selectbox in the sidebar for the example questions
question = st.selectbox("Example Questions:", [""] + question_list, key="selected_question")


# initialize the question
if (question != "") & (len(st.session_state.messages) == 1):
    st.session_state.messages.append({"role": "user", "content": question})

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if type(message["content"]) == pd.DataFrame:
            st.dataframe(message["content"])
        else:
            st.write(message["content"])

# Take input user prompt
if prompt := st.chat_input():
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

# Get the latest message in the messages
last_msg = st.session_state.messages[-1]

#Chat logic for follow up
if last_msg["role"] == "user":
    messages = []
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            # If the latest message is the question, reset conversation and pass through the initial prompt
            if last_msg["content"] == question:
                st.session_state.conversation = reset_conversation_agent(model_id=model_id, model_kwargs=model_kwargs)
                prompt = generate_sql_prompt(question=question, instructions=sql_instructions, creds=creds)
            else:
                prompt = last_msg["content"]
            #Model invocation
            call_start_time = time()
            response = st.session_state.conversation.predict(input=prompt)
            sql_running_time = round(time()-call_start_time, 2)
            logger.info(f"\nBedrock SQL generation calling time:\n{sql_running_time}s\n")
            query, has_sql = parse_generated_sql(response)
            # If sql is generated, query the database
            if has_sql:
                # Print the sql query in the chat
                query_fmt = sqlparse.format(query, reindent=True, keyword_case='upper')
                st.text(query_fmt)
                messages.append(query_fmt)
                data = query_postgres(query=query, creds=creds)
                # If query returns errors reprompt the model with the supplied error
                trial_cnt = 0
                while type(data) != pd.core.frame.DataFrame and time() - call_start_time < 120 and trial_cnt < 5:
                    pred_start_time = time()
                    new_prompt = f'The previous SQL you generated has the following error:{data}. Please regenerate the sql that revise the previous error'
                    response = st.session_state.conversation.predict(input=new_prompt)
                    logger.info(f"\nBedrock SQL generation calling time:\n{round(time()-pred_start_time, 2)}s\n")
                    query, has_sql = parse_generated_sql(response)
                    query_fmt = sqlparse.format(query, reindent=True, keyword_case='upper')
                    st.text(response)
                    messages.append(response)
                    data = query_postgres(query=query, creds=creds)
                    trial_cnt += 1
                if time()-call_start_time>120 or trial_cnt >= 5: #timeout
                    response = 'Time out, please retry'
                    nlp_start_time = time()
                else: #Generate the response (NLP)
                    st.dataframe(data.head(50), hide_index=True)
                    messages.append(data.head(50))
                    nlp_start_time = time()
                    nlp_prompt = generate_nlp_prompt(data=data, question=question, query=query, instructions=nlp_instructions)
                    response = st.session_state.conversation.predict(input=nlp_prompt)
                logger.info(f"\nBedrock NLP generation calling time:\n{round(time()-nlp_start_time, 2)}s\n")
                response = parse_generated_nlp(response)
                nlp_running_time = round(time()-nlp_start_time, 2)
                response += '\n\nSQL generation time is %3.2fs, NLP generation time is %3.2fs, total running time is %3.2fs' % (sql_running_time, nlp_running_time, time()-call_start_time)
            st.write(response.replace('$', '\$'))
            messages.append(response)
    messages = [{"role": "assistant", "content": m} for m in messages]
    st.session_state.messages += messages