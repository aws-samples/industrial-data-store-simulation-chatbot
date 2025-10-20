"""
Database Tools for MES Agents.

This module provides Strands SDK tools for SQLite database access with enhanced
error handling, intelligent suggestions, and educational feedback.

Key Tools:
- run_sqlite_query: Execute SQL with comprehensive error analysis
- get_database_schema: Retrieve database structure information

Features:
- Query validation and safety checks
- SQLite-specific error analysis
- Recovery suggestions and educational tips
- Performance monitoring and optimization hints
"""

import sqlite3
import pandas as pd
import logging
from typing import Dict, Any, List, Optional
from strands import tool
from ..error_handling import IntelligentErrorAnalyzer, ErrorContext, TimeoutHandler
from datetime import datetime


@tool
def run_sqlite_query(query: str) -> Dict[str, Any]:
    """
    Execute SQL query on MES SQLite database with enhanced error handling and recovery.
    
    Args:
        query: SQL query string to execute
        
    Returns:
        Dictionary containing query results, metadata, and comprehensive error analysis
    """
    logger = logging.getLogger(__name__)
    start_time = datetime.now()
    
    try:
        # Validate query before execution
        validation_result = _validate_query(query)
        if not validation_result['valid']:
            return _create_validation_error_response(query, validation_result)
        
        # Connect to the MES database with timeout
        conn = sqlite3.connect('mes.db', timeout=30.0)
        
        try:
            # Execute query and get results as DataFrame
            df = pd.read_sql_query(query, conn)
            
            # Convert DataFrame to list of dictionaries for agent processing
            results = df.to_dict('records')
            
            # Get column information
            columns = list(df.columns)
            row_count = len(df)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return {
                'success': True,
                'results': results,
                'columns': columns,
                'row_count': row_count,
                'query': query,
                'execution_time': execution_time,
                'data_types': {col: str(df[col].dtype) for col in df.columns} if not df.empty else {},
                'query_metadata': {
                    'has_results': row_count > 0,
                    'result_size': 'large' if row_count > 1000 else 'medium' if row_count > 100 else 'small',
                    'columns_count': len(columns)
                }
            }
            
        finally:
            conn.close()
        
    except sqlite3.Error as e:
        return _handle_sqlite_error(e, query, start_time)
        
    except Exception as e:
        return _handle_general_error(e, query, start_time)


def _get_sqlite_error_suggestions(error_message: str, query: str) -> List[str]:
    """
    Provide intelligent suggestions for common SQLite errors.
    
    Args:
        error_message: The SQLite error message
        query: The original query that caused the error
        
    Returns:
        List of helpful suggestions
    """
    suggestions = []
    error_lower = error_message.lower()
    
    if 'no such table' in error_lower:
        suggestions.extend([
            "The table name in your query doesn't exist in the database.",
            "Use the get_database_schema tool to see available tables.",
            "Check for typos in the table name."
        ])
    
    elif 'no such column' in error_lower:
        suggestions.extend([
            "The column name in your query doesn't exist in the specified table.",
            "Use the get_database_schema tool to see available columns for the table.",
            "Check for typos in the column name."
        ])
    
    elif 'syntax error' in error_lower:
        suggestions.extend([
            "There's a syntax error in your SQL query.",
            "Check for missing commas, parentheses, or quotes.",
            "Verify that SQL keywords are spelled correctly."
        ])
    
    elif 'ambiguous column name' in error_lower:
        suggestions.extend([
            "A column name appears in multiple tables in your JOIN query.",
            "Use table aliases to specify which table the column belongs to.",
            "Example: SELECT t1.column_name FROM table1 t1 JOIN table2 t2..."
        ])
    
    elif 'datatype mismatch' in error_lower:
        suggestions.extend([
            "There's a data type mismatch in your query.",
            "Check that you're comparing compatible data types.",
            "Use CAST() function if you need to convert data types."
        ])
    
    else:
        suggestions.extend([
            "Review your SQL query syntax.",
            "Check table and column names for accuracy.",
            "Use the get_database_schema tool to understand the database structure."
        ])
    
    return suggestions


@tool  
def get_database_schema(table_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Retrieve database schema information for agent analysis.
    
    Args:
        table_name: Optional specific table name. If None, returns all tables.
        
    Returns:
        Dictionary containing comprehensive schema information
    """
    try:
        conn = sqlite3.connect('mes.db')
        cursor = conn.cursor()
        
        if table_name:
            # Get specific table schema
            schema_info = _get_table_schema(cursor, table_name)
            if not schema_info:
                return {
                    'success': False,
                    'error': f"Table '{table_name}' not found",
                    'available_tables': _get_all_table_names(cursor)
                }
            return {
                'success': True,
                'table_name': table_name,
                'schema': schema_info
            }
        else:
            # Get all tables schema
            all_tables = _get_all_tables_schema(cursor)
            return {
                'success': True,
                'tables': all_tables,
                'table_count': len(all_tables)
            }
            
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'error_type': 'schema_error'
        }
    finally:
        conn.close()


def _get_table_schema(cursor: sqlite3.Cursor, table_name: str) -> Optional[Dict[str, Any]]:
    """Get detailed schema information for a specific table."""
    try:
        # Get table info
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        
        if not columns:
            return None
            
        # Format column information
        column_info = []
        for col in columns:
            column_info.append({
                'name': col[1],
                'type': col[2],
                'not_null': bool(col[3]),
                'default_value': col[4],
                'primary_key': bool(col[5])
            })
        
        # Get sample data (first 3 rows)
        cursor.execute(f"SELECT * FROM {table_name} LIMIT 3")
        sample_rows = cursor.fetchall()
        
        # Get row count
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        row_count = cursor.fetchone()[0]
        
        return {
            'columns': column_info,
            'sample_data': sample_rows,
            'row_count': row_count,
            'column_count': len(column_info)
        }
        
    except sqlite3.Error:
        return None


def _get_all_tables_schema(cursor: sqlite3.Cursor) -> Dict[str, Any]:
    """Get schema information for all tables in the database."""
    # Get all table names
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    table_names = [row[0] for row in cursor.fetchall()]
    
    tables_info = {}
    for table_name in table_names:
        schema = _get_table_schema(cursor, table_name)
        if schema:
            tables_info[table_name] = schema
    
    return tables_info


def _get_all_table_names(cursor: sqlite3.Cursor) -> List[str]:
    """Get list of all table names in the database."""
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    return [row[0] for row in cursor.fetchall()]


def _validate_query(query: str) -> Dict[str, Any]:
    """
    Validate SQL query before execution.
    
    Args:
        query: SQL query string
        
    Returns:
        Dictionary with validation results
    """
    validation_result = {'valid': True, 'warnings': [], 'suggestions': []}
    
    query_lower = query.lower().strip()
    
    # Check for empty query
    if not query_lower:
        validation_result['valid'] = False
        validation_result['error'] = 'Query cannot be empty'
        return validation_result
    
    # Check for dangerous operations (basic safety)
    dangerous_keywords = ['drop', 'delete', 'truncate', 'alter', 'create', 'insert', 'update']
    if any(keyword in query_lower for keyword in dangerous_keywords):
        validation_result['valid'] = False
        validation_result['error'] = 'Modifying operations are not allowed. Use SELECT queries only.'
        validation_result['suggestions'] = ['Use SELECT statements to query data without modifying it']
        return validation_result
    
    # Check for SELECT statement
    if not query_lower.startswith('select'):
        validation_result['warnings'].append('Query should start with SELECT for data retrieval')
    
    # Check for potential performance issues
    if 'select *' in query_lower and 'limit' not in query_lower:
        validation_result['warnings'].append('Consider using LIMIT clause with SELECT * for better performance')
        validation_result['suggestions'].append('Add "LIMIT 100" to limit results for testing')
    
    # Check for common syntax issues
    if query_lower.count('(') != query_lower.count(')'):
        validation_result['valid'] = False
        validation_result['error'] = 'Unmatched parentheses in query'
        return validation_result
    
    return validation_result


def _create_validation_error_response(query: str, validation_result: Dict[str, Any]) -> Dict[str, Any]:
    """Create error response for validation failures."""
    return {
        'success': False,
        'error': validation_result.get('error', 'Query validation failed'),
        'error_type': 'validation_error',
        'query': query,
        'suggestions': validation_result.get('suggestions', []),
        'warnings': validation_result.get('warnings', []),
        'educational_content': [
            "💡 **Query Guidelines**: Use SELECT statements to retrieve data safely",
            "🔒 **Security**: Modifying operations (INSERT, UPDATE, DELETE) are not allowed",
            "⚡ **Performance**: Use LIMIT clauses to control result size"
        ]
    }


def _handle_sqlite_error(error: sqlite3.Error, query: str, start_time: datetime) -> Dict[str, Any]:
    """
    Handle SQLite errors with comprehensive analysis and recovery suggestions.
    
    Args:
        error: SQLite error object
        query: Original query
        start_time: Query start time
        
    Returns:
        Comprehensive error response with recovery options
    """
    logger = logging.getLogger(__name__)
    execution_time = (datetime.now() - start_time).total_seconds()
    error_message = str(error)
    
    # Create error context for analysis
    error_context = ErrorContext(
        original_query=query,
        error_message=error_message,
        error_type='sqlite_error',
        timestamp=datetime.now(),
        execution_time=execution_time
    )
    
    # Analyze error with intelligent analyzer
    analyzer = IntelligentErrorAnalyzer()
    analysis = analyzer.analyze_error(error_context)
    
    # Enhanced SQLite-specific suggestions
    sqlite_suggestions = _get_enhanced_sqlite_suggestions(error_message, query)
    
    # Try to provide recovery options
    recovery_options = _generate_sqlite_recovery_options(error_message, query)
    
    logger.warning(f"SQLite error in query: {query[:100]}... Error: {error_message}")
    
    return {
        'success': False,
        'error': error_message,
        'error_type': 'sqlite_error',
        'error_category': analysis.category.value,
        'severity': analysis.severity.value,
        'query': query,
        'execution_time': execution_time,
        'user_friendly_message': analysis.user_friendly_message,
        'root_cause': analysis.root_cause,
        'suggestions': sqlite_suggestions,
        'recovery_options': recovery_options,
        'educational_content': analysis.educational_content,
        'alternative_approaches': analysis.alternative_approaches,
        'technical_details': {
            'sqlite_error_code': getattr(error, 'sqlite_errorcode', None),
            'sqlite_error_name': getattr(error, 'sqlite_errorname', None)
        }
    }


def _handle_general_error(error: Exception, query: str, start_time: datetime) -> Dict[str, Any]:
    """
    Handle general errors with comprehensive analysis.
    
    Args:
        error: Exception object
        query: Original query
        start_time: Query start time
        
    Returns:
        Comprehensive error response
    """
    logger = logging.getLogger(__name__)
    execution_time = (datetime.now() - start_time).total_seconds()
    error_message = str(error)
    
    # Create error context for analysis
    error_context = ErrorContext(
        original_query=query,
        error_message=error_message,
        error_type='general_error',
        timestamp=datetime.now(),
        execution_time=execution_time,
        stack_trace=str(error.__class__.__name__)
    )
    
    # Analyze error
    analyzer = IntelligentErrorAnalyzer()
    analysis = analyzer.analyze_error(error_context)
    
    logger.error(f"General error in query: {query[:100]}... Error: {error_message}")
    
    return {
        'success': False,
        'error': error_message,
        'error_type': 'general_error',
        'error_category': analysis.category.value,
        'severity': analysis.severity.value,
        'query': query,
        'execution_time': execution_time,
        'user_friendly_message': analysis.user_friendly_message,
        'root_cause': analysis.root_cause,
        'suggestions': [
            'Check query syntax and formatting',
            'Verify database connectivity',
            'Try a simpler version of the query'
        ],
        'recovery_options': [
            'Retry the query after checking syntax',
            'Use the schema tool to verify table structure',
            'Break complex queries into simpler parts'
        ],
        'educational_content': analysis.educational_content,
        'alternative_approaches': analysis.alternative_approaches
    }


def _get_enhanced_sqlite_suggestions(error_message: str, query: str) -> List[str]:
    """
    Provide enhanced intelligent suggestions for SQLite errors.
    
    Args:
        error_message: The SQLite error message
        query: The original query that caused the error
        
    Returns:
        List of enhanced suggestions
    """
    suggestions = []
    error_lower = error_message.lower()
    query_lower = query.lower()
    
    if 'no such table' in error_lower:
        # Extract table name from error if possible
        table_name = _extract_table_name_from_error(error_message)
        suggestions.extend([
            f"The table '{table_name}' doesn't exist in the MES database" if table_name else "The referenced table doesn't exist",
            "Use 'get_database_schema()' to see all available tables",
            "Check for typos in the table name - names are case-sensitive",
            "Common MES tables include: work_orders, quality_checks, equipment_status, inventory_items"
        ])
    
    elif 'no such column' in error_lower:
        column_name = _extract_column_name_from_error(error_message)
        suggestions.extend([
            f"The column '{column_name}' doesn't exist in the specified table" if column_name else "The referenced column doesn't exist",
            "Use 'get_database_schema(table_name)' to see available columns",
            "Check column name spelling and case sensitivity",
            "Verify you're using the correct table for this column"
        ])
    
    elif 'syntax error' in error_lower:
        suggestions.extend([
            "There's a SQL syntax error in your query",
            "Check for missing commas between column names",
            "Verify parentheses are properly matched",
            "Ensure string values are enclosed in quotes",
            "Check that SQL keywords are spelled correctly"
        ])
        
        # Specific syntax suggestions based on query content
        if 'join' in query_lower and 'on' not in query_lower:
            suggestions.append("JOIN clauses require an ON condition to specify how tables are related")
        
        if query_lower.count("'") % 2 != 0:
            suggestions.append("Check for unmatched single quotes around string values")
    
    elif 'ambiguous column name' in error_lower:
        suggestions.extend([
            "A column name appears in multiple tables in your JOIN",
            "Use table aliases to specify which table: 'table_alias.column_name'",
            "Example: SELECT w.order_id, q.defect_count FROM work_orders w JOIN quality_checks q ON w.order_id = q.order_id"
        ])
    
    elif 'datatype mismatch' in error_lower:
        suggestions.extend([
            "You're comparing incompatible data types",
            "Use CAST() to convert data types: CAST(column AS INTEGER)",
            "Check that date comparisons use proper date format",
            "Ensure numeric comparisons don't include text values"
        ])
    
    elif 'database is locked' in error_lower:
        suggestions.extend([
            "The database is currently locked by another process",
            "Wait a moment and try again",
            "Check if other applications are accessing the database",
            "This is usually a temporary issue that resolves quickly"
        ])
    
    else:
        # Generic suggestions for unknown SQLite errors
        suggestions.extend([
            "Review your SQL query syntax carefully",
            "Check table and column names for accuracy",
            "Use the database schema tool to understand the structure",
            "Try simplifying the query to isolate the issue"
        ])
    
    return suggestions


def _generate_sqlite_recovery_options(error_message: str, query: str) -> List[str]:
    """Generate specific recovery options for SQLite errors."""
    recovery_options = []
    error_lower = error_message.lower()
    
    if 'no such table' in error_lower:
        recovery_options.extend([
            "Check available tables with: get_database_schema()",
            "Try a basic query: SELECT name FROM sqlite_master WHERE type='table'",
            "Verify the correct table name from the schema"
        ])
    
    elif 'no such column' in error_lower:
        recovery_options.extend([
            "Check table structure with: get_database_schema('table_name')",
            "List all columns: SELECT * FROM table_name LIMIT 1",
            "Verify column names match exactly (case-sensitive)"
        ])
    
    elif 'syntax error' in error_lower:
        recovery_options.extend([
            "Start with a simple SELECT: SELECT * FROM table_name LIMIT 10",
            "Build the query step by step, testing each part",
            "Use an online SQL syntax checker to validate the query"
        ])
    
    else:
        recovery_options.extend([
            "Try a simplified version of the query",
            "Check the database schema for correct table/column names",
            "Test with a basic SELECT statement first"
        ])
    
    return recovery_options


def _extract_table_name_from_error(error_message: str) -> Optional[str]:
    """Extract table name from SQLite error message."""
    import re
    
    # Pattern to match "no such table: table_name"
    match = re.search(r'no such table:\s*(\w+)', error_message, re.IGNORECASE)
    if match:
        return match.group(1)
    
    return None


def _extract_column_name_from_error(error_message: str) -> Optional[str]:
    """Extract column name from SQLite error message."""
    import re
    
    # Pattern to match "no such column: column_name"
    match = re.search(r'no such column:\s*(\w+)', error_message, re.IGNORECASE)
    if match:
        return match.group(1)
    
    return None