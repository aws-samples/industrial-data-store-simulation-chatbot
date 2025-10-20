"""
Visualization Tools for MES Agents.

This module provides Strands SDK tools for intelligent data visualization with
AI-powered chart selection and comprehensive error handling.

Key Tools:
- create_intelligent_visualization: AI-powered chart generation

Features:
- Automatic chart type selection based on data characteristics
- Fallback visualizations when charts fail
- Data structure analysis and validation
- Comprehensive error handling with recovery options
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from strands import tool
from ..error_handling import IntelligentErrorAnalyzer, ErrorContext


@tool
def create_intelligent_visualization(
    data: List[Dict], 
    analysis_intent: str, 
    chart_reasoning: str
) -> Dict[str, Any]:
    """
    Generate appropriate visualizations based on AI analysis of data characteristics.
    
    Args:
        data: List of dictionaries containing the data to visualize
        analysis_intent: Description of what the user wants to analyze
        chart_reasoning: AI reasoning for why this chart type was chosen
        
    Returns:
        Dictionary containing visualization specification and plotly figure
    """
    try:
        if not data:
            return {
                'success': False,
                'error': 'No data provided for visualization',
                'suggestion': 'Ensure your query returns data before attempting visualization'
            }
        
        # Convert to DataFrame for analysis
        df = pd.DataFrame(data)
        
        # Analyze data characteristics
        data_analysis = _analyze_data_characteristics(df)
        
        # Determine best chart type based on data characteristics and intent
        chart_spec = _determine_chart_type(df, data_analysis, analysis_intent)
        
        # Create the visualization
        fig = _create_plotly_visualization(df, chart_spec)
        
        return {
            'success': True,
            'chart_type': chart_spec['type'],
            'reasoning': chart_reasoning,
            'data_analysis': data_analysis,
            'chart_config': chart_spec,
            'plotly_json': fig.to_json(),
            'plotly_html': fig.to_html(include_plotlyjs='cdn'),
            'data_summary': {
                'rows': len(df),
                'columns': list(df.columns),
                'numeric_columns': data_analysis['numeric_columns'],
                'categorical_columns': data_analysis['categorical_columns']
            }
        }
        
    except Exception as e:
        return _handle_visualization_error(e, data, analysis_intent, chart_reasoning)


def _analyze_data_characteristics(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Analyze data characteristics to inform visualization decisions.
    
    Args:
        df: DataFrame to analyze
        
    Returns:
        Dictionary containing data analysis results
    """
    numeric_columns = df.select_dtypes(include=['number']).columns.tolist()
    categorical_columns = df.select_dtypes(include=['object', 'category']).columns.tolist()
    datetime_columns = df.select_dtypes(include=['datetime']).columns.tolist()
    
    # Analyze column cardinality
    column_cardinality = {}
    for col in df.columns:
        unique_count = df[col].nunique()
        total_count = len(df)
        column_cardinality[col] = {
            'unique_count': unique_count,
            'cardinality_ratio': unique_count / total_count if total_count > 0 else 0
        }
    
    return {
        'row_count': len(df),
        'column_count': len(df.columns),
        'numeric_columns': numeric_columns,
        'categorical_columns': categorical_columns,
        'datetime_columns': datetime_columns,
        'column_cardinality': column_cardinality,
        'has_time_series': len(datetime_columns) > 0,
        'is_single_metric': len(numeric_columns) == 1,
        'is_multi_metric': len(numeric_columns) > 1
    }


def _determine_chart_type(df: pd.DataFrame, data_analysis: Dict, analysis_intent: str) -> Dict[str, Any]:
    """
    Determine the most appropriate chart type based on data characteristics.
    
    Args:
        df: DataFrame containing the data
        data_analysis: Results from data characteristic analysis
        analysis_intent: User's analysis intent
        
    Returns:
        Chart specification dictionary
    """
    numeric_cols = data_analysis['numeric_columns']
    categorical_cols = data_analysis['categorical_columns']
    datetime_cols = data_analysis['datetime_columns']
    
    # Time series data
    if datetime_cols and numeric_cols:
        return {
            'type': 'line',
            'x': datetime_cols[0],
            'y': numeric_cols[0],
            'reasoning': 'Time series data detected - line chart shows trends over time'
        }
    
    # Single numeric column with categorical grouping
    if len(numeric_cols) == 1 and len(categorical_cols) >= 1:
        categorical_col = categorical_cols[0]
        unique_categories = df[categorical_col].nunique()
        
        if unique_categories <= 10:
            return {
                'type': 'bar',
                'x': categorical_col,
                'y': numeric_cols[0],
                'reasoning': f'Bar chart effectively compares {numeric_cols[0]} across {unique_categories} categories'
            }
        else:
            return {
                'type': 'histogram',
                'x': numeric_cols[0],
                'reasoning': f'Histogram shows distribution of {numeric_cols[0]} (too many categories for bar chart)'
            }
    
    # Two numeric columns - scatter plot for correlation
    if len(numeric_cols) >= 2:
        return {
            'type': 'scatter',
            'x': numeric_cols[0],
            'y': numeric_cols[1],
            'color': categorical_cols[0] if categorical_cols else None,
            'reasoning': f'Scatter plot reveals relationship between {numeric_cols[0]} and {numeric_cols[1]}'
        }
    
    # Single numeric column - histogram for distribution
    if len(numeric_cols) == 1 and not categorical_cols:
        return {
            'type': 'histogram',
            'x': numeric_cols[0],
            'reasoning': f'Histogram shows distribution of {numeric_cols[0]} values'
        }
    
    # Categorical data only - count plot
    if categorical_cols and not numeric_cols:
        return {
            'type': 'bar',
            'x': categorical_cols[0],
            'y': 'count',
            'reasoning': f'Bar chart shows frequency distribution of {categorical_cols[0]} categories'
        }
    
    # Fallback to table view
    return {
        'type': 'table',
        'reasoning': 'Data structure is complex - table view provides comprehensive overview'
    }


def _create_plotly_visualization(df: pd.DataFrame, chart_spec: Dict[str, Any]) -> go.Figure:
    """
    Create the actual plotly visualization based on chart specification.
    
    Args:
        df: DataFrame containing the data
        chart_spec: Chart specification from _determine_chart_type
        
    Returns:
        Plotly figure object
    """
    chart_type = chart_spec['type']
    
    try:
        if chart_type == 'line':
            fig = px.line(
                df, 
                x=chart_spec['x'], 
                y=chart_spec['y'],
                title=f"{chart_spec['y']} over {chart_spec['x']}"
            )
            
        elif chart_type == 'bar':
            if chart_spec.get('y') == 'count':
                # Count plot
                value_counts = df[chart_spec['x']].value_counts()
                fig = px.bar(
                    x=value_counts.index,
                    y=value_counts.values,
                    title=f"Count of {chart_spec['x']}"
                )
                fig.update_xaxis(title=chart_spec['x'])
                fig.update_yaxis(title='Count')
            else:
                fig = px.bar(
                    df,
                    x=chart_spec['x'],
                    y=chart_spec['y'],
                    title=f"{chart_spec['y']} by {chart_spec['x']}"
                )
                
        elif chart_type == 'scatter':
            fig = px.scatter(
                df,
                x=chart_spec['x'],
                y=chart_spec['y'],
                color=chart_spec.get('color'),
                title=f"{chart_spec['y']} vs {chart_spec['x']}"
            )
            
        elif chart_type == 'histogram':
            fig = px.histogram(
                df,
                x=chart_spec['x'],
                title=f"Distribution of {chart_spec['x']}"
            )
            
        else:  # table or fallback
            fig = go.Figure(data=[go.Table(
                header=dict(values=list(df.columns)),
                cells=dict(values=[df[col] for col in df.columns])
            )])
            fig.update_layout(title="Data Table View")
        
        # Apply consistent styling
        fig.update_layout(
            template="plotly_white",
            showlegend=True,
            height=500,
            margin=dict(l=50, r=50, t=80, b=50)
        )
        
        return fig
        
    except Exception as e:
        # Fallback to simple table if visualization fails
        fig = go.Figure(data=[go.Table(
            header=dict(values=list(df.columns)),
            cells=dict(values=[df[col] for col in df.columns])
        )])
        fig.update_layout(
            title=f"Data Table (Visualization Error: {str(e)})",
            template="plotly_white"
        )
        return fig


def _handle_visualization_error(
    error: Exception, 
    data: List[Dict], 
    analysis_intent: str, 
    chart_reasoning: str
) -> Dict[str, Any]:
    """
    Handle visualization errors with comprehensive analysis and recovery options.
    
    Args:
        error: Exception that occurred
        data: Original data that failed to visualize
        analysis_intent: User's analysis intent
        chart_reasoning: AI reasoning for chart selection
        
    Returns:
        Comprehensive error response with recovery options
    """
    logger = logging.getLogger(__name__)
    error_message = str(error)
    
    # Create error context
    error_context = ErrorContext(
        original_query=f"Visualization request: {analysis_intent}",
        error_message=error_message,
        error_type='visualization_error',
        timestamp=datetime.now(),
        execution_time=0.0,
        partial_results={'data_available': len(data) > 0 if data else False}
    )
    
    # Analyze error
    analyzer = IntelligentErrorAnalyzer()
    analysis = analyzer.analyze_error(error_context)
    
    # Generate visualization-specific suggestions
    viz_suggestions = _get_visualization_suggestions(error_message, data, analysis_intent)
    
    # Generate recovery options
    recovery_options = _generate_visualization_recovery_options(error_message, data)
    
    # Try to create a fallback visualization
    fallback_viz = _create_fallback_visualization(data)
    
    logger.warning(f"Visualization error: {error_message}")
    
    response = {
        'success': False,
        'error': error_message,
        'error_type': 'visualization_error',
        'error_category': analysis.category.value,
        'severity': analysis.severity.value,
        'user_friendly_message': analysis.user_friendly_message,
        'root_cause': analysis.root_cause,
        'original_intent': analysis_intent,
        'chart_reasoning': chart_reasoning,
        'suggestions': viz_suggestions,
        'recovery_options': recovery_options,
        'educational_content': analysis.educational_content,
        'alternative_approaches': analysis.alternative_approaches,
        'data_summary': {
            'data_available': len(data) > 0 if data else False,
            'data_rows': len(data) if data else 0,
            'data_structure': _analyze_data_structure(data) if data else None
        }
    }
    
    # Add fallback visualization if available
    if fallback_viz:
        response['fallback_visualization'] = fallback_viz
        response['fallback_message'] = "Here's a basic table view of your data instead:"
    
    return response


def _get_visualization_suggestions(error_message: str, data: List[Dict], analysis_intent: str) -> List[str]:
    """Generate specific suggestions for visualization errors."""
    suggestions = []
    error_lower = error_message.lower()
    
    if 'empty' in error_lower or 'no data' in error_lower:
        suggestions.extend([
            "The query returned no data to visualize",
            "Check your query filters - they might be too restrictive",
            "Verify the date range or other criteria in your query",
            "Try a broader query to see if data exists"
        ])
    
    elif 'column' in error_lower or 'key' in error_lower:
        suggestions.extend([
            "The data structure doesn't match the expected format for this chart type",
            "Check that your query returns the right column names",
            "Verify that numeric columns contain actual numbers, not text",
            "Ensure date columns are in a recognizable date format"
        ])
    
    elif 'type' in error_lower or 'dtype' in error_lower:
        suggestions.extend([
            "There's a data type mismatch in your visualization data",
            "Numeric charts require numeric data - check for text in number columns",
            "Date charts need properly formatted date values",
            "Consider converting data types in your SQL query using CAST()"
        ])
    
    elif 'plotly' in error_lower:
        suggestions.extend([
            "There's an issue with the chart generation library",
            "The data format may not be compatible with the selected chart type",
            "Try a simpler chart type like a bar chart or table view",
            "Check that all required data columns are present"
        ])
    
    else:
        suggestions.extend([
            "There was an unexpected issue creating the visualization",
            "The data format may not be suitable for the selected chart type",
            "Try viewing the data in table format first",
            "Consider simplifying the data or using a different chart type"
        ])
    
    # Add intent-specific suggestions
    if 'trend' in analysis_intent.lower():
        suggestions.append("For trend analysis, ensure you have date/time data and numeric values")
    elif 'comparison' in analysis_intent.lower():
        suggestions.append("For comparisons, ensure you have categorical data and numeric values to compare")
    elif 'distribution' in analysis_intent.lower():
        suggestions.append("For distributions, ensure you have numeric data to analyze")
    
    return suggestions


def _generate_visualization_recovery_options(error_message: str, data: List[Dict]) -> List[str]:
    """Generate recovery options for visualization errors."""
    recovery_options = []
    
    if data and len(data) > 0:
        recovery_options.extend([
            "View the data in table format to understand its structure",
            "Try a simple bar chart with the first numeric column",
            "Create a basic scatter plot if you have two numeric columns",
            "Use a histogram to see the distribution of a single numeric column"
        ])
    else:
        recovery_options.extend([
            "Check that your query returns data before attempting visualization",
            "Modify your query to return some sample data",
            "Verify your query syntax and table/column names"
        ])
    
    recovery_options.extend([
        "Start with a simple table view to examine the data structure",
        "Try the visualization again with a different chart type",
        "Simplify your data by selecting fewer columns"
    ])
    
    return recovery_options


def _create_fallback_visualization(data: List[Dict]) -> Optional[Dict[str, Any]]:
    """Create a fallback table visualization when charts fail."""
    if not data or len(data) == 0:
        return None
    
    try:
        df = pd.DataFrame(data)
        
        # Create a simple table visualization
        fig = go.Figure(data=[go.Table(
            header=dict(
                values=list(df.columns),
                fill_color='lightblue',
                align='left',
                font=dict(size=12, color='black')
            ),
            cells=dict(
                values=[df[col] for col in df.columns],
                fill_color='white',
                align='left',
                font=dict(size=11, color='black')
            )
        )])
        
        fig.update_layout(
            title="Data Table View (Fallback Visualization)",
            template="plotly_white",
            height=400
        )
        
        return {
            'chart_type': 'table',
            'reasoning': 'Fallback table view when chart generation fails',
            'plotly_json': fig.to_json(),
            'plotly_html': fig.to_html(include_plotlyjs='cdn'),
            'data_summary': {
                'rows': len(df),
                'columns': list(df.columns)
            }
        }
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to create fallback visualization: {e}")
        return None


def _analyze_data_structure(data: List[Dict]) -> Dict[str, Any]:
    """Analyze the structure of data for error reporting."""
    if not data:
        return {'empty': True}
    
    try:
        df = pd.DataFrame(data)
        
        return {
            'empty': False,
            'rows': len(df),
            'columns': list(df.columns),
            'column_types': {col: str(df[col].dtype) for col in df.columns},
            'numeric_columns': df.select_dtypes(include=['number']).columns.tolist(),
            'text_columns': df.select_dtypes(include=['object']).columns.tolist(),
            'has_nulls': df.isnull().any().any(),
            'sample_row': data[0] if data else None
        }
        
    except Exception as e:
        return {
            'analysis_error': str(e),
            'raw_data_sample': data[0] if data else None
        }