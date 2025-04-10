"""
Shared database utilities for accessing the MES database
"""

import logging
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import time
import os
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DatabaseManager:
    """Database manager for accessing the MES database with common queries"""
    
    def __init__(self, db_path=None):
        """Initialize with the database path"""
        if db_path is None:
            # Always use mes.db in the root directory, not relative to this file
            db_path = 'mes.db'
        
        self.db_path = db_path
        self._schema_cache = None
        self._schema_cache_time = None
        self._cache_expiry = 60 * 5  # Cache expires after 5 minutes
        
        # Verify database exists
        if not os.path.exists(self.db_path):
            logger.warning(f"Database file not found: {self.db_path}")
    
    def get_connection(self):
        """Get a database connection"""
        return sqlite3.connect(self.db_path)
    
    def execute_query(self, sql_query):
        """Execute a SQL query and return the results"""
        logger.info(f"Executing SQL query: {sql_query}")
        start_time = time.time()
        
        try:
            # Connect to the database
            conn = self.get_connection()
            
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
            conn = self.get_connection()
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
    
    # ---- Production Meeting Specific Queries ---- #
    
    def get_daily_production_summary(self, days_back=1):
        """Get a summary of production for the specified days back from today"""
        today = datetime.now()
        target_date = today - timedelta(days=days_back)
        
        # Format date for SQL query
        date_str = target_date.strftime('%Y-%m-%d')
        
        query = f"""
        SELECT 
            p.Name as ProductName,
            COUNT(wo.OrderID) as TotalOrders,
            SUM(wo.Quantity) as PlannedQuantity,
            SUM(wo.ActualProduction) as ActualProduction,
            SUM(wo.Scrap) as ScrapQuantity,
            ROUND(SUM(wo.ActualProduction) * 100.0 / SUM(wo.Quantity), 2) as CompletionPercentage
        FROM 
            WorkOrders wo
        JOIN 
            Products p ON wo.ProductID = p.ProductID
        WHERE 
            wo.ActualStartTime LIKE '{date_str}%'
        GROUP BY 
            p.Name
        ORDER BY 
            TotalOrders DESC
        """
        
        result = self.execute_query(query)
        if result["success"]:
            return pd.DataFrame(result["rows"])
        else:
            logger.error(f"Error getting daily production summary: {result['error']}")
            return pd.DataFrame()
    
    def get_machine_status_summary(self):
        """Get a summary of current machine status"""
        query = """
        SELECT 
            m.Type as MachineType,
            COUNT(m.MachineID) as TotalMachines,
            SUM(CASE WHEN m.Status = 'running' THEN 1 ELSE 0 END) as Running,
            SUM(CASE WHEN m.Status = 'idle' THEN 1 ELSE 0 END) as Idle,
            SUM(CASE WHEN m.Status = 'maintenance' THEN 1 ELSE 0 END) as Maintenance,
            SUM(CASE WHEN m.Status = 'breakdown' THEN 1 ELSE 0 END) as Breakdown,
            ROUND(AVG(m.EfficiencyFactor) * 100, 2) as AvgEfficiency
        FROM 
            Machines m
        GROUP BY 
            m.Type
        ORDER BY 
            TotalMachines DESC
        """
        
        result = self.execute_query(query)
        if result["success"]:
            return pd.DataFrame(result["rows"])
        else:
            logger.error(f"Error getting machine status summary: {result['error']}")
            return pd.DataFrame()
    
    def get_quality_summary(self, days_back=1, range_days=30):
        """Get a summary of quality metrics for a range of days
        
        Args:
            days_back (int): Days ago to start the range
            range_days (int): Number of days to look back from the start date
        """
        today = datetime.now()
        end_date = today - timedelta(days=days_back)
        start_date = end_date - timedelta(days=range_days)
        
        # Format dates for SQL query
        end_date_str = end_date.strftime('%Y-%m-%d')
        start_date_str = start_date.strftime('%Y-%m-%d')
        
        query = f"""
        SELECT 
            p.Name as ProductName,
            p.Category as ProductCategory,
            COUNT(qc.CheckID) as InspectionCount,
            ROUND(AVG(qc.DefectRate) * 100, 2) as AvgDefectRate,
            ROUND(AVG(qc.ReworkRate) * 100, 2) as AvgReworkRate,
            ROUND(AVG(qc.YieldRate) * 100, 2) as AvgYieldRate,
            SUM(CASE WHEN qc.Result = 'pass' THEN 1 ELSE 0 END) as PassCount,
            SUM(CASE WHEN qc.Result = 'fail' THEN 1 ELSE 0 END) as FailCount,
            SUM(CASE WHEN qc.Result = 'rework' THEN 1 ELSE 0 END) as ReworkCount
        FROM 
            QualityControl qc
        JOIN 
            WorkOrders wo ON qc.OrderID = wo.OrderID
        JOIN 
            Products p ON wo.ProductID = p.ProductID
        WHERE 
            qc.Date BETWEEN '{start_date_str}' AND '{end_date_str} 23:59:59'
        GROUP BY 
            p.Name, p.Category
        ORDER BY 
            InspectionCount DESC
        """
        
        result = self.execute_query(query)
        if result["success"]:
            return pd.DataFrame(result["rows"])
        else:
            logger.error(f"Error getting quality summary: {result['error']}")
            return pd.DataFrame()
    
    def get_inventory_alerts(self):
        """Get inventory items that are below reorder level"""
        query = """
        SELECT 
            i.Name as ItemName,
            i.Category as Category,
            i.Quantity as CurrentQuantity,
            i.ReorderLevel as ReorderLevel,
            i.LeadTime as LeadTimeInDays,
            s.Name as SupplierName,
            (i.ReorderLevel - i.Quantity) as ShortageAmount
        FROM 
            Inventory i
        JOIN 
            Suppliers s ON i.SupplierID = s.SupplierID
        WHERE 
            i.Quantity < i.ReorderLevel
        ORDER BY 
            ShortageAmount DESC
        """
        
        result = self.execute_query(query)
        if result["success"]:
            return pd.DataFrame(result["rows"])
        else:
            logger.error(f"Error getting inventory alerts: {result['error']}")
            return pd.DataFrame()
    
    def get_upcoming_maintenance(self, days_ahead=7):
        """Get machines due for maintenance in the next X days"""
        today = datetime.now()
        future_date = today + timedelta(days=days_ahead)
        
        # Format dates for SQL query
        today_str = today.strftime('%Y-%m-%d')
        future_str = future_date.strftime('%Y-%m-%d')
        
        query = f"""
        SELECT 
            m.Name as MachineName,
            m.Type as MachineType,
            wc.Name as WorkCenterName,
            m.NextMaintenanceDate as MaintenanceDate,
            m.MaintenanceFrequency as FrequencyHours,
            m.LastMaintenanceDate as LastMaintenance,
            julianday(m.NextMaintenanceDate) - julianday('{today_str}') as DaysUntilMaintenance
        FROM 
            Machines m
        JOIN 
            WorkCenters wc ON m.WorkCenterID = wc.WorkCenterID
        WHERE 
            m.NextMaintenanceDate BETWEEN '{today_str}' AND '{future_str}'
        ORDER BY 
            m.NextMaintenanceDate ASC
        """
        
        result = self.execute_query(query)
        if result["success"]:
            return pd.DataFrame(result["rows"])
        else:
            logger.error(f"Error getting upcoming maintenance: {result['error']}")
            return pd.DataFrame()
    
    def get_work_order_status(self):
        """Get current work order status summary"""
        query = """
        SELECT 
            wo.Status as Status,
            COUNT(wo.OrderID) as OrderCount,
            SUM(wo.Quantity) as TotalQuantity,
            ROUND(AVG(julianday(wo.PlannedEndTime) - julianday(wo.PlannedStartTime)) * 24, 2) as AvgPlanHours
        FROM 
            WorkOrders wo
        GROUP BY 
            wo.Status
        ORDER BY 
            OrderCount DESC
        """
        
        result = self.execute_query(query)
        if result["success"]:
            return pd.DataFrame(result["rows"])
        else:
            logger.error(f"Error getting work order status: {result['error']}")
            return pd.DataFrame()

# Bedrock tool configuration for the chat interface
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
                                    "description": "The SQL query to execute against the MES database. Write clean, efficient SQL that joins necessary tables to answer the user's question in one query when possible. The queries must be SQLite compatible"
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