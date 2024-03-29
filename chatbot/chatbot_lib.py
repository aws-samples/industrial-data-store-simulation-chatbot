from datetime import datetime
import logging
import os
import re
import time
import json
import sqlite3

import boto3
import pandas as pd
from langchain.prompts import PromptTemplate
from langchain.chains import ConversationChain
from langchain.llms.bedrock import Bedrock
from langchain_community.chat_models import BedrockChat
from langchain.memory import ConversationBufferMemory
from langchain_community.utilities import SQLDatabase


def get_llm(model_id="anthropic.claude-v2:1", model_kwargs="""{"maxTokenCount": 4000,"temperature": 0.1}"""):
    """Creates the LLM object for the langchain conversational bedrock agent.
    Parameters:
        model_kwargs (dict): Dictionary of model_kwargs to be passed to the Bedrock model.
    Returns:
        langchain.llms.bedrock.Bedrock: Bedrock model
    """
    session = boto3.Session(
        region_name=os.getenv("AWS_REGION", "us-east-1"), profile_name=os.getenv("AWS_PROFILE")
    )
    bedrock_client = boto3.client(
        service_name='bedrock-runtime',
        endpoint_url='https://bedrock-runtime.'+os.getenv('AWS_REGION', 'us-east-1')+'.amazonaws.com',
        )
    if (model_id == "anthropic.claude-3-haiku-20240307-v1:0") or (model_id == "anthropic.claude-3-sonnet-20240229-v1:0"):
        llm = BedrockChat(
            client=bedrock_client,
            model_id=model_id,
            model_kwargs=model_kwargs)
    else:
        llm = Bedrock(
            client=bedrock_client,
            model_id=model_id,
            model_kwargs=model_kwargs)

    return llm


def reset_conversation_agent(verbose=True, model_id="anthropic.claude-v2:1", model_kwargs="""{"maxTokenCount": 4000,"temperature": 0.1}"""):
    """Resets the langchain conversational bedrock agent with a new 
    conversation history, tempreature and model_id.
    Parameters
    ----------
    verbose :
        Flag for printing model react prompts (default=True)
    model_kwargs:
        Dictionary of model_kwargs to be passed to the Bedrock model.
    Returns
    ----------
    langchain.chains.ConversationChain :
        A langchain ConversationChain initialized with the specified parameters
    """
    memory = ConversationBufferMemory(ai_prefix='Assistant')
    conversation = ConversationChain(
        llm=get_llm(model_id=model_id, model_kwargs=model_kwargs), verbose=verbose, memory=memory
    )

    # langchain prompts do not always work with all the models. This prompt is tuned for Claude
    claude_prompt = PromptTemplate.from_template("""The following is a friendly conversation between a human and an AI.
    The AI is talkative and provides lots of specific details from its context. If the AI does not know
    the answer to a question, it truthfully says it does not know. If the AI is not sure about about the questions
    or some parameters in the question is unclear to provide an answer, ask follow up questions instead of hallucination. 

    Current conversation:
    {history}


    Human: {input}


    Assistant:
    """)

    conversation.prompt = claude_prompt
    return conversation


def read_content(file_path):
    """
    Reads and returns the entire content of a file.
    Parameters
    ----------
    file_path (str): 
        The path to the file that needs to be read.
    Returns
    ----------
    str: 
        The entire content of the file as a string
    """
    with open(file_path, 'r', encoding="utf-8") as file:
        # Read the entire content of the file
        message = file.read()
    return message


def generate_sql_prompt(question,
                        instructions,
                        db_path,
                        current_date=datetime.strftime(datetime.now(), '%A, %Y-%m-%d')):
    """Generates an prompt for text-to-SQL. Currently tuned for Claude which
    leverages xml tagging to separate key parts of the context. Supplies the 
    model with table description, table name, current date, table schema, 
    sample data. Includes model specific instructions.
    Parameters
    ----------
    question :
        question to be answered
    instructions :
        Model specific instructions engineered for text-to-SQL
    db_path :
        Path to the SQLite database file
    current_date :
        A specified date. (default=datetime.now())
    Returns
    ----------
    str :
        Prompt for text-to-SQL generation
    """

    # begin the prompt with the current date
    sql_prompt = f"Current Date: {current_date}\n\n"
    # add db description and schema
    sql_prompt += f"""<description>\n This database simulates a Manufacturing Execution System (MES), which is a software system designed to manage the production process of products. The MES is used to track the production process, maintain the inventory, and ensure the quality of the products. The MES is designed to be used in a manufacturing environment, where products are manufactured, machines are used to produce products, work orders are created and tracked, and quality control is performed.\n</description>\n\nThe database schema is as follows:"""
    schema = get_mes_schema(db_path=db_path)
    sql_prompt += f"\n\n<schema> {schema} \n</schema>\n\n"
    # add in user question and task instructions
    sql_prompt += instructions
    sql_prompt += "\n\nThe task is:"
    sql_prompt += f"\n<task>\n{question}\n</task>\n\n"
    logging.info(f"Length of prompt for SQL generation: {len(sql_prompt)} characters\n")

    return sql_prompt


def generate_nlp_prompt(data, question, query, instructions):
    """Generates a prompt given the results of the text-to-SQL request
    Parameters
    ----------
    data :
        the data returned from the database
    question :
        the original question asked
    query :
        the query used to return the data
    instructions :
        engineered instructions that are specific to the model provided
    Returns
    ----------
    str :
        An engineered prompt for summarizing the SQL results
    """
    nlp_prompt = """<task>\n%s\n</task>\n\n<sql>%s</sql>\n\n<data>\n%s\n</data>\n\n%s"""

    prompt = nlp_prompt % (question, query, data, instructions)

    logging.info(f"Length of prompt for NLP generation: {len(prompt)} characters\n")

    return prompt

def get_mes_schema(db_path):
    """Get the schema of the mes database
    Parameters
    ----------
    db_path :
        Path to the SQLite database file
    Returns
    ----------
    str :
        schema of the mes database as a string
    """
    db = SQLDatabase.from_uri(f"sqlite:///{db_path}", sample_rows_in_table_info=8)
    tables = db.get_usable_table_names()
    schema = db.get_table_info_no_throw(tables)
    return schema

def query_sqlite(query, db_path):
    """Creates a connection to a SQLite database and executes a query
    Parameters
    ----------
    query :
        An string containing SQL code
    db_path :
        Path to the SQLite database file
    Returns
    ----------
    pandas.DataFrame :
        the results of the SQL query
    """
    try:
        conn = sqlite3.connect(db_path)
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except Exception as e:
        return e

def parse_generated_sql(response):
    """Given a text-to-SQL generated output, extract the provided SQL. If query
    cannot be extracted than return the full response.
    Parameters
    ----------
    response :
        text-to-SQL generated string
    Returns
    ----------
    str :
        either the SQL from the generated text or the original response
    """
    logging.info(f"\nResponse that should include SQL code:\n{response}\n")
    try:
        start_sql = re.search(r'<sql>', response).end()
        end_sql = re.search(r'</sql>', response).start()
        query = response[start_sql:end_sql].strip()
        return query, True
    except:
        return response, False


def parse_generated_nlp(response):
    """Extract the response from the model. Currently built for Claude XML 
    tagging format
    Parameters
    ----------
    response :
        LLM generated string
    Returns
    ----------
    str :
        extracted string
    """
    logging.info(f"NLP response:\n{response}\n")
    try:
        start = re.search(r'<response>', response).end()
        end = re.search(r'</response>', response).start()
        response = response[start:end].strip()
        logging.info(f"Final Output:\n{response}\n")
        return response
    except:
        return response
