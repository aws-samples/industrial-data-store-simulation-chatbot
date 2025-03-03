"""Tools for the MES chatbot application"""

import logging
import sqlite3
import pandas as pd
import json
from datetime import datetime
import time

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DatabaseQueryTool:
    """A tool for executing SQL queries against the MES database"""
    
    def __init__(self, db_path):
        """Initialize with the database path"""
        self.db_path = db_path
        self._schema_cache = None
        self._schema_cache_time = None
        self._cache_expiry = 60 * 5  # Cache expires after 5 minutes
    
    def execute_query(self, sql_query):
        """Execute a SQL query and return the results"""
        logger.info(f"Executing SQL query: {sql_query}")
        start_time = time.time()
        
        try:
            # Connect to the database
            conn = sqlite3.connect(self.db_path)
            
            # Execute the query
            df = pd.read_sql_query(sql_query, conn)
            conn.close()
            
            # Process datetime columns for better display
            for col in df.columns:
                if df[col].dtype == 'object':
                    # Try to convert string columns that might be dates
                    try:
                        if df[col].str.contains('-').any() and df[col].str.contains(':').any():
                            df[col] = pd.to_datetime(df[col])
                            # Format datetime for display
                            df[col] = df[col].dt.strftime('%Y-%m-%d %H:%M')
                    except:
                        pass
            
            # Round float columns to 2 decimal places for display
            for col in df.select_dtypes(include=['float']).columns:
                df[col] = df[col].round(2)
            
            # Convert to JSON-serializable format
            result = {
                "success": True,
                "rows": df.to_dict(orient="records"),
                "column_names": df.columns.tolist(),
                "row_count": len(df),
                "execution_time_ms": round((time.time() - start_time) * 1000, 2)
            }
            
            logger.info(f"Query executed successfully: {len(df)} rows returned in {result['execution_time_ms']}ms")
            return result
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error executing SQL query: {error_msg}")
            
            # Provide more helpful error messages for common issues
            if "no such table" in error_msg.lower():
                table_name = error_msg.split("no such table:", 1)[1].strip() if "no such table:" in error_msg else "unknown"
                error_msg = f"Table '{table_name}' doesn't exist. Please check the schema and table names."
            elif "no such column" in error_msg.lower():
                col_name = error_msg.split("no such column:", 1)[1].strip() if "no such column:" in error_msg else "unknown"
                error_msg = f"Column '{col_name}' doesn't exist. Please check the schema and column names."
            elif "syntax error" in error_msg.lower():
                error_msg = f"SQL syntax error: {error_msg}. Please check your query syntax."
            
            return {
                "success": False,
                "error": error_msg,
                "execution_time_ms": round((time.time() - start_time) * 1000, 2)
            }
    
    def get_schema(self):
        """Get the database schema with caching for performance"""
        current_time = time.time()
        
        # Return cached schema if available and fresh
        if (self._schema_cache is not None and 
            self._schema_cache_time is not None and 
            current_time - self._schema_cache_time < self._cache_expiry):
            logger.info("Returning cached schema")
            return self._schema_cache
        
        logger.info("Retrieving fresh database schema")
        start_time = time.time()
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            
            schema = {}
            for table in tables:
                table_name = table[0]
                
                # Get column information
                cursor.execute(f"PRAGMA table_info({table_name});")
                columns = cursor.fetchall()
                
                # Format column information
                column_info = []
                for col in columns:
                    column_info.append({
                        "name": col[1],
                        "type": col[2],
                        "notnull": bool(col[3]),
                        "pk": bool(col[5])
                    })
                
                # Get foreign key relationships
                cursor.execute(f"PRAGMA foreign_key_list({table_name});")
                foreign_keys = cursor.fetchall()
                
                fk_info = []
                for fk in foreign_keys:
                    fk_info.append({
                        "id": fk[0],
                        "seq": fk[1],
                        "table": fk[2],
                        "from": fk[3],
                        "to": fk[4]
                    })
                
                # Get table row count
                cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
                row_count = cursor.fetchone()[0]
                
                # Get sample data (limited to 3 rows for performance)
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 3;")
                sample_data = cursor.fetchall()
                
                # Get column names for the sample data
                column_names = [col[1] for col in columns]
                
                # Format sample data as records
                sample_data_records = []
                for row in sample_data:
                    record = {}
                    for i, value in enumerate(row):
                        record[column_names[i]] = value
                    sample_data_records.append(record)
                
                # Add table information to schema
                schema[table_name] = {
                    "columns": column_info,
                    "foreign_keys": fk_info,
                    "row_count": row_count,
                    "sample_data": sample_data_records
                }
            
            # Add schema metadata
            schema["__metadata__"] = {
                "database_name": self.db_path.split("/")[-1],
                "total_tables": len(tables),
                "generated_at": datetime.now().isoformat(),
                "schema_version": "1.1"
            }
            
            conn.close()
            
            # Update cache
            self._schema_cache = schema
            self._schema_cache_time = current_time
            
            logger.info(f"Schema retrieved in {round((time.time() - start_time) * 1000, 2)}ms")
            return schema
            
        except Exception as e:
            logger.error(f"Error retrieving schema: {e}")
            return {
                "error": f"Failed to retrieve schema: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }

    def get_table_relationships(self):
        """Generate a visual representation of table relationships"""
        schema = self.get_schema()
        
        relationships = []
        
        # Extract relationships from foreign keys
        for table_name, table_info in schema.items():
            if table_name == "__metadata__":
                continue
                
            for fk in table_info.get("foreign_keys", []):
                relationships.append({
                    "from_table": table_name,
                    "from_column": fk["from"],
                    "to_table": fk["table"],
                    "to_column": fk["to"]
                })
        
        return {
            "relationships": relationships,
            "table_counts": {table: info["row_count"] for table, info in schema.items() if table != "__metadata__"}
        }

# Define the tool configuration for Bedrock
def get_tool_config():
    """Get the tool configuration for the Bedrock converse API"""
    
    return {
        "tools": [
            {
                "toolSpec": {
                    "name": "get_schema",
                    "description": "ALWAYS use this tool FIRST to get the schema of the MES database before attempting any SQL queries. This provides details about all tables, columns, relationships, and sample data.",
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
                    "description": "Execute SQL queries against the MES database ONLY after you have retrieved and examined the schema. Write efficient SQL that joins relevant tables and focuses on answering the user's specific question.",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {
                                "sql_query": {
                                    "type": "string",
                                    "description": "The SQL query to execute against the MES database. Write clean, efficient SQL that joins necessary tables to answer the user's question in one query when possible."
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