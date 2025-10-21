"""
Visualization Tools for Production Meeting Agents.

This module provides Strands SDK tools for intelligent data visualization
specifically designed for production meeting contexts. It includes enhanced
chart capabilities, Streamlit default color integration, and meeting-focused
visualization recommendations.

Key Tools:
- create_intelligent_visualization: AI-powered chart generation with Streamlit colors
- suggest_chart_improvements: Recommendations for better chart types and formatting
- create_meeting_dashboard: Meeting-focused dashboard visualizations

Features:
- Streamlit default color palette integration
- Production meeting specific chart recommendations
- Enhanced error handling for manufacturing data
- Meeting efficiency optimized visualizations
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from strands import tool
from ..error_handling import IntelligentErrorAnalyzer, ErrorContext


# Streamlit default color palette for consistency
STREAMLIT_COLORS = [
    '#FF6B6B',  # Red
    '#4ECDC4',  # Teal
    '#45B7D1',  # Blue
    '#96CEB4',  # Green
    '#FFEAA7',  # Yellow
    '#DDA0DD',  # Plum
    '#98D8C8',  # Mint
    '#F7DC6F',  # Light Yellow
    '#BB8FCE',  # Light Purple
    '#85C1E9'   # Light Blue
]

# Production meeting color themes
PRODUCTION_THEMES = {
    'status': {
        'running': '#2ECC71',      # Green
        'idle': '#F39C12',         # Orange
        'maintenance': '#3498DB',  # Blue
        'breakdown': '#E74C3C',    # Red
        'offline': '#95A5A6'       # Gray
    },
    'quality': {
        'pass': '#27AE60',         # Dark Green
        'fail': '#C0392B',         # Dark Red
        'rework': '#F39C12',       # Orange
        'pending': '#F1C40F'       # Yellow
    },
    'priority': {
        'critical': '#E74C3C',     # Red
        'high': '#F39C12',         # Orange
        'medium': '#F1C40F',       # Yellow
        'low': '#2ECC71'           # Green
    }
}


@tool
def create_intelligent_visualization(
    data: List[Dict], 
    analysis_intent: str, 
    chart_reasoning: str,
    meeting_context: str = 'daily'
) -> Dict[str, Any]:
    """
    Generate appropriate visualizations for production meetings using Streamlit colors.
    
    This tool creates visualizations optimized for production meeting contexts,
    using Streamlit's default color palette for consistency with the dashboard theme.
    
    Args:
        data: List of dictionaries containing the data to visualize
        analysis_intent: Description of what the user wants to analyze
        chart_reasoning: AI reasoning for why this chart type was chosen
        meeting_context: Meeting context ('daily', 'weekly', 'monthly')
        
    Returns:
        Dictionary containing visualization specification and plotly figure
    """
    try:
        if not data:
            return {
                'success': False,
                'error': 'No data provided for visualization',
                'suggestion': 'Ensure your query returns data before attempting visualization',
                'meeting_guidance': 'Consider using get_production_context() to get meeting-ready data'
            }
        
        # Convert to DataFrame for analysis
        df = pd.DataFrame(data)
        
        # Analyze data characteristics with production meeting focus
        data_analysis = _analyze_production_data_characteristics(df)
        
        # Determine best chart type for production meetings
        chart_spec = _determine_production_chart_type(df, data_analysis, analysis_intent, meeting_context)
        
        # Create the visualization with Streamlit colors
        fig = _create_production_plotly_visualization(df, chart_spec, meeting_context)
        
        # Generate meeting-specific insights
        meeting_insights = _generate_visualization_meeting_insights(df, chart_spec, meeting_context)
        
        return {
            'success': True,
            'chart_type': chart_spec['type'],
            'reasoning': chart_reasoning,
            'data_analysis': data_analysis,
            'chart_config': chart_spec,
            'meeting_context': meeting_context,
            'meeting_insights': meeting_insights,
            'plotly_json': fig.to_json(),
            'plotly_html': fig.to_html(include_plotlyjs='cdn'),
            'streamlit_colors_used': True,
            'data_summary': {
                'rows': len(df),
                'columns': list(df.columns),
                'numeric_columns': data_analysis['numeric_columns'],
                'categorical_columns': data_analysis['categorical_columns'],
                'production_relevance': data_analysis['production_relevance']
            },
            'presentation_tips': _get_meeting_presentation_tips(chart_spec, meeting_context)
        }
        
    except Exception as e:
        return _handle_production_visualization_error(e, data, analysis_intent, chart_reasoning, meeting_context)


@tool
def suggest_chart_improvements(
    current_chart_type: str, 
    data_characteristics: Dict[str, Any],
    meeting_focus: str = 'efficiency'
) -> Dict[str, Any]:
    """
    Suggest better chart types and formatting for production meeting data.
    
    This tool analyzes current visualization choices and suggests improvements
    specifically for production meeting contexts and efficiency.
    
    Args:
        current_chart_type: Current chart type being used
        data_characteristics: Characteristics of the data being visualized
        meeting_focus: Meeting focus area ('efficiency', 'quality', 'maintenance', 'inventory')
        
    Returns:
        Dictionary containing improvement suggestions and alternative chart types
    """
    try:
        improvements = {
            'success': True,
            'current_chart': current_chart_type,
            'meeting_focus': meeting_focus,
            'suggestions': [],
            'alternative_charts': [],
            'formatting_improvements': [],
            'color_recommendations': [],
            'meeting_optimization': []
        }
        
        # Analyze current chart effectiveness
        effectiveness_analysis = _analyze_chart_effectiveness(current_chart_type, data_characteristics, meeting_focus)
        improvements['effectiveness_score'] = effectiveness_analysis['score']
        improvements['effectiveness_reasoning'] = effectiveness_analysis['reasoning']
        
        # Generate chart type suggestions
        chart_suggestions = _generate_chart_type_suggestions(current_chart_type, data_characteristics, meeting_focus)
        improvements['alternative_charts'] = chart_suggestions
        
        # Generate formatting improvements
        formatting_suggestions = _generate_formatting_improvements(current_chart_type, data_characteristics, meeting_focus)
        improvements['formatting_improvements'] = formatting_suggestions
        
        # Generate color recommendations
        color_recommendations = _generate_color_recommendations(current_chart_type, data_characteristics, meeting_focus)
        improvements['color_recommendations'] = color_recommendations
        
        # Generate meeting-specific optimizations
        meeting_optimizations = _generate_meeting_optimizations(current_chart_type, data_characteristics, meeting_focus)
        improvements['meeting_optimization'] = meeting_optimizations
        
        # Overall recommendation
        improvements['overall_recommendation'] = _generate_overall_recommendation(
            current_chart_type, data_characteristics, meeting_focus, effectiveness_analysis
        )
        
        return improvements
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'error_type': 'chart_improvement_error',
            'fallback_suggestions': [
                'Use Streamlit default colors for consistency',
                'Keep charts simple for meeting efficiency',
                'Focus on key metrics only',
                'Ensure charts are readable in both light and dark themes'
            ]
        }


@tool
def create_meeting_dashboard(
    data_sections: Dict[str, List[Dict]], 
    focus_areas: List[str],
    meeting_type: str = 'daily'
) -> Dict[str, Any]:
    """
    Create meeting-focused dashboard visualizations for production data.
    
    This tool creates a comprehensive dashboard layout optimized for production
    meetings, with multiple coordinated visualizations using consistent theming.
    
    Args:
        data_sections: Dictionary with section names as keys and data lists as values
        focus_areas: List of focus areas for the meeting ('production', 'quality', 'equipment', 'inventory')
        meeting_type: Type of meeting ('daily', 'weekly', 'monthly')
        
    Returns:
        Dictionary containing dashboard specification and multiple visualizations
    """
    try:
        dashboard = {
            'success': True,
            'meeting_type': meeting_type,
            'focus_areas': focus_areas,
            'sections': {},
            'layout_recommendations': [],
            'meeting_insights': [],
            'color_theme': 'streamlit_default'
        }
        
        # Process each data section
        for section_name, section_data in data_sections.items():
            if not section_data:
                dashboard['sections'][section_name] = {
                    'status': 'no_data',
                    'message': f'No data available for {section_name}',
                    'placeholder_chart': _create_placeholder_chart(section_name)
                }
                continue
            
            # Create section-specific visualization
            section_viz = _create_dashboard_section_visualization(
                section_data, section_name, meeting_type, focus_areas
            )
            dashboard['sections'][section_name] = section_viz
        
        # Generate layout recommendations
        dashboard['layout_recommendations'] = _generate_dashboard_layout_recommendations(
            data_sections, focus_areas, meeting_type
        )
        
        # Generate meeting insights across all sections
        dashboard['meeting_insights'] = _generate_dashboard_meeting_insights(
            data_sections, focus_areas, meeting_type
        )
        
        # Add navigation and interaction recommendations
        dashboard['interaction_recommendations'] = _generate_dashboard_interaction_recommendations(
            data_sections, meeting_type
        )
        
        return dashboard
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'error_type': 'dashboard_creation_error',
            'fallback_dashboard': _create_fallback_dashboard(data_sections, focus_areas, meeting_type)
        }


def _analyze_production_data_characteristics(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Analyze data characteristics with production meeting focus.
    
    Args:
        df: DataFrame to analyze
        
    Returns:
        Dictionary containing production-focused data analysis results
    """
    numeric_columns = df.select_dtypes(include=['number']).columns.tolist()
    categorical_columns = df.select_dtypes(include=['object', 'category']).columns.tolist()
    datetime_columns = df.select_dtypes(include=['datetime']).columns.tolist()
    
    # Analyze production relevance of columns
    production_relevance = _assess_production_column_relevance(df.columns.tolist())
    
    # Analyze data patterns for production metrics
    production_patterns = _identify_production_data_patterns(df, numeric_columns, categorical_columns)
    
    return {
        'row_count': len(df),
        'column_count': len(df.columns),
        'numeric_columns': numeric_columns,
        'categorical_columns': categorical_columns,
        'datetime_columns': datetime_columns,
        'production_relevance': production_relevance,
        'production_patterns': production_patterns,
        'has_time_series': len(datetime_columns) > 0,
        'has_status_data': _has_status_columns(df.columns.tolist()),
        'has_performance_metrics': _has_performance_metrics(numeric_columns),
        'meeting_suitability': _assess_meeting_suitability(df, numeric_columns, categorical_columns)
    }


def _determine_production_chart_type(
    df: pd.DataFrame, 
    data_analysis: Dict, 
    analysis_intent: str, 
    meeting_context: str
) -> Dict[str, Any]:
    """
    Determine the most appropriate chart type for production meeting data.
    
    Args:
        df: DataFrame containing the data
        data_analysis: Results from production data analysis
        analysis_intent: User's analysis intent
        meeting_context: Meeting context ('daily', 'weekly', 'monthly')
        
    Returns:
        Chart specification dictionary optimized for production meetings
    """
    numeric_cols = data_analysis['numeric_columns']
    categorical_cols = data_analysis['categorical_columns']
    datetime_cols = data_analysis['datetime_columns']
    production_patterns = data_analysis['production_patterns']
    
    # Production-specific chart selection logic
    
    # Status/Equipment data - use status-appropriate colors
    if production_patterns.get('has_status_data'):
        status_col = production_patterns['status_column']
        if numeric_cols:
            return {
                'type': 'bar',
                'x': status_col,
                'y': numeric_cols[0],
                'color_theme': 'status',
                'reasoning': f'Bar chart with status colors shows {numeric_cols[0]} by equipment/process status'
            }
    
    # Quality data - use quality-appropriate colors
    if production_patterns.get('has_quality_data'):
        quality_col = production_patterns['quality_column']
        if numeric_cols:
            return {
                'type': 'bar',
                'x': quality_col,
                'y': numeric_cols[0],
                'color_theme': 'quality',
                'reasoning': f'Bar chart with quality colors shows {numeric_cols[0]} by quality results'
            }
    
    # Time series production data
    if datetime_cols and numeric_cols:
        return {
            'type': 'line',
            'x': datetime_cols[0],
            'y': numeric_cols[0],
            'color_theme': 'streamlit',
            'reasoning': f'Line chart shows {numeric_cols[0]} trends over time for {meeting_context} meeting analysis'
        }
    
    # Performance comparison data
    if len(numeric_cols) >= 2 and categorical_cols:
        return {
            'type': 'grouped_bar',
            'x': categorical_cols[0],
            'y': numeric_cols[:2],
            'color_theme': 'streamlit',
            'reasoning': f'Grouped bar chart compares {numeric_cols[0]} and {numeric_cols[1]} across {categorical_cols[0]}'
        }
    
    # Single metric by category - common in production meetings
    if len(numeric_cols) == 1 and len(categorical_cols) >= 1:
        categorical_col = categorical_cols[0]
        unique_categories = df[categorical_col].nunique()
        
        if unique_categories <= 15:  # Good for meeting display
            return {
                'type': 'bar',
                'x': categorical_col,
                'y': numeric_cols[0],
                'color_theme': 'streamlit',
                'reasoning': f'Bar chart effectively shows {numeric_cols[0]} across {unique_categories} categories for meeting review'
            }
        else:
            return {
                'type': 'histogram',
                'x': numeric_cols[0],
                'color_theme': 'streamlit',
                'reasoning': f'Histogram shows distribution of {numeric_cols[0]} (too many categories for effective meeting display)'
            }
    
    # Correlation analysis for process optimization
    if len(numeric_cols) >= 2:
        return {
            'type': 'scatter',
            'x': numeric_cols[0],
            'y': numeric_cols[1],
            'color': categorical_cols[0] if categorical_cols else None,
            'color_theme': 'streamlit',
            'reasoning': f'Scatter plot reveals relationship between {numeric_cols[0]} and {numeric_cols[1]} for process optimization'
        }
    
    # Distribution analysis
    if len(numeric_cols) == 1 and not categorical_cols:
        return {
            'type': 'histogram',
            'x': numeric_cols[0],
            'color_theme': 'streamlit',
            'reasoning': f'Histogram shows distribution of {numeric_cols[0]} values for process analysis'
        }
    
    # Categorical frequency analysis
    if categorical_cols and not numeric_cols:
        return {
            'type': 'bar',
            'x': categorical_cols[0],
            'y': 'count',
            'color_theme': 'streamlit',
            'reasoning': f'Bar chart shows frequency distribution of {categorical_cols[0]} for meeting analysis'
        }
    
    # Fallback to table for complex data
    return {
        'type': 'table',
        'color_theme': 'streamlit',
        'reasoning': 'Table view provides comprehensive data overview for detailed meeting discussion'
    }


def _create_production_plotly_visualization(
    df: pd.DataFrame, 
    chart_spec: Dict[str, Any], 
    meeting_context: str
) -> go.Figure:
    """
    Create plotly visualization optimized for production meetings with Streamlit colors.
    
    Args:
        df: DataFrame containing the data
        chart_spec: Chart specification from _determine_production_chart_type
        meeting_context: Meeting context for optimization
        
    Returns:
        Plotly figure object with production meeting optimizations
    """
    chart_type = chart_spec['type']
    color_theme = chart_spec.get('color_theme', 'streamlit')
    
    try:
        if chart_type == 'line':
            fig = px.line(
                df, 
                x=chart_spec['x'], 
                y=chart_spec['y'],
                title=f"{chart_spec['y']} Trend - {meeting_context.title()} Meeting",
                color_discrete_sequence=STREAMLIT_COLORS
            )
            
        elif chart_type == 'bar':
            if chart_spec.get('y') == 'count':
                # Count plot with Streamlit colors
                value_counts = df[chart_spec['x']].value_counts()
                fig = px.bar(
                    x=value_counts.index,
                    y=value_counts.values,
                    title=f"{chart_spec['x']} Distribution - {meeting_context.title()} Meeting",
                    color_discrete_sequence=STREAMLIT_COLORS
                )
                fig.update_xaxis(title=chart_spec['x'])
                fig.update_yaxis(title='Count')
            else:
                # Regular bar chart with appropriate colors
                colors = _get_color_sequence(color_theme, df[chart_spec['x']].unique() if 'x' in chart_spec else None)
                fig = px.bar(
                    df,
                    x=chart_spec['x'],
                    y=chart_spec['y'],
                    title=f"{chart_spec['y']} by {chart_spec['x']} - {meeting_context.title()} Meeting",
                    color=chart_spec['x'] if color_theme != 'streamlit' else None,
                    color_discrete_map=colors if color_theme != 'streamlit' else None,
                    color_discrete_sequence=STREAMLIT_COLORS if color_theme == 'streamlit' else None
                )
                
        elif chart_type == 'grouped_bar':
            # Create grouped bar chart for multiple metrics
            fig = go.Figure()
            colors = STREAMLIT_COLORS
            
            for i, y_col in enumerate(chart_spec['y']):
                fig.add_trace(go.Bar(
                    name=y_col,
                    x=df[chart_spec['x']],
                    y=df[y_col],
                    marker_color=colors[i % len(colors)]
                ))
            
            fig.update_layout(
                title=f"Performance Comparison - {meeting_context.title()} Meeting",
                barmode='group'
            )
            
        elif chart_type == 'scatter':
            fig = px.scatter(
                df,
                x=chart_spec['x'],
                y=chart_spec['y'],
                color=chart_spec.get('color'),
                title=f"{chart_spec['y']} vs {chart_spec['x']} Analysis - {meeting_context.title()} Meeting",
                color_discrete_sequence=STREAMLIT_COLORS
            )
            
        elif chart_type == 'histogram':
            fig = px.histogram(
                df,
                x=chart_spec['x'],
                title=f"{chart_spec['x']} Distribution - {meeting_context.title()} Meeting",
                color_discrete_sequence=STREAMLIT_COLORS
            )
            
        else:  # table or fallback
            fig = go.Figure(data=[go.Table(
                header=dict(
                    values=list(df.columns),
                    fill_color=STREAMLIT_COLORS[0],
                    align='left',
                    font=dict(size=12, color='white')
                ),
                cells=dict(
                    values=[df[col] for col in df.columns],
                    fill_color='white',
                    align='left',
                    font=dict(size=11, color='black')
                )
            )])
            fig.update_layout(title=f"Data Overview - {meeting_context.title()} Meeting")
        
        # Apply production meeting optimizations
        fig = _apply_production_meeting_styling(fig, meeting_context)
        
        return fig
        
    except Exception as e:
        # Fallback to simple table with error message
        fig = go.Figure(data=[go.Table(
            header=dict(
                values=list(df.columns),
                fill_color=STREAMLIT_COLORS[0],
                align='left'
            ),
            cells=dict(
                values=[df[col] for col in df.columns],
                fill_color='white',
                align='left'
            )
        )])
        fig.update_layout(
            title=f"Data Table - {meeting_context.title()} Meeting (Chart Error: {str(e)})",
            template="plotly_white"
        )
        return fig


def _apply_production_meeting_styling(fig: go.Figure, meeting_context: str) -> go.Figure:
    """
    Apply production meeting specific styling to plotly figures.
    
    Args:
        fig: Plotly figure to style
        meeting_context: Meeting context for styling decisions
        
    Returns:
        Styled plotly figure optimized for production meetings
    """
    # Base styling for all production meeting charts
    fig.update_layout(
        template="plotly_white",
        showlegend=True,
        height=450,  # Optimized for meeting displays
        margin=dict(l=60, r=60, t=80, b=60),
        font=dict(size=12),  # Readable in meeting rooms
        title_font=dict(size=16, color='#2C3E50'),  # Professional title styling
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    # Meeting-specific optimizations
    if meeting_context == 'daily':
        # Daily meetings need quick, clear visuals
        fig.update_layout(
            title_font=dict(size=14),
            height=400
        )
    elif meeting_context == 'weekly':
        # Weekly meetings can handle more detail
        fig.update_layout(
            height=500
        )
    elif meeting_context == 'monthly':
        # Monthly meetings need comprehensive views
        fig.update_layout(
            height=550,
            margin=dict(l=80, r=80, t=100, b=80)
        )
    
    return fig


def _get_color_sequence(color_theme: str, categories: Optional[List] = None) -> Dict[str, str]:
    """
    Get appropriate color sequence based on theme and categories.
    
    Args:
        color_theme: Color theme to use ('streamlit', 'status', 'quality', 'priority')
        categories: List of categories to map colors to
        
    Returns:
        Dictionary mapping categories to colors
    """
    if color_theme == 'streamlit' or not categories:
        return {}
    
    if color_theme in PRODUCTION_THEMES:
        theme_colors = PRODUCTION_THEMES[color_theme]
        color_map = {}
        
        for i, category in enumerate(categories):
            category_lower = str(category).lower()
            
            # Try to match category to theme-specific colors
            if category_lower in theme_colors:
                color_map[category] = theme_colors[category_lower]
            else:
                # Fallback to Streamlit colors
                color_map[category] = STREAMLIT_COLORS[i % len(STREAMLIT_COLORS)]
        
        return color_map
    
    # Default to Streamlit colors
    return {}


# Helper functions for data analysis
def _assess_production_column_relevance(columns: List[str]) -> Dict[str, str]:
    """Assess how relevant columns are to production meetings."""
    relevance_map = {}
    
    for col in columns:
        col_lower = col.lower()
        
        if any(keyword in col_lower for keyword in ['production', 'quantity', 'output', 'volume']):
            relevance_map[col] = 'high'
        elif any(keyword in col_lower for keyword in ['quality', 'defect', 'yield', 'scrap']):
            relevance_map[col] = 'high'
        elif any(keyword in col_lower for keyword in ['efficiency', 'oee', 'downtime', 'availability']):
            relevance_map[col] = 'high'
        elif any(keyword in col_lower for keyword in ['status', 'state', 'condition']):
            relevance_map[col] = 'medium'
        elif any(keyword in col_lower for keyword in ['time', 'date', 'duration']):
            relevance_map[col] = 'medium'
        else:
            relevance_map[col] = 'low'
    
    return relevance_map


def _identify_production_data_patterns(df: pd.DataFrame, numeric_cols: List[str], categorical_cols: List[str]) -> Dict[str, Any]:
    """Identify production-specific data patterns."""
    patterns = {}
    
    # Check for status/state columns
    for col in categorical_cols:
        col_values = df[col].unique()
        col_values_lower = [str(val).lower() for val in col_values]
        
        if any(status in col_values_lower for status in ['running', 'idle', 'maintenance', 'breakdown']):
            patterns['has_status_data'] = True
            patterns['status_column'] = col
            break
    
    # Check for quality result columns
    for col in categorical_cols:
        col_values = df[col].unique()
        col_values_lower = [str(val).lower() for val in col_values]
        
        if any(result in col_values_lower for result in ['pass', 'fail', 'rework', 'pending']):
            patterns['has_quality_data'] = True
            patterns['quality_column'] = col
            break
    
    # Check for performance metrics
    performance_indicators = ['efficiency', 'oee', 'yield', 'throughput', 'utilization']
    for col in numeric_cols:
        if any(indicator in col.lower() for indicator in performance_indicators):
            patterns['has_performance_metrics'] = True
            patterns['performance_columns'] = patterns.get('performance_columns', []) + [col]
    
    return patterns


def _has_status_columns(columns: List[str]) -> bool:
    """Check if data has status-related columns."""
    status_keywords = ['status', 'state', 'condition', 'mode']
    return any(keyword in col.lower() for col in columns for keyword in status_keywords)


def _has_performance_metrics(numeric_columns: List[str]) -> bool:
    """Check if data has performance metric columns."""
    performance_keywords = ['efficiency', 'oee', 'yield', 'throughput', 'utilization', 'rate']
    return any(keyword in col.lower() for col in numeric_columns for keyword in performance_keywords)


def _assess_meeting_suitability(df: pd.DataFrame, numeric_cols: List[str], categorical_cols: List[str]) -> Dict[str, Any]:
    """Assess how suitable the data is for meeting presentation."""
    suitability = {
        'overall_score': 0,
        'factors': {}
    }
    
    # Data size factor
    row_count = len(df)
    if row_count <= 20:
        suitability['factors']['data_size'] = {'score': 10, 'reason': 'Perfect size for meeting review'}
    elif row_count <= 100:
        suitability['factors']['data_size'] = {'score': 8, 'reason': 'Good size for meeting summary'}
    else:
        suitability['factors']['data_size'] = {'score': 5, 'reason': 'Large dataset - needs summarization'}
    
    # Column complexity factor
    total_cols = len(df.columns)
    if total_cols <= 5:
        suitability['factors']['complexity'] = {'score': 10, 'reason': 'Simple structure, easy to understand'}
    elif total_cols <= 10:
        suitability['factors']['complexity'] = {'score': 7, 'reason': 'Moderate complexity'}
    else:
        suitability['factors']['complexity'] = {'score': 4, 'reason': 'Complex structure - focus on key columns'}
    
    # Production relevance factor
    production_cols = sum(1 for col in df.columns if any(keyword in col.lower() 
                         for keyword in ['production', 'quality', 'efficiency', 'status']))
    if production_cols >= 2:
        suitability['factors']['relevance'] = {'score': 10, 'reason': 'Highly relevant to production meetings'}
    elif production_cols >= 1:
        suitability['factors']['relevance'] = {'score': 7, 'reason': 'Moderately relevant to production'}
    else:
        suitability['factors']['relevance'] = {'score': 3, 'reason': 'Limited production relevance'}
    
    # Calculate overall score
    scores = [factor['score'] for factor in suitability['factors'].values()]
    suitability['overall_score'] = sum(scores) / len(scores) if scores else 0
    
    return suitability


def _generate_visualization_meeting_insights(df: pd.DataFrame, chart_spec: Dict[str, Any], meeting_context: str) -> List[str]:
    """Generate meeting-specific insights from visualization data."""
    insights = []
    
    row_count = len(df)
    chart_type = chart_spec['type']
    
    # General data insights
    if row_count == 0:
        insights.append('No data available - investigate data collection or query parameters')
    elif row_count <= 10:
        insights.append(f'Small dataset ({row_count} records) - suitable for detailed meeting review')
    elif row_count <= 50:
        insights.append(f'Moderate dataset ({row_count} records) - good for meeting analysis')
    else:
        insights.append(f'Large dataset ({row_count} records) - focus on key trends and outliers')
    
    # Chart-specific insights
    if chart_type == 'bar' and 'y' in chart_spec:
        y_col = chart_spec['y']
        if y_col in df.columns and df[y_col].dtype in ['int64', 'float64']:
            max_val = df[y_col].max()
            min_val = df[y_col].min()
            insights.append(f'{y_col} ranges from {min_val} to {max_val} - review outliers and patterns')
    
    # Meeting context insights
    if meeting_context == 'daily':
        insights.append('Focus on immediate actions and today\'s priorities')
    elif meeting_context == 'weekly':
        insights.append('Look for weekly trends and patterns requiring attention')
    elif meeting_context == 'monthly':
        insights.append('Analyze long-term trends and strategic improvements')
    
    return insights


def _get_meeting_presentation_tips(chart_spec: Dict[str, Any], meeting_context: str) -> List[str]:
    """Get presentation tips for meeting context."""
    tips = []
    chart_type = chart_spec['type']
    
    # Chart-specific tips
    if chart_type == 'line':
        tips.extend([
            'Point out key trend changes and inflection points',
            'Highlight any unusual spikes or dips',
            'Compare current performance to targets or previous periods'
        ])
    elif chart_type == 'bar':
        tips.extend([
            'Start with the highest/lowest values',
            'Identify items requiring immediate attention',
            'Compare performance across categories'
        ])
    elif chart_type == 'scatter':
        tips.extend([
            'Look for correlation patterns and outliers',
            'Identify data points that need investigation',
            'Discuss process optimization opportunities'
        ])
    
    # Meeting context tips
    if meeting_context == 'daily':
        tips.extend([
            'Keep discussion focused on actionable items',
            'Prioritize issues that can be resolved today',
            'Note items for follow-up in future meetings'
        ])
    elif meeting_context == 'weekly':
        tips.extend([
            'Review weekly targets and achievements',
            'Identify trends that need strategic attention',
            'Plan actions for the upcoming week'
        ])
    
    return tips


# Chart improvement and suggestion functions
def _analyze_chart_effectiveness(current_chart_type: str, data_characteristics: Dict[str, Any], meeting_focus: str) -> Dict[str, Any]:
    """Analyze the effectiveness of current chart type for meeting context."""
    effectiveness = {'score': 5, 'reasoning': ''}
    
    # Base effectiveness by chart type
    chart_effectiveness = {
        'bar': 8,      # Great for comparisons
        'line': 9,     # Excellent for trends
        'scatter': 6,  # Good for correlations
        'histogram': 5, # Moderate for distributions
        'pie': 4,      # Limited use in production
        'table': 7     # Always useful for details
    }
    
    base_score = chart_effectiveness.get(current_chart_type, 5)
    
    # Adjust based on data characteristics
    if data_characteristics.get('has_time_series') and current_chart_type == 'line':
        base_score += 2
        effectiveness['reasoning'] = 'Line chart is excellent for time series data'
    elif data_characteristics.get('has_categorical_data') and current_chart_type == 'bar':
        base_score += 1
        effectiveness['reasoning'] = 'Bar chart works well for categorical comparisons'
    
    # Adjust based on meeting focus
    focus_adjustments = {
        'efficiency': {'line': 2, 'bar': 1},
        'quality': {'bar': 2, 'histogram': 1},
        'maintenance': {'bar': 1, 'scatter': 1},
        'inventory': {'bar': 2, 'line': 1}
    }
    
    if meeting_focus in focus_adjustments and current_chart_type in focus_adjustments[meeting_focus]:
        base_score += focus_adjustments[meeting_focus][current_chart_type]
    
    effectiveness['score'] = min(10, max(1, base_score))
    
    if not effectiveness['reasoning']:
        effectiveness['reasoning'] = f'{current_chart_type.title()} chart is moderately effective for this data and meeting focus'
    
    return effectiveness


def _generate_chart_type_suggestions(current_chart_type: str, data_characteristics: Dict[str, Any], meeting_focus: str) -> List[Dict[str, Any]]:
    """Generate alternative chart type suggestions."""
    suggestions = []
    
    # Time series data suggestions
    if data_characteristics.get('has_time_series'):
        if current_chart_type != 'line':
            suggestions.append({
                'chart_type': 'line',
                'reason': 'Line chart better shows trends over time',
                'meeting_benefit': 'Easier to spot performance trends and patterns'
            })
    
    # Categorical comparison suggestions
    if data_characteristics.get('has_categorical_data'):
        if current_chart_type != 'bar':
            suggestions.append({
                'chart_type': 'bar',
                'reason': 'Bar chart better compares values across categories',
                'meeting_benefit': 'Clear visual comparison for decision making'
            })
    
    # Multiple metrics suggestions
    if data_characteristics.get('multiple_numeric_columns'):
        if current_chart_type not in ['grouped_bar', 'scatter']:
            suggestions.append({
                'chart_type': 'grouped_bar',
                'reason': 'Grouped bar chart can show multiple metrics together',
                'meeting_benefit': 'Compare multiple KPIs simultaneously'
            })
    
    # Meeting focus specific suggestions
    if meeting_focus == 'quality' and current_chart_type != 'histogram':
        suggestions.append({
            'chart_type': 'histogram',
            'reason': 'Histogram shows quality distribution patterns',
            'meeting_benefit': 'Identify quality issues and process variations'
        })
    
    return suggestions


def _generate_formatting_improvements(current_chart_type: str, data_characteristics: Dict[str, Any], meeting_focus: str) -> List[str]:
    """Generate formatting improvement suggestions."""
    improvements = []
    
    # General formatting improvements
    improvements.extend([
        'Use Streamlit default colors for consistency with dashboard theme',
        'Ensure chart titles clearly describe the data and time period',
        'Add axis labels with units where appropriate',
        'Use consistent font sizes readable in meeting rooms'
    ])
    
    # Chart-specific improvements
    if current_chart_type == 'bar':
        improvements.extend([
            'Sort bars by value for easier comparison',
            'Add data labels on bars for precise values',
            'Use horizontal bars if category names are long'
        ])
    elif current_chart_type == 'line':
        improvements.extend([
            'Add markers to highlight data points',
            'Include reference lines for targets or thresholds',
            'Use different line styles for multiple series'
        ])
    elif current_chart_type == 'scatter':
        improvements.extend([
            'Use different colors/shapes for different categories',
            'Add trend lines to show correlations',
            'Include tooltips with detailed information'
        ])
    
    # Meeting focus improvements
    if meeting_focus == 'efficiency':
        improvements.append('Highlight performance against targets or benchmarks')
    elif meeting_focus == 'quality':
        improvements.append('Use red/green colors to highlight pass/fail status')
    elif meeting_focus == 'maintenance':
        improvements.append('Use color coding to show urgency levels')
    
    return improvements


def _generate_color_recommendations(current_chart_type: str, data_characteristics: Dict[str, Any], meeting_focus: str) -> List[str]:
    """Generate color scheme recommendations."""
    recommendations = []
    
    # Base color recommendations
    recommendations.extend([
        'Use Streamlit default color palette for consistency',
        'Ensure colors work in both light and dark themes',
        'Use high contrast colors for accessibility'
    ])
    
    # Context-specific color recommendations
    if meeting_focus == 'quality':
        recommendations.extend([
            'Use green for pass/good quality results',
            'Use red for fail/poor quality results',
            'Use orange for rework/marginal results'
        ])
    elif meeting_focus == 'efficiency':
        recommendations.extend([
            'Use green for high efficiency/performance',
            'Use red for low efficiency/problems',
            'Use gradient colors to show performance ranges'
        ])
    elif meeting_focus == 'maintenance':
        recommendations.extend([
            'Use red for critical/overdue maintenance',
            'Use orange for upcoming maintenance',
            'Use green for recently completed maintenance'
        ])
    
    # Chart-specific color recommendations
    if current_chart_type == 'line':
        recommendations.append('Use distinct colors for multiple trend lines')
    elif current_chart_type == 'bar':
        recommendations.append('Consider using single color for simple comparisons')
    
    return recommendations


def _generate_meeting_optimizations(current_chart_type: str, data_characteristics: Dict[str, Any], meeting_focus: str) -> List[str]:
    """Generate meeting-specific optimization suggestions."""
    optimizations = []
    
    # General meeting optimizations
    optimizations.extend([
        'Optimize chart size for meeting room displays',
        'Use clear, large fonts readable from distance',
        'Minimize chart complexity for quick understanding',
        'Focus on actionable insights rather than raw data'
    ])
    
    # Data size optimizations
    row_count = data_characteristics.get('row_count', 0)
    if row_count > 50:
        optimizations.extend([
            'Consider showing only top/bottom items for large datasets',
            'Use summary statistics instead of all data points',
            'Implement filtering to focus on current priorities'
        ])
    
    # Meeting focus optimizations
    if meeting_focus == 'efficiency':
        optimizations.extend([
            'Highlight items below target performance',
            'Show trend arrows for quick status assessment',
            'Include benchmark comparisons where relevant'
        ])
    elif meeting_focus == 'quality':
        optimizations.extend([
            'Prioritize showing quality issues requiring action',
            'Use clear pass/fail indicators',
            'Include defect rate trends over time'
        ])
    
    return optimizations


def _generate_overall_recommendation(current_chart_type: str, data_characteristics: Dict[str, Any], meeting_focus: str, effectiveness_analysis: Dict[str, Any]) -> str:
    """Generate overall recommendation for chart improvement."""
    score = effectiveness_analysis['score']
    
    if score >= 8:
        return f"Current {current_chart_type} chart is well-suited for this data and meeting context. Consider minor formatting improvements for optimal presentation."
    elif score >= 6:
        return f"Current {current_chart_type} chart is adequate but could be improved. Consider alternative chart types or enhanced formatting for better meeting effectiveness."
    else:
        return f"Current {current_chart_type} chart may not be optimal for this meeting context. Strongly consider switching to a more suitable chart type for better data communication."


# Dashboard creation functions
def _create_dashboard_section_visualization(section_data: List[Dict], section_name: str, meeting_type: str, focus_areas: List[str]) -> Dict[str, Any]:
    """Create visualization for a dashboard section."""
    try:
        if not section_data:
            return {
                'status': 'no_data',
                'message': f'No data available for {section_name}',
                'chart_type': 'placeholder'
            }
        
        df = pd.DataFrame(section_data)
        
        # Determine appropriate visualization for section
        if section_name.lower() in ['production', 'output', 'manufacturing']:
            chart_spec = _get_production_section_chart_spec(df, meeting_type)
        elif section_name.lower() in ['quality', 'defects', 'inspection']:
            chart_spec = _get_quality_section_chart_spec(df, meeting_type)
        elif section_name.lower() in ['equipment', 'machines', 'maintenance']:
            chart_spec = _get_equipment_section_chart_spec(df, meeting_type)
        elif section_name.lower() in ['inventory', 'materials', 'stock']:
            chart_spec = _get_inventory_section_chart_spec(df, meeting_type)
        else:
            chart_spec = _get_generic_section_chart_spec(df, meeting_type)
        
        # Create the visualization
        fig = _create_production_plotly_visualization(df, chart_spec, meeting_type)
        
        return {
            'status': 'success',
            'chart_type': chart_spec['type'],
            'chart_spec': chart_spec,
            'plotly_json': fig.to_json(),
            'plotly_html': fig.to_html(include_plotlyjs='cdn'),
            'data_summary': {
                'rows': len(df),
                'columns': list(df.columns)
            },
            'section_insights': _generate_section_insights(df, section_name, meeting_type)
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e),
            'fallback': _create_placeholder_chart(section_name)
        }


def _create_placeholder_chart(section_name: str) -> Dict[str, Any]:
    """Create a placeholder chart when no data is available."""
    fig = go.Figure()
    fig.add_annotation(
        text=f"No data available for {section_name}",
        xref="paper", yref="paper",
        x=0.5, y=0.5,
        xanchor='center', yanchor='middle',
        showarrow=False,
        font=dict(size=16, color="gray")
    )
    fig.update_layout(
        title=f"{section_name} - No Data Available",
        template="plotly_white",
        height=300
    )
    
    return {
        'chart_type': 'placeholder',
        'plotly_json': fig.to_json(),
        'plotly_html': fig.to_html(include_plotlyjs='cdn')
    }


def _get_production_section_chart_spec(df: pd.DataFrame, meeting_type: str) -> Dict[str, Any]:
    """Get chart specification for production section."""
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
    
    if categorical_cols and numeric_cols:
        return {
            'type': 'bar',
            'x': categorical_cols[0],
            'y': numeric_cols[0],
            'color_theme': 'streamlit',
            'reasoning': f'Production performance by {categorical_cols[0]}'
        }
    elif len(numeric_cols) >= 2:
        return {
            'type': 'grouped_bar',
            'x': categorical_cols[0] if categorical_cols else 'index',
            'y': numeric_cols[:2],
            'color_theme': 'streamlit',
            'reasoning': 'Production metrics comparison'
        }
    else:
        return {
            'type': 'table',
            'color_theme': 'streamlit',
            'reasoning': 'Detailed production data overview'
        }


def _get_quality_section_chart_spec(df: pd.DataFrame, meeting_type: str) -> Dict[str, Any]:
    """Get chart specification for quality section."""
    # Look for quality-specific columns
    quality_cols = [col for col in df.columns if any(keyword in col.lower() 
                   for keyword in ['quality', 'defect', 'yield', 'pass', 'fail'])]
    
    if quality_cols:
        return {
            'type': 'bar',
            'x': quality_cols[0] if quality_cols[0] in df.select_dtypes(include=['object']).columns else df.columns[0],
            'y': quality_cols[0] if quality_cols[0] in df.select_dtypes(include=['number']).columns else df.select_dtypes(include=['number']).columns[0],
            'color_theme': 'quality',
            'reasoning': 'Quality metrics with status colors'
        }
    else:
        return _get_generic_section_chart_spec(df, meeting_type)


def _get_equipment_section_chart_spec(df: pd.DataFrame, meeting_type: str) -> Dict[str, Any]:
    """Get chart specification for equipment section."""
    # Look for status columns
    status_cols = [col for col in df.columns if 'status' in col.lower()]
    
    if status_cols:
        return {
            'type': 'bar',
            'x': status_cols[0],
            'y': 'count',
            'color_theme': 'status',
            'reasoning': 'Equipment status distribution'
        }
    else:
        return _get_generic_section_chart_spec(df, meeting_type)


def _get_inventory_section_chart_spec(df: pd.DataFrame, meeting_type: str) -> Dict[str, Any]:
    """Get chart specification for inventory section."""
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
    
    if categorical_cols and numeric_cols:
        return {
            'type': 'bar',
            'x': categorical_cols[0],
            'y': numeric_cols[0],
            'color_theme': 'streamlit',
            'reasoning': f'Inventory levels by {categorical_cols[0]}'
        }
    else:
        return _get_generic_section_chart_spec(df, meeting_type)


def _get_generic_section_chart_spec(df: pd.DataFrame, meeting_type: str) -> Dict[str, Any]:
    """Get generic chart specification for any section."""
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
    
    if categorical_cols and numeric_cols:
        return {
            'type': 'bar',
            'x': categorical_cols[0],
            'y': numeric_cols[0],
            'color_theme': 'streamlit',
            'reasoning': 'General data comparison'
        }
    else:
        return {
            'type': 'table',
            'color_theme': 'streamlit',
            'reasoning': 'Comprehensive data table'
        }


def _generate_dashboard_layout_recommendations(data_sections: Dict[str, List[Dict]], focus_areas: List[str], meeting_type: str) -> List[str]:
    """Generate layout recommendations for dashboard."""
    recommendations = []
    
    # Priority-based layout
    if 'production' in focus_areas:
        recommendations.append('Place production metrics in the top-left position for immediate visibility')
    if 'quality' in focus_areas:
        recommendations.append('Position quality charts prominently to highlight quality issues')
    if 'equipment' in focus_areas:
        recommendations.append('Include equipment status in a dedicated section for maintenance planning')
    
    # Meeting type recommendations
    if meeting_type == 'daily':
        recommendations.extend([
            'Use a compact 2x2 grid layout for quick overview',
            'Prioritize actionable items in the top row',
            'Keep detailed data in expandable sections'
        ])
    elif meeting_type == 'weekly':
        recommendations.extend([
            'Use a 2x3 or 3x2 grid for comprehensive review',
            'Include trend analysis in dedicated sections',
            'Add comparison views for week-over-week analysis'
        ])
    
    return recommendations


def _generate_dashboard_meeting_insights(data_sections: Dict[str, List[Dict]], focus_areas: List[str], meeting_type: str) -> List[str]:
    """Generate meeting insights across all dashboard sections."""
    insights = []
    
    # Cross-section analysis
    total_sections = len(data_sections)
    sections_with_data = sum(1 for data in data_sections.values() if data)
    
    if sections_with_data == 0:
        insights.append('No data available across all sections - investigate data collection systems')
    elif sections_with_data < total_sections:
        insights.append(f'Data available for {sections_with_data}/{total_sections} sections - some areas may need attention')
    else:
        insights.append(f'Complete data available across all {total_sections} sections')
    
    # Focus area insights
    if 'production' in focus_areas and 'production' in data_sections:
        insights.append('Production data available for performance analysis')
    if 'quality' in focus_areas and 'quality' in data_sections:
        insights.append('Quality data available for defect analysis')
    
    # Meeting type insights
    if meeting_type == 'daily':
        insights.append('Dashboard optimized for daily standup efficiency')
    elif meeting_type == 'weekly':
        insights.append('Dashboard configured for weekly performance review')
    
    return insights


def _generate_dashboard_interaction_recommendations(data_sections: Dict[str, List[Dict]], meeting_type: str) -> List[str]:
    """Generate interaction recommendations for dashboard."""
    recommendations = []
    
    # General interaction recommendations
    recommendations.extend([
        'Use click interactions to drill down into detailed data',
        'Implement hover tooltips for additional context',
        'Add filter controls for time period selection',
        'Include export options for follow-up analysis'
    ])
    
    # Meeting type specific recommendations
    if meeting_type == 'daily':
        recommendations.extend([
            'Enable quick navigation between sections',
            'Implement one-click refresh for real-time data',
            'Add bookmark functionality for key views'
        ])
    elif meeting_type == 'weekly':
        recommendations.extend([
            'Include comparison toggles for period analysis',
            'Add annotation capabilities for meeting notes',
            'Implement sharing options for stakeholder distribution'
        ])
    
    return recommendations


def _generate_section_insights(df: pd.DataFrame, section_name: str, meeting_type: str) -> List[str]:
    """Generate insights for a specific dashboard section."""
    insights = []
    
    row_count = len(df)
    
    # General insights
    if row_count == 0:
        insights.append(f'No {section_name} data available')
    elif row_count <= 10:
        insights.append(f'Limited {section_name} data ({row_count} records) - suitable for detailed review')
    else:
        insights.append(f'{section_name} data available ({row_count} records) - focus on key metrics')
    
    # Section-specific insights
    if section_name.lower() in ['production', 'manufacturing']:
        insights.append('Review production targets and completion rates')
    elif section_name.lower() in ['quality', 'defects']:
        insights.append('Focus on quality issues requiring immediate action')
    elif section_name.lower() in ['equipment', 'machines']:
        insights.append('Check equipment status and maintenance needs')
    elif section_name.lower() in ['inventory', 'materials']:
        insights.append('Monitor inventory levels and reorder requirements')
    
    return insights


def _create_fallback_dashboard(data_sections: Dict[str, List[Dict]], focus_areas: List[str], meeting_type: str) -> Dict[str, Any]:
    """Create a fallback dashboard when main creation fails."""
    return {
        'success': False,
        'fallback': True,
        'meeting_type': meeting_type,
        'focus_areas': focus_areas,
        'message': 'Dashboard creation failed - using simplified view',
        'sections': {name: _create_placeholder_chart(name) for name in data_sections.keys()},
        'recommendations': [
            'Check data format and structure',
            'Verify all required columns are present',
            'Try creating individual charts first',
            'Contact support if issues persist'
        ]
    }


def _handle_production_visualization_error(error: Exception, data: List[Dict], analysis_intent: str, chart_reasoning: str, meeting_context: str) -> Dict[str, Any]:
    """Handle production visualization errors with meeting-specific context."""
    logger = logging.getLogger(__name__)
    error_message = str(error)
    
    # Create error context
    error_context = ErrorContext(
        original_query=f"Production visualization: {analysis_intent}",
        error_message=error_message,
        error_type='production_visualization_error',
        timestamp=datetime.now(),
        execution_time=0.0,
        partial_results={'data_available': len(data) > 0 if data else False}
    )
    
    # Analyze error
    analyzer = IntelligentErrorAnalyzer()
    analysis = analyzer.analyze_error(error_context)
    
    # Generate production-specific suggestions
    production_suggestions = _get_production_visualization_suggestions(error_message, data, analysis_intent, meeting_context)
    
    # Try to create a fallback visualization
    fallback_viz = _create_fallback_visualization(data) if data else None
    
    logger.warning(f"Production visualization error: {error_message}")
    
    response = {
        'success': False,
        'error': error_message,
        'error_type': 'production_visualization_error',
        'meeting_context': meeting_context,
        'user_friendly_message': f"Unable to create visualization for {meeting_context} meeting",
        'original_intent': analysis_intent,
        'chart_reasoning': chart_reasoning,
        'suggestions': production_suggestions,
        'meeting_alternatives': [
            'Use tabular data view for detailed analysis',
            'Focus on key metrics discussion without charts',
            'Schedule follow-up for visualization troubleshooting'
        ],
        'data_summary': {
            'data_available': len(data) > 0 if data else False,
            'data_rows': len(data) if data else 0
        }
    }
    
    # Add fallback visualization if available
    if fallback_viz:
        response['fallback_visualization'] = fallback_viz
        response['fallback_message'] = f"Here's a basic table view for your {meeting_context} meeting:"
    
    return response


def _get_production_visualization_suggestions(error_message: str, data: List[Dict], analysis_intent: str, meeting_context: str) -> List[str]:
    """Generate production-specific visualization error suggestions."""
    suggestions = []
    error_lower = error_message.lower()
    
    # Standard error suggestions
    if 'empty' in error_lower or 'no data' in error_lower:
        suggestions.extend([
            f'No data available for {meeting_context} meeting analysis',
            'Check if production systems are collecting data',
            'Verify database connectivity and data sources',
            'Consider using get_production_context() for meeting data'
        ])
    elif 'column' in error_lower:
        suggestions.extend([
            'Production data structure may not match expected format',
            'Verify that production queries return correct column names',
            'Check that numeric columns contain actual production values',
            'Ensure time columns are in proper datetime format'
        ])
    else:
        suggestions.extend([
            f'Visualization failed for {meeting_context} meeting context',
            'Try using simpler chart types for production data',
            'Consider table view for detailed production analysis',
            'Check data format compatibility with production metrics'
        ])
    
    # Meeting context suggestions
    if meeting_context == 'daily':
        suggestions.append('For daily meetings, focus on simple, actionable visualizations')
    elif meeting_context == 'weekly':
        suggestions.append('For weekly meetings, trend charts may be more appropriate')
    
    return suggestions


def _create_fallback_visualization(data: List[Dict]) -> Optional[Dict[str, Any]]:
    """Create a fallback table visualization for production data."""
    if not data or len(data) == 0:
        return None
    
    try:
        df = pd.DataFrame(data)
        
        # Create a production-optimized table
        fig = go.Figure(data=[go.Table(
            header=dict(
                values=list(df.columns),
                fill_color=STREAMLIT_COLORS[0],
                align='left',
                font=dict(size=12, color='white')
            ),
            cells=dict(
                values=[df[col] for col in df.columns],
                fill_color='white',
                align='left',
                font=dict(size=11, color='black'),
                height=30
            )
        )])
        
        fig.update_layout(
            title="Production Data - Table View (Fallback)",
            template="plotly_white",
            height=400,
            margin=dict(l=20, r=20, t=60, b=20)
        )
        
        return {
            'chart_type': 'table',
            'reasoning': 'Fallback table view for production meeting data',
            'plotly_json': fig.to_json(),
            'plotly_html': fig.to_html(include_plotlyjs='cdn'),
            'data_summary': {
                'rows': len(df),
                'columns': list(df.columns)
            }
        }
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to create fallback production visualization: {e}")
        return None