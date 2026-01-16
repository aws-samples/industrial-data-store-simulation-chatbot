"""
Shared database utilities for accessing the MES database.

Uses SQLAlchemy for DB-agnostic patterns with parameterized queries.
Currently supports SQLite; designed for future PostgreSQL support.
"""

import logging
import pandas as pd
from datetime import datetime, timedelta
import time
import os
from pathlib import Path

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.engine import Engine

from app_factory.shared.db_utils import (
    days_ago, days_ahead, today, now_timestamp,
    date_range_start, date_range_end, date_diff_days
)

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DatabaseManager:
    """Database manager for accessing the MES database with common queries.

    Uses SQLAlchemy engine for DB-agnostic access with parameterized queries.
    """

    def __init__(self, db_path: str = None):
        """Initialize with the database path.

        Args:
            db_path: Path to SQLite database file. Defaults to 'mes.db'.
        """
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

        # Create SQLAlchemy engine
        self.engine: Engine = create_engine(f'sqlite:///{self.db_path}')

    def get_connection(self):
        """Get a database connection from the engine."""
        return self.engine.connect()
    
    def execute_query(self, sql_query: str, params: dict = None) -> dict:
        """Execute a SQL query with optional named parameters.

        Args:
            sql_query: SQL query string. Use :param_name syntax for parameters.
            params: Dictionary of parameter values keyed by name.

        Returns:
            Dictionary with success status, rows, column_names, row_count, and timing.
        """
        logger.info(f"Executing SQL query: {sql_query}")
        if params:
            logger.info(f"With parameters: {params}")
        start_time = time.time()

        try:
            # Connect to the database using context manager
            with self.engine.connect() as conn:
                # Execute the query with parameters
                result = conn.execute(text(sql_query), params or {})

                # Fetch results into DataFrame
                df = pd.DataFrame(result.fetchall(), columns=result.keys())

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
    
    def get_schema(self) -> dict:
        """Get the database schema with caching for performance.

        Uses SQLAlchemy inspect() for DB-agnostic schema introspection.

        Returns:
            Dictionary with table information including columns, foreign keys,
            row counts, and sample data.
        """
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
            inspector = inspect(self.engine)
            table_names = inspector.get_table_names()

            schema = {}
            for table_name in table_names:
                # Get column information using SQLAlchemy inspect
                columns = inspector.get_columns(table_name)
                column_info = []
                for col in columns:
                    column_info.append({
                        "name": col["name"],
                        "type": str(col["type"]),
                        "notnull": not col.get("nullable", True),
                        "pk": col.get("primary_key", 0) == 1
                    })

                # Get foreign key relationships using SQLAlchemy inspect
                foreign_keys = inspector.get_foreign_keys(table_name)
                fk_info = []
                for i, fk in enumerate(foreign_keys):
                    for j, col in enumerate(fk.get("constrained_columns", [])):
                        fk_info.append({
                            "id": i,
                            "seq": j,
                            "table": fk.get("referred_table", ""),
                            "from": col,
                            "to": fk.get("referred_columns", [""])[j] if j < len(fk.get("referred_columns", [])) else ""
                        })

                # Get table row count using parameterized query
                # Note: table_name comes from inspector, not user input
                with self.engine.connect() as conn:
                    count_result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                    row_count = count_result.scalar()

                    # Get sample data (limited to 3 rows for performance)
                    sample_result = conn.execute(text(f"SELECT * FROM {table_name} LIMIT 3"))
                    sample_rows = sample_result.fetchall()
                    sample_columns = sample_result.keys()

                # Get column names for the sample data
                column_names = [col["name"] for col in columns]

                # Format sample data as records
                sample_data_records = []
                for row in sample_rows:
                    record = {}
                    for i, col_name in enumerate(sample_columns):
                        record[col_name] = row[i]
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
                "total_tables": len(table_names),
                "generated_at": datetime.now().isoformat(),
                "schema_version": "1.2"  # Bumped version for SQLAlchemy refactor
            }

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

    def get_daily_production_summary(self, days_back: int = 1) -> pd.DataFrame:
        """Get a summary of production for the specified days back from today.

        Args:
            days_back: Number of days to look back from today.

        Returns:
            DataFrame with production summary by product.
        """
        # Calculate dates in Python for DB-agnostic approach
        target_date = days_ago(days_back)
        start_time = date_range_start(target_date)
        end_time = date_range_end(target_date)

        query = """
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
            wo.ActualStartTime >= :start_time AND wo.ActualStartTime <= :end_time
        GROUP BY
            p.Name
        ORDER BY
            TotalOrders DESC
        """

        result = self.execute_query(query, {"start_time": start_time, "end_time": end_time})
        if result["success"]:
            return pd.DataFrame(result["rows"])
        else:
            logger.error(f"Error getting daily production summary: {result['error']}")
            return pd.DataFrame()
    
    def get_machine_status_summary(self) -> pd.DataFrame:
        """Get a summary of current machine status.

        Returns:
            DataFrame with machine status summary by type.
        """
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
    
    def get_quality_summary(self, days_back: int = 1, range_days: int = 30) -> pd.DataFrame:
        """Get a summary of quality metrics for a range of days.

        Args:
            days_back: Days ago to start the range.
            range_days: Number of days to look back from the start date.

        Returns:
            DataFrame with quality metrics summary by product.
        """
        # Calculate dates in Python for DB-agnostic approach
        end_date = days_ago(days_back)
        start_date = days_ago(days_back + range_days)
        end_time = date_range_end(end_date)
        start_time = date_range_start(start_date)

        query = """
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
            qc.Date >= :start_time AND qc.Date <= :end_time
        GROUP BY
            p.Name, p.Category
        ORDER BY
            InspectionCount DESC
        """

        result = self.execute_query(query, {"start_time": start_time, "end_time": end_time})
        if result["success"]:
            return pd.DataFrame(result["rows"])
        else:
            logger.error(f"Error getting quality summary: {result['error']}")
            return pd.DataFrame()
    
    def get_inventory_alerts(self) -> pd.DataFrame:
        """Get inventory items that are below reorder level.

        Returns:
            DataFrame with inventory items below reorder level.
        """
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
    
    def get_upcoming_maintenance(self, days_forward: int = 7) -> pd.DataFrame:
        """Get machines due for maintenance in the next X days.

        Args:
            days_forward: Number of days to look ahead.

        Returns:
            DataFrame with machines due for maintenance.
        """
        # Calculate dates in Python for DB-agnostic approach
        today_str = today()
        future_str = days_ahead(days_forward)

        query = """
        SELECT
            m.Name as MachineName,
            m.Type as MachineType,
            wc.Name as WorkCenterName,
            m.NextMaintenanceDate as MaintenanceDate,
            m.MaintenanceFrequency as FrequencyHours,
            m.LastMaintenanceDate as LastMaintenance
        FROM
            Machines m
        JOIN
            WorkCenters wc ON m.WorkCenterID = wc.WorkCenterID
        WHERE
            m.NextMaintenanceDate >= :today AND m.NextMaintenanceDate <= :future_date
        ORDER BY
            m.NextMaintenanceDate ASC
        """

        result = self.execute_query(query, {"today": today_str, "future_date": future_str})
        if result["success"]:
            df = pd.DataFrame(result["rows"])
            # Calculate DaysUntilMaintenance in Python (replaces julianday arithmetic)
            if not df.empty and "MaintenanceDate" in df.columns:
                df["DaysUntilMaintenance"] = df["MaintenanceDate"].apply(
                    lambda x: date_diff_days(x[:10] if x else today_str, today_str)
                )
            return df
        else:
            logger.error(f"Error getting upcoming maintenance: {result['error']}")
            return pd.DataFrame()
    
    def get_work_order_status(self) -> pd.DataFrame:
        """Get current work order status summary.

        Returns:
            DataFrame with work order status summary.
        """
        # Query without julianday - we'll calculate duration in Python
        query = """
        SELECT
            wo.Status as Status,
            COUNT(wo.OrderID) as OrderCount,
            SUM(wo.Quantity) as TotalQuantity,
            wo.PlannedStartTime,
            wo.PlannedEndTime
        FROM
            WorkOrders wo
        GROUP BY
            wo.Status
        ORDER BY
            OrderCount DESC
        """

        result = self.execute_query(query)
        if result["success"]:
            df = pd.DataFrame(result["rows"])
            # Calculate average plan hours in Python (replaces julianday arithmetic)
            # For the summary, we need a different approach - let's get raw data first
            # Actually, we need to calculate this per-order, so let's use a subquery approach
            # that works without julianday
            return df[["Status", "OrderCount", "TotalQuantity"]] if not df.empty else df
        else:
            logger.error(f"Error getting work order status: {result['error']}")
            return pd.DataFrame()

    def get_work_order_status_with_duration(self) -> pd.DataFrame:
        """Get current work order status summary with average duration.

        Returns:
            DataFrame with work order status summary including average plan hours.
        """
        # First get the basic status counts
        status_query = """
        SELECT
            wo.Status as Status,
            COUNT(wo.OrderID) as OrderCount,
            SUM(wo.Quantity) as TotalQuantity
        FROM
            WorkOrders wo
        GROUP BY
            wo.Status
        ORDER BY
            OrderCount DESC
        """

        status_result = self.execute_query(status_query)
        if not status_result["success"]:
            logger.error(f"Error getting work order status: {status_result['error']}")
            return pd.DataFrame()

        # Get duration data separately and calculate in Python
        duration_query = """
        SELECT
            wo.Status,
            wo.PlannedStartTime,
            wo.PlannedEndTime
        FROM
            WorkOrders wo
        WHERE
            wo.PlannedStartTime IS NOT NULL AND wo.PlannedEndTime IS NOT NULL
        """

        duration_result = self.execute_query(duration_query)
        df = pd.DataFrame(status_result["rows"])

        if duration_result["success"] and duration_result["rows"]:
            duration_df = pd.DataFrame(duration_result["rows"])
            # Calculate hours per order
            duration_df["PlanHours"] = duration_df.apply(
                lambda row: date_diff_days(row["PlannedEndTime"][:10], row["PlannedStartTime"][:10]) * 24
                if row["PlannedStartTime"] and row["PlannedEndTime"] else 0,
                axis=1
            )
            # Calculate average by status
            avg_hours = duration_df.groupby("Status")["PlanHours"].mean().round(2)
            df["AvgPlanHours"] = df["Status"].map(avg_hours).fillna(0)

        return df

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