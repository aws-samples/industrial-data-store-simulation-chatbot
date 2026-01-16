"""
Database Tools for Production Meeting Agents.

This module provides Strands SDK tools for database access specifically
designed for production meeting contexts. It includes enhanced error handling,
production meeting context awareness, and intelligent suggestions.

Key Tools:
- run_sqlite_query: Execute SQL with production meeting context
- get_database_schema: Retrieve database structure information
- get_production_context: Get meeting timeframes and production context

Features:
- Production meeting specific query validation
- DB-agnostic patterns via SQLAlchemy
- Meeting context awareness and timeframe management
- Performance monitoring optimized for meeting efficiency
"""

import pandas as pd
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from functools import lru_cache
from strands import tool
from ..error_handling import IntelligentErrorAnalyzer, ErrorContext
from app_factory.shared.database import DatabaseManager
from app_factory.shared.db_utils import (
    days_ago, days_ahead, today,
    date_range_start, date_range_end
)

# Module logger
logger = logging.getLogger(__name__)

# Performance optimization: Cache frequently accessed data
_schema_cache = None
_schema_cache_time = None
CACHE_DURATION = 300  # 5 minutes


@tool
def run_sqlite_query(query: str) -> Dict[str, Any]:
    """
    Execute SQL query on MES SQLite database with production meeting context.
    
    This tool is optimized for production meeting scenarios, providing enhanced
    error handling and context-aware analysis for manufacturing data queries.
    
    Args:
        query: SQL query string to execute
        
    Returns:
        Dictionary containing query results, metadata, and production meeting insights
    """
    logger = logging.getLogger(__name__)
    start_time = datetime.now()
    
    # Log query for performance monitoring
    logger.info(f"Executing production meeting query: {query[:100]}{'...' if len(query) > 100 else ''}")

    try:
        # Validate query BEFORE adding LIMIT clause
        validation_result = _validate_production_query(query)
        if not validation_result['valid']:
            return _create_production_validation_error_response(query, validation_result)

        # Performance optimization: Limit result size for meeting efficiency
        MAX_ROWS_FOR_MEETINGS = 1000
        if 'LIMIT' not in query.upper():
            query = f"{query.rstrip(';')} LIMIT {MAX_ROWS_FOR_MEETINGS}"
            logger.debug(f"Added LIMIT clause for meeting efficiency: {MAX_ROWS_FOR_MEETINGS} rows")
        
        # Use the shared database manager for consistency
        db_manager = DatabaseManager()
        result = db_manager.execute_query(query)
        
        if result['success']:
            # Enhance results with production meeting context
            enhanced_result = _enhance_with_production_context(result, query)
            enhanced_result['meeting_insights'] = _generate_meeting_insights(result, query)
            return enhanced_result
        else:
            # Handle errors with production meeting specific analysis
            return _handle_production_query_error(result, query, start_time)
            
    except Exception as e:
        return _handle_general_production_error(e, query, start_time)


@tool
def get_database_schema(table_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Retrieve database schema information optimized for production meeting analysis.
    
    This tool provides comprehensive schema information with production meeting
    context, highlighting tables and columns most relevant for daily meetings.
    Uses caching to improve performance for repeated schema requests.
    
    Args:
        table_name: Optional specific table name. If None, returns production-relevant tables.
        
    Returns:
        Dictionary containing schema information with production meeting insights
    """
    global _schema_cache, _schema_cache_time
    
    # Check if we have a valid cached schema
    current_time = datetime.now()
    if (_schema_cache is not None and 
        _schema_cache_time is not None and 
        (current_time - _schema_cache_time).total_seconds() < CACHE_DURATION):
        logger.debug("Using cached database schema")
        if table_name:
            return _schema_cache.get(table_name, {"error": f"Table {table_name} not found in schema"})
        return _schema_cache
    try:
        # Use the shared database manager for consistency
        db_manager = DatabaseManager()
        schema = db_manager.get_schema()
        
        if table_name:
            # Get specific table schema with production context
            if table_name in schema:
                table_schema = schema[table_name]
                return {
                    'success': True,
                    'table_name': table_name,
                    'schema': table_schema,
                    'production_relevance': _get_table_production_relevance(table_name),
                    'meeting_usage_tips': _get_table_meeting_tips(table_name),
                    'common_queries': _get_common_production_queries(table_name)
                }
            else:
                available_tables = list(schema.keys())
                production_tables = _filter_production_relevant_tables(available_tables)
                return {
                    'success': False,
                    'error': f"Table '{table_name}' not found",
                    'available_tables': available_tables,
                    'production_relevant_tables': production_tables,
                    'suggestion': f"Try one of the production-relevant tables: {', '.join(production_tables[:5])}"
                }
        else:
            # Get all tables with production meeting focus
            production_tables = _get_production_focused_schema(schema)
            
            # Cache the schema for performance optimization
            _schema_cache = {
                'success': True,
                'tables': production_tables,
                'table_count': len(production_tables),
                'meeting_priorities': _get_meeting_table_priorities(),
                'quick_start_queries': _get_quick_start_queries()
            }
            _schema_cache_time = datetime.now()
            logger.debug("Database schema cached for performance optimization")
            
            return _schema_cache
            
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'error_type': 'schema_error',
            'recovery_suggestions': [
                'Check database connectivity',
                'Verify database file exists',
                'Try again in a moment'
            ]
        }


@tool
def get_production_context(meeting_type: str = 'daily', days_back: int = 1) -> Dict[str, Any]:
    """
    Get current production meeting context and timeframes.
    
    This tool provides essential context for production meetings, including
    relevant time ranges, key metrics, and focus areas based on meeting type.
    
    Args:
        meeting_type: Type of meeting ('daily', 'weekly', 'monthly')
        days_back: Number of days to look back from today
        
    Returns:
        Dictionary containing production context and meeting-relevant information
    """
    try:
        current_time = datetime.now()
        
        # Calculate time ranges based on meeting type
        time_ranges = _calculate_meeting_time_ranges(meeting_type, days_back, current_time)
        
        # Get production context data
        db_manager = DatabaseManager()
        
        # Get basic production metrics for context
        production_summary = _get_production_summary_for_context(db_manager, time_ranges)
        quality_summary = _get_quality_summary_for_context(db_manager, time_ranges)
        equipment_summary = _get_equipment_summary_for_context(db_manager, time_ranges)
        inventory_alerts = _get_inventory_alerts_for_context(db_manager)
        
        return {
            'success': True,
            'meeting_type': meeting_type,
            'time_ranges': time_ranges,
            'current_timestamp': current_time.isoformat(),
            'production_context': {
                'production_summary': production_summary,
                'quality_summary': quality_summary,
                'equipment_summary': equipment_summary,
                'inventory_alerts': inventory_alerts
            },
            'meeting_focus_areas': _get_meeting_focus_areas(meeting_type),
            'recommended_queries': _get_context_recommended_queries(meeting_type, time_ranges),
            'key_metrics_to_review': _get_key_metrics_for_meeting(meeting_type)
        }
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error getting production context: {e}")
        
        return {
            'success': False,
            'error': str(e),
            'error_type': 'context_error',
            'fallback_context': _get_fallback_production_context(meeting_type, days_back),
            'recovery_suggestions': [
                'Try with default parameters',
                'Check database connectivity',
                'Use basic time ranges for manual analysis'
            ]
        }


def _validate_production_query(query: str) -> Dict[str, Any]:
    """
    Validate SQL query with production meeting specific checks.
    
    Args:
        query: SQL query string
        
    Returns:
        Dictionary with validation results and production-specific suggestions
    """
    validation_result = {'valid': True, 'warnings': [], 'suggestions': []}
    
    query_lower = query.lower().strip()
    
    # Basic validation
    if not query_lower:
        validation_result['valid'] = False
        validation_result['error'] = 'Query cannot be empty'
        return validation_result
    
    # Check for dangerous operations
    dangerous_keywords = ['drop', 'delete', 'truncate', 'alter', 'create', 'insert', 'update']
    if any(keyword in query_lower for keyword in dangerous_keywords):
        validation_result['valid'] = False
        validation_result['error'] = 'Modifying operations are not allowed in production meetings. Use SELECT queries only.'
        validation_result['suggestions'] = [
            'Use SELECT statements to analyze production data',
            'Focus on data retrieval for meeting insights'
        ]
        return validation_result
    
    # Production meeting specific validations
    if not query_lower.startswith('select'):
        validation_result['warnings'].append('Production meeting queries should use SELECT for data analysis')
    
    # Check for performance considerations in meeting context
    if 'select *' in query_lower and 'limit' not in query_lower:
        validation_result['warnings'].append('Consider using LIMIT for faster meeting responses')
        validation_result['suggestions'].append('Add "LIMIT 100" for quicker results during meetings')
    
    # Suggest production-relevant enhancements
    if 'workorders' in query_lower or 'work_orders' in query_lower:
        if 'date' not in query_lower and 'time' not in query_lower:
            validation_result['suggestions'].append('Consider adding date filters for current production period')
    
    if 'qualitycontrol' in query_lower or 'quality_control' in query_lower:
        if 'defect' not in query_lower and 'yield' not in query_lower:
            validation_result['suggestions'].append('Consider including defect rates or yield metrics for quality analysis')
    
    return validation_result


def _enhance_with_production_context(result: Dict[str, Any], query: str) -> Dict[str, Any]:
    """
    Enhance query results with production meeting context.
    
    Args:
        result: Original query result
        query: Original SQL query
        
    Returns:
        Enhanced result with production context
    """
    enhanced_result = result.copy()
    
    # Add production meeting metadata
    enhanced_result['production_metadata'] = {
        'query_type': _classify_production_query(query),
        'meeting_relevance': _assess_meeting_relevance(result, query),
        'data_freshness': _assess_data_freshness(result),
        'actionable_insights': _identify_actionable_insights(result, query)
    }
    
    # Add meeting-specific formatting suggestions
    enhanced_result['meeting_presentation'] = {
        'summary_format': _suggest_summary_format(result, query),
        'key_highlights': _extract_key_highlights(result, query),
        'follow_up_questions': _suggest_follow_up_questions(result, query)
    }
    
    return enhanced_result


def _generate_meeting_insights(result: Dict[str, Any], query: str) -> List[str]:
    """
    Generate production meeting specific insights from query results.
    
    Args:
        result: Query result data
        query: Original SQL query
        
    Returns:
        List of meeting-relevant insights
    """
    insights = []
    
    if not result.get('success') or not result.get('rows'):
        return ['No data available for analysis']
    
    rows = result['rows']
    row_count = len(rows)
    
    # General insights based on data volume
    if row_count == 0:
        insights.append('No records found - this may indicate normal operations or a data issue to investigate')
    elif row_count > 100:
        insights.append(f'Large dataset ({row_count} records) - consider filtering for meeting focus')
    else:
        insights.append(f'Manageable dataset ({row_count} records) - good for detailed meeting review')
    
    # Query-specific insights
    query_lower = query.lower()
    
    if 'workorder' in query_lower or 'work_order' in query_lower:
        insights.extend(_generate_work_order_insights(rows))
    
    if 'quality' in query_lower:
        insights.extend(_generate_quality_insights(rows))
    
    if 'machine' in query_lower or 'equipment' in query_lower:
        insights.extend(_generate_equipment_insights(rows))
    
    if 'inventory' in query_lower:
        insights.extend(_generate_inventory_insights(rows))
    
    return insights


def _get_production_focused_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Filter and prioritize schema information for production meetings.
    
    Args:
        schema: Full database schema
        
    Returns:
        Production-focused schema information
    """
    production_tables = {}
    
    # Priority order for production meetings
    priority_tables = [
        'WorkOrders', 'QualityControl', 'Machines', 'Inventory',
        'Products', 'WorkCenters', 'Suppliers', 'Employees'
    ]
    
    # Add priority tables first
    for table_name in priority_tables:
        if table_name in schema:
            production_tables[table_name] = schema[table_name]
            production_tables[table_name]['meeting_priority'] = 'high'
            production_tables[table_name]['usage_tips'] = _get_table_meeting_tips(table_name)
    
    # Add other tables with lower priority
    for table_name, table_info in schema.items():
        if table_name not in production_tables and table_name != '__metadata__':
            production_tables[table_name] = table_info
            production_tables[table_name]['meeting_priority'] = 'medium'
            production_tables[table_name]['usage_tips'] = _get_table_meeting_tips(table_name)
    
    return production_tables


def _get_table_production_relevance(table_name: str) -> Dict[str, Any]:
    """Get production relevance information for a specific table."""
    relevance_map = {
        'WorkOrders': {
            'relevance': 'critical',
            'meeting_use': 'Daily production status, completion rates, delays',
            'key_metrics': ['completion_percentage', 'actual_production', 'scrap_quantity']
        },
        'QualityControl': {
            'relevance': 'critical',
            'meeting_use': 'Quality issues, defect rates, rework requirements',
            'key_metrics': ['defect_rate', 'yield_rate', 'rework_rate']
        },
        'Machines': {
            'relevance': 'high',
            'meeting_use': 'Equipment status, downtime, maintenance needs',
            'key_metrics': ['status', 'efficiency_factor', 'next_maintenance_date']
        },
        'Inventory': {
            'relevance': 'high',
            'meeting_use': 'Stock levels, shortages, reorder alerts',
            'key_metrics': ['quantity', 'reorder_level', 'lead_time']
        },
        'Products': {
            'relevance': 'medium',
            'meeting_use': 'Product specifications, categories, standards',
            'key_metrics': ['category', 'standard_time', 'quality_standard']
        }
    }
    
    return relevance_map.get(table_name, {
        'relevance': 'low',
        'meeting_use': 'Supporting information',
        'key_metrics': []
    })


def _get_table_meeting_tips(table_name: str) -> List[str]:
    """Get meeting-specific usage tips for a table."""
    tips_map = {
        'WorkOrders': [
            'Filter by recent dates for current production status',
            'Join with Products table for product-specific analysis',
            'Check ActualProduction vs Quantity for completion rates'
        ],
        'QualityControl': [
            'Focus on recent quality checks for current issues',
            'Look for patterns in defect rates by product or time',
            'Join with WorkOrders for production impact analysis'
        ],
        'Machines': [
            'Check Status field for current operational state',
            'Review NextMaintenanceDate for upcoming maintenance',
            'Analyze EfficiencyFactor for performance trends'
        ],
        'Inventory': [
            'Compare Quantity with ReorderLevel for shortage alerts',
            'Check LeadTime for supply chain planning',
            'Join with Suppliers for vendor performance'
        ]
    }
    
    return tips_map.get(table_name, [
        'Review table structure with get_database_schema()',
        'Start with simple SELECT queries',
        'Consider joining with related tables for context'
    ])


def _get_common_production_queries(table_name: str) -> List[str]:
    """Get common production queries for a specific table."""
    # Use actual dates for example queries (DB-agnostic)
    yesterday = days_ago(1)
    seven_days_ago = days_ago(7)
    seven_days_ahead_date = days_ahead(7)

    queries_map = {
        'WorkOrders': [
            f"SELECT * FROM WorkOrders WHERE ActualStartTime >= '{yesterday}'",
            "SELECT ProductID, SUM(ActualProduction) as Total FROM WorkOrders GROUP BY ProductID",
            "SELECT * FROM WorkOrders WHERE Status = 'in_progress'"
        ],
        'QualityControl': [
            f"SELECT * FROM QualityControl WHERE Date >= '{yesterday}'",
            f"SELECT AVG(DefectRate) as AvgDefectRate FROM QualityControl WHERE Date >= '{seven_days_ago}'",
            "SELECT * FROM QualityControl WHERE Result = 'fail'"
        ],
        'Machines': [
            "SELECT * FROM Machines WHERE Status != 'running'",
            "SELECT MachineID, EfficiencyFactor FROM Machines ORDER BY EfficiencyFactor DESC",
            f"SELECT * FROM Machines WHERE NextMaintenanceDate <= '{seven_days_ahead_date}'"
        ],
        'Inventory': [
            "SELECT * FROM Inventory WHERE Quantity < ReorderLevel",
            "SELECT * FROM Inventory WHERE Quantity <= 0",
            "SELECT ItemName, Quantity, ReorderLevel FROM Inventory ORDER BY Quantity ASC"
        ]
    }

    return queries_map.get(table_name, [
        f"SELECT * FROM {table_name} LIMIT 10",
        f"SELECT COUNT(*) FROM {table_name}",
        f"SELECT * FROM {table_name} ORDER BY rowid DESC LIMIT 5"
    ])


def _calculate_meeting_time_ranges(meeting_type: str, days_back: int, current_time: datetime) -> Dict[str, Any]:
    """Calculate appropriate time ranges for different meeting types."""
    ranges = {}
    
    if meeting_type == 'daily':
        # For daily meetings, focus on yesterday and today
        start_date = current_time - timedelta(days=days_back)
        end_date = current_time
        ranges['primary'] = {
            'start': start_date.strftime('%Y-%m-%d'),
            'end': end_date.strftime('%Y-%m-%d'),
            'description': f'Last {days_back} day(s)'
        }
        ranges['comparison'] = {
            'start': (start_date - timedelta(days=7)).strftime('%Y-%m-%d'),
            'end': (end_date - timedelta(days=7)).strftime('%Y-%m-%d'),
            'description': 'Same period last week'
        }
    
    elif meeting_type == 'weekly':
        # For weekly meetings, focus on the past week
        start_date = current_time - timedelta(days=7)
        end_date = current_time
        ranges['primary'] = {
            'start': start_date.strftime('%Y-%m-%d'),
            'end': end_date.strftime('%Y-%m-%d'),
            'description': 'Past week'
        }
        ranges['comparison'] = {
            'start': (start_date - timedelta(days=7)).strftime('%Y-%m-%d'),
            'end': (end_date - timedelta(days=7)).strftime('%Y-%m-%d'),
            'description': 'Previous week'
        }
    
    elif meeting_type == 'monthly':
        # For monthly meetings, focus on the past month
        start_date = current_time - timedelta(days=30)
        end_date = current_time
        ranges['primary'] = {
            'start': start_date.strftime('%Y-%m-%d'),
            'end': end_date.strftime('%Y-%m-%d'),
            'description': 'Past month'
        }
        ranges['comparison'] = {
            'start': (start_date - timedelta(days=30)).strftime('%Y-%m-%d'),
            'end': (end_date - timedelta(days=30)).strftime('%Y-%m-%d'),
            'description': 'Previous month'
        }
    
    return ranges


def _get_production_summary_for_context(db_manager: DatabaseManager, time_ranges: Dict[str, Any]) -> Dict[str, Any]:
    """Get production summary for meeting context."""
    try:
        primary_range = time_ranges['primary']
        start_time = date_range_start(primary_range['start'])
        end_time = date_range_end(primary_range['end'])

        query = """
        SELECT
            COUNT(wo.OrderID) as total_orders,
            SUM(wo.Quantity) as planned_quantity,
            SUM(wo.ActualProduction) as actual_production,
            SUM(wo.Scrap) as total_scrap,
            ROUND(AVG(CASE WHEN wo.Quantity > 0 THEN wo.ActualProduction * 100.0 / wo.Quantity ELSE 0 END), 2) as avg_completion_rate
        FROM WorkOrders wo
        WHERE wo.ActualStartTime >= :start_time AND wo.ActualStartTime <= :end_time
        """

        result = db_manager.execute_query(query, {"start_time": start_time, "end_time": end_time})
        if result['success'] and result['rows']:
            return result['rows'][0]
        else:
            return {'total_orders': 0, 'planned_quantity': 0, 'actual_production': 0, 'total_scrap': 0, 'avg_completion_rate': 0}

    except Exception:
        return {'error': 'Unable to retrieve production summary'}


def _get_quality_summary_for_context(db_manager: DatabaseManager, time_ranges: Dict[str, Any]) -> Dict[str, Any]:
    """Get quality summary for meeting context."""
    try:
        primary_range = time_ranges['primary']
        start_time = date_range_start(primary_range['start'])
        end_time = date_range_end(primary_range['end'])

        query = """
        SELECT
            COUNT(qc.CheckID) as total_checks,
            ROUND(AVG(qc.DefectRate) * 100, 2) as avg_defect_rate,
            ROUND(AVG(qc.YieldRate) * 100, 2) as avg_yield_rate,
            SUM(CASE WHEN qc.Result = 'pass' THEN 1 ELSE 0 END) as pass_count,
            SUM(CASE WHEN qc.Result = 'fail' THEN 1 ELSE 0 END) as fail_count
        FROM QualityControl qc
        WHERE qc.Date >= :start_time AND qc.Date <= :end_time
        """

        result = db_manager.execute_query(query, {"start_time": start_time, "end_time": end_time})
        if result['success'] and result['rows']:
            return result['rows'][0]
        else:
            return {'total_checks': 0, 'avg_defect_rate': 0, 'avg_yield_rate': 0, 'pass_count': 0, 'fail_count': 0}

    except Exception:
        return {'error': 'Unable to retrieve quality summary'}


def _get_equipment_summary_for_context(db_manager: DatabaseManager, time_ranges: Dict[str, Any]) -> Dict[str, Any]:
    """Get equipment summary for meeting context."""
    try:
        query = """
        SELECT 
            COUNT(m.MachineID) as total_machines,
            SUM(CASE WHEN m.Status = 'running' THEN 1 ELSE 0 END) as running_count,
            SUM(CASE WHEN m.Status = 'idle' THEN 1 ELSE 0 END) as idle_count,
            SUM(CASE WHEN m.Status = 'maintenance' THEN 1 ELSE 0 END) as maintenance_count,
            SUM(CASE WHEN m.Status = 'breakdown' THEN 1 ELSE 0 END) as breakdown_count,
            ROUND(AVG(m.EfficiencyFactor) * 100, 2) as avg_efficiency
        FROM Machines m
        """
        
        result = db_manager.execute_query(query)
        if result['success'] and result['rows']:
            return result['rows'][0]
        else:
            return {'total_machines': 0, 'running_count': 0, 'idle_count': 0, 'maintenance_count': 0, 'breakdown_count': 0, 'avg_efficiency': 0}
    
    except Exception:
        return {'error': 'Unable to retrieve equipment summary'}


def _get_inventory_alerts_for_context(db_manager: DatabaseManager) -> Dict[str, Any]:
    """Get inventory alerts for meeting context."""
    try:
        query = """
        SELECT 
            COUNT(i.ItemID) as total_items,
            SUM(CASE WHEN i.Quantity < i.ReorderLevel THEN 1 ELSE 0 END) as low_stock_count,
            SUM(CASE WHEN i.Quantity <= 0 THEN 1 ELSE 0 END) as out_of_stock_count
        FROM Inventory i
        """
        
        result = db_manager.execute_query(query)
        if result['success'] and result['rows']:
            return result['rows'][0]
        else:
            return {'total_items': 0, 'low_stock_count': 0, 'out_of_stock_count': 0}
    
    except Exception:
        return {'error': 'Unable to retrieve inventory alerts'}


# Helper functions for error handling and context generation
def _create_production_validation_error_response(query: str, validation_result: Dict[str, Any]) -> Dict[str, Any]:
    """Create error response for production query validation failures."""
    return {
        'success': False,
        'error': validation_result.get('error', 'Query validation failed'),
        'error_type': 'production_validation_error',
        'query': query,
        'suggestions': validation_result.get('suggestions', []),
        'warnings': validation_result.get('warnings', []),
        'meeting_guidance': [
            "🏭 **Production Focus**: Use queries that provide actionable meeting insights",
            "⏱️ **Meeting Efficiency**: Keep queries focused and time-bounded for quick results",
            "📊 **Data Analysis**: Focus on trends, exceptions, and key performance indicators"
        ]
    }


def _handle_production_query_error(result: Dict[str, Any], query: str, start_time: datetime) -> Dict[str, Any]:
    """Handle production query errors with meeting-specific context."""
    enhanced_result = result.copy()
    enhanced_result['meeting_impact'] = 'Query failed - consider alternative analysis approaches'
    enhanced_result['production_alternatives'] = [
        'Try a simpler version of the query',
        'Check table names with get_database_schema()',
        'Use get_production_context() for meeting-ready data'
    ]
    return enhanced_result


def _handle_general_production_error(error: Exception, query: str, start_time: datetime) -> Dict[str, Any]:
    """Handle general production errors with meeting context."""
    execution_time = (datetime.now() - start_time).total_seconds()
    
    return {
        'success': False,
        'error': str(error),
        'error_type': 'production_general_error',
        'query': query,
        'execution_time': execution_time,
        'meeting_impact': 'Unable to complete analysis - meeting can proceed with available data',
        'recovery_options': [
            'Use get_production_context() for basic meeting data',
            'Try get_database_schema() to understand available data',
            'Focus on manual review of key production metrics'
        ]
    }


# Additional helper functions for meeting insights
def _classify_production_query(query: str) -> str:
    """Classify the type of production query for meeting context."""
    query_lower = query.lower()
    
    if 'workorder' in query_lower or 'work_order' in query_lower:
        return 'production_analysis'
    elif 'quality' in query_lower:
        return 'quality_analysis'
    elif 'machine' in query_lower or 'equipment' in query_lower:
        return 'equipment_analysis'
    elif 'inventory' in query_lower:
        return 'inventory_analysis'
    else:
        return 'general_analysis'


def _assess_meeting_relevance(result: Dict[str, Any], query: str) -> str:
    """Assess how relevant the query results are for production meetings."""
    if not result.get('success') or not result.get('rows'):
        return 'low'
    
    row_count = len(result['rows'])
    query_type = _classify_production_query(query)
    
    if query_type in ['production_analysis', 'quality_analysis'] and row_count > 0:
        return 'high'
    elif query_type in ['equipment_analysis', 'inventory_analysis'] and row_count > 0:
        return 'medium'
    else:
        return 'low'


def _assess_data_freshness(result: Dict[str, Any]) -> str:
    """Assess how fresh/current the data is for meeting purposes."""
    # This is a simplified assessment - in a real implementation,
    # you would check timestamp fields in the data
    if result.get('success') and result.get('rows'):
        return 'current'
    else:
        return 'unknown'


def _identify_actionable_insights(result: Dict[str, Any], query: str) -> List[str]:
    """Identify actionable insights from query results for meetings."""
    insights = []
    
    if not result.get('success') or not result.get('rows'):
        return ['No actionable data available']
    
    rows = result['rows']
    query_type = _classify_production_query(query)
    
    if query_type == 'production_analysis':
        insights.append('Review production completion rates and identify bottlenecks')
    elif query_type == 'quality_analysis':
        insights.append('Address quality issues and implement corrective actions')
    elif query_type == 'equipment_analysis':
        insights.append('Schedule maintenance and address equipment issues')
    elif query_type == 'inventory_analysis':
        insights.append('Manage inventory levels and prevent stockouts')
    
    return insights


def _suggest_summary_format(result: Dict[str, Any], query: str) -> str:
    """Suggest how to format results for meeting presentation."""
    if not result.get('success'):
        return 'Error summary for meeting discussion'
    
    row_count = len(result.get('rows', []))
    query_type = _classify_production_query(query)
    
    if row_count <= 5:
        return 'Detailed review of all items'
    elif row_count <= 20:
        return 'Summary with key highlights'
    else:
        return 'Executive summary with top issues only'


def _extract_key_highlights(result: Dict[str, Any], query: str) -> List[str]:
    """Extract key highlights from query results for meeting focus."""
    highlights = []
    
    if not result.get('success') or not result.get('rows'):
        return ['No data highlights available']
    
    row_count = len(result['rows'])
    highlights.append(f'Found {row_count} records for analysis')
    
    query_type = _classify_production_query(query)
    if query_type == 'production_analysis':
        highlights.append('Focus on completion rates and production targets')
    elif query_type == 'quality_analysis':
        highlights.append('Review quality metrics and defect patterns')
    
    return highlights


def _suggest_follow_up_questions(result: Dict[str, Any], query: str) -> List[str]:
    """Suggest follow-up questions based on query results."""
    questions = []
    
    query_type = _classify_production_query(query)
    
    if query_type == 'production_analysis':
        questions.extend([
            'What are the root causes of any production delays?',
            'Which products or work centers need immediate attention?',
            'Are there resource constraints affecting production?'
        ])
    elif query_type == 'quality_analysis':
        questions.extend([
            'What are the main quality issues requiring immediate action?',
            'Which products have recurring quality problems?',
            'What corrective actions should be implemented?'
        ])
    
    return questions


def _generate_work_order_insights(rows: List[Dict]) -> List[str]:
    """Generate work order specific insights."""
    insights = []
    
    if not rows:
        return ['No work order data available']
    
    # Analyze completion rates if available
    completion_rates = []
    for row in rows:
        if 'CompletionPercentage' in row and row['CompletionPercentage'] is not None:
            completion_rates.append(float(row['CompletionPercentage']))
    
    if completion_rates:
        avg_completion = sum(completion_rates) / len(completion_rates)
        if avg_completion < 80:
            insights.append(f'Low average completion rate ({avg_completion:.1f}%) - investigate delays')
        elif avg_completion > 95:
            insights.append(f'Excellent completion rate ({avg_completion:.1f}%) - production on track')
    
    return insights


def _generate_quality_insights(rows: List[Dict]) -> List[str]:
    """Generate quality specific insights."""
    insights = []
    
    if not rows:
        return ['No quality data available']
    
    # Analyze defect rates if available
    defect_rates = []
    for row in rows:
        if 'AvgDefectRate' in row and row['AvgDefectRate'] is not None:
            defect_rates.append(float(row['AvgDefectRate']))
    
    if defect_rates:
        avg_defect_rate = sum(defect_rates) / len(defect_rates)
        if avg_defect_rate > 5:
            insights.append(f'High defect rate ({avg_defect_rate:.1f}%) - quality issues need attention')
        elif avg_defect_rate < 1:
            insights.append(f'Excellent quality ({avg_defect_rate:.1f}% defect rate)')
    
    return insights


def _generate_equipment_insights(rows: List[Dict]) -> List[str]:
    """Generate equipment specific insights."""
    insights = []
    
    if not rows:
        return ['No equipment data available']
    
    # Count equipment status if available
    status_counts = {}
    for row in rows:
        if 'Status' in row and row['Status']:
            status = row['Status']
            status_counts[status] = status_counts.get(status, 0) + 1
    
    if status_counts:
        if status_counts.get('breakdown', 0) > 0:
            insights.append(f"{status_counts['breakdown']} machines in breakdown status - immediate attention needed")
        if status_counts.get('maintenance', 0) > 0:
            insights.append(f"{status_counts['maintenance']} machines in maintenance")
    
    return insights


def _generate_inventory_insights(rows: List[Dict]) -> List[str]:
    """Generate inventory specific insights."""
    insights = []
    
    if not rows:
        return ['No inventory data available']
    
    # Check for shortage indicators
    shortage_count = 0
    for row in rows:
        if 'ShortageAmount' in row and row['ShortageAmount'] and float(row['ShortageAmount']) > 0:
            shortage_count += 1
    
    if shortage_count > 0:
        insights.append(f'{shortage_count} items below reorder level - procurement action needed')
    else:
        insights.append('Inventory levels appear adequate')
    
    return insights


def _filter_production_relevant_tables(table_names: List[str]) -> List[str]:
    """Filter table names to show production-relevant ones first."""
    priority_tables = ['WorkOrders', 'QualityControl', 'Machines', 'Inventory', 'Products']
    
    relevant_tables = []
    for table in priority_tables:
        if table in table_names:
            relevant_tables.append(table)
    
    # Add other tables
    for table in table_names:
        if table not in relevant_tables:
            relevant_tables.append(table)
    
    return relevant_tables


def _get_meeting_table_priorities() -> Dict[str, str]:
    """Get table priorities for different meeting types."""
    return {
        'WorkOrders': 'Critical for daily production status',
        'QualityControl': 'Essential for quality review',
        'Machines': 'Important for equipment status',
        'Inventory': 'Key for supply chain status',
        'Products': 'Reference for product specifications'
    }


def _get_quick_start_queries() -> Dict[str, str]:
    """Get quick start queries for common meeting needs."""
    # Use actual dates for example queries (DB-agnostic)
    yesterday = days_ago(1)
    seven_days_ago = days_ago(7)

    return {
        'daily_production': f"SELECT * FROM WorkOrders WHERE ActualStartTime >= '{yesterday}' LIMIT 20",
        'quality_issues': f"SELECT * FROM QualityControl WHERE Result = 'fail' AND Date >= '{seven_days_ago}' LIMIT 10",
        'equipment_status': "SELECT Name, Type, Status, EfficiencyFactor FROM Machines WHERE Status != 'running' LIMIT 15",
        'inventory_alerts': "SELECT Name, Quantity, ReorderLevel FROM Inventory WHERE Quantity < ReorderLevel LIMIT 10"
    }


def _get_meeting_focus_areas(meeting_type: str) -> List[str]:
    """Get focus areas for different meeting types."""
    focus_areas = {
        'daily': [
            'Yesterday\'s production completion',
            'Current quality issues',
            'Equipment status and breakdowns',
            'Immediate inventory needs'
        ],
        'weekly': [
            'Weekly production performance',
            'Quality trends and improvements',
            'Equipment efficiency and maintenance',
            'Inventory planning and procurement'
        ],
        'monthly': [
            'Monthly production targets',
            'Quality performance analysis',
            'Equipment reliability trends',
            'Inventory optimization opportunities'
        ]
    }
    
    return focus_areas.get(meeting_type, focus_areas['daily'])


def _get_context_recommended_queries(meeting_type: str, time_ranges: Dict[str, Any]) -> List[str]:
    """Get recommended queries based on meeting type and time ranges."""
    primary_range = time_ranges['primary']
    start_time = date_range_start(primary_range['start'])
    end_time = date_range_end(primary_range['end'])

    queries = []

    if meeting_type == 'daily':
        # These are display queries - using actual values for easy copy/paste
        queries.extend([
            f"SELECT * FROM WorkOrders WHERE ActualStartTime >= '{start_time}' AND ActualStartTime <= '{end_time}' LIMIT 20",
            f"SELECT * FROM QualityControl WHERE Date >= '{start_time}' AND Date <= '{end_time}' AND Result = 'fail' LIMIT 10"
        ])

    queries.append("SELECT Name, Status, EfficiencyFactor FROM Machines WHERE Status != 'running'")
    queries.append("SELECT Name, Quantity, ReorderLevel FROM Inventory WHERE Quantity < ReorderLevel")

    return queries


def _get_key_metrics_for_meeting(meeting_type: str) -> List[str]:
    """Get key metrics to review for different meeting types."""
    metrics = {
        'daily': [
            'Production completion rates',
            'Quality pass/fail rates',
            'Equipment availability',
            'Critical inventory levels'
        ],
        'weekly': [
            'Weekly production targets vs actual',
            'Quality trend analysis',
            'Equipment efficiency trends',
            'Inventory turnover rates'
        ],
        'monthly': [
            'Monthly production performance',
            'Quality improvement metrics',
            'Equipment reliability statistics',
            'Inventory optimization metrics'
        ]
    }
    
    return metrics.get(meeting_type, metrics['daily'])


def _get_fallback_production_context(meeting_type: str, days_back: int) -> Dict[str, Any]:
    """Get fallback production context when database is unavailable."""
    current_time = datetime.now()
    
    return {
        'meeting_type': meeting_type,
        'fallback_time_ranges': _calculate_meeting_time_ranges(meeting_type, days_back, current_time),
        'manual_checklist': [
            'Review production schedules manually',
            'Check equipment status boards',
            'Verify inventory levels with warehouse',
            'Review quality reports from shift supervisors'
        ],
        'recommended_actions': [
            'Proceed with manual data collection',
            'Focus on critical issues only',
            'Schedule follow-up when database is available'
        ]
    }