"""Utility functions for the MES chatbot application"""

import os
import re
import json
import sqlite3
import logging
from datetime import datetime

import pandas as pd
import boto3

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_bedrock_client():
    """Create a bedrock-runtime client"""
    return boto3.client(
        service_name='bedrock-runtime',
        region_name=os.getenv("AWS_REGION", "us-east-1"),
        endpoint_url=f'https://bedrock-runtime.{os.getenv("AWS_REGION", "us-east-1")}.amazonaws.com',
    )

def get_db_schema(db_path):
    """Get the schema of the MES database"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    schema = ""
    for table in tables:
        table_name = table[0]
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = cursor.fetchall()
        
        schema += f"Table: {table_name}\n"
        for col in columns:
            col_name = col[1]
            col_type = col[2]
            schema += f"  {col_name} ({col_type})\n"
        
        # Get sample data
        cursor.execute(f"SELECT * FROM {table_name} LIMIT 3;")
        sample_data = cursor.fetchall()
        if sample_data:
            schema += "Sample data:\n"
            for row in sample_data:
                schema += f"  {row}\n"
        
        schema += "\n"
    
    conn.close()
    return schema

def create_sql_prompt(question, sql_instructions, db_path):
    """Create a prompt for SQL generation"""
    current_date = datetime.strftime(datetime.now(), '%A, %Y-%m-%d')
    
    # begin the prompt with the current date
    sql_prompt = f"Current Date: {current_date}\n\n"
    
    # add db description and schema
    sql_prompt += f"""<description>
This database simulates a Manufacturing Execution System (MES), which is a software system designed to manage
the production process of products. The MES is used to track the production process, maintain the inventory,
and ensure the quality of the products. The MES is designed to be used in a manufacturing environment, where
products are manufactured, machines are used to produce products, work orders are created and tracked, and
quality control is performed.
</description>

The database schema is as follows:"""
    
    schema = get_db_schema(db_path=db_path)
    sql_prompt += f"\n\n<schema> {schema} \n</schema>\n\n"
    
    # add in user question and task instructions
    sql_prompt += sql_instructions
    sql_prompt += "\n\nThe task is:"
    sql_prompt += f"\n<task>\n{question}\n</task>\n\n"
    
    logger.info(f"Length of SQL prompt: {len(sql_prompt)} characters")
    return sql_prompt

def create_nlp_prompt(data, question, query, nlp_instructions):
    """Create a prompt for natural language generation"""
    nlp_prompt = f"""<task>
{question}
</task>

<sql>
{query}
</sql>

<data>
{data}
</data>

{nlp_instructions}"""

    logger.info(f"Length of NLP prompt: {len(nlp_prompt)} characters")
    return nlp_prompt

def extract_sql(response):
    """Extract SQL query from response text"""
    logger.info(f"Extracting SQL from response:\n{response}")
    try:
        start_sql = re.search(r'<sql>', response).end()
        end_sql = re.search(r'</sql>', response).start()
        query = response[start_sql:end_sql].strip()
        return query, True
    except:
        return response, False

def extract_response_text(response):
    """Extract final response from model output"""
    logger.info(f"Extracting response text from:\n{response}")
    try:
        start = re.search(r'<response>', response).end()
        end = re.search(r'</response>', response).start()
        result = response[start:end].strip()
        logger.info(f"Extracted response:\n{result}")
        return result
    except:
        return response

def execute_sql(query, db_path):
    """Execute SQL query and return results as DataFrame"""
    try:
        conn = sqlite3.connect(db_path)
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except Exception as e:
        return e