"""Tools for the MES chatbot application"""

import logging
import sqlite3
import pandas as pd
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseQueryTool:
    """A tool for executing SQL queries against the MES database"""
    
    def __init__(self, db_path):
        """Initialize with the database path"""
        self.db_path = db_path
    
    def execute_query(self, sql_query):
        """Execute a SQL query and return the results"""
        logger.info(f"Executing SQL query: {sql_query}")
        
        try:
            # Connect to the database
            conn = sqlite3.connect(self.db_path)
            
            # Execute the query
            df = pd.read_sql_query(sql_query, conn)
            conn.close()
            
            # Convert to JSON-serializable format
            result = {
                "success": True,
                "rows": df.to_dict(orient="records"),
                "column_names": df.columns.tolist(),
                "row_count": len(df)
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing SQL query: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_schema(self):
        """Get the database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        schema = {}
        for table in tables:
            table_name = table[0]
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            
            # Format column information
            column_info = []
            for col in columns:
                column_info.append({
                    "name": col[1],
                    "type": col[2],
                    "notnull": col[3],
                    "pk": col[5]
                })
            
            # Get sample data
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 3;")
            sample_data = cursor.fetchall()
            
            # Get column names for the sample data
            cursor.execute(f"PRAGMA table_info({table_name});")
            column_names = [col[1] for col in cursor.fetchall()]
            
            # Format sample data
            sample_data_records = []
            for row in sample_data:
                record = {}
                for i, value in enumerate(row):
                    record[column_names[i]] = value
                sample_data_records.append(record)
            
            # Add table information to schema
            schema[table_name] = {
                "columns": column_info,
                "sample_data": sample_data_records
            }
        
        conn.close()
        return schema

# Define the tool configuration for Bedrock
def get_tool_config():
    """Get the tool configuration for the Bedrock converse API"""
    
    return {
        "tools": [
            {
                "toolSpec": {
                    "name": "get_schema",
                    "description": "ALWAYS use this tool FIRST to get the schema of the MES database before attempting any SQL queries.",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {}
                        }
                    }
                }
            },
            {
                "toolSpec": {
                    "name": "execute_sql",
                    "description": "Execute SQL queries against the MES database ONLY after you have retrieved and examined the schema.",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {
                                "sql_query": {
                                    "type": "string",
                                    "description": "The SQL query to execute against the MES database. Only write SQL after examining the schema."
                                }
                            },
                            "required": [
                                "sql_query"
                            ]
                        }
                    }
                }
            }
        ]
    }