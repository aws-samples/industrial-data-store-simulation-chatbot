"""
Shared color configuration for production meeting dashboards.
Ensures consistent use of Streamlit default colors and theme compatibility.
"""

# Streamlit default color palette - compatible with both light and dark themes
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

# Status-specific color mappings using Streamlit colors
STATUS_COLORS = {
    'running': STREAMLIT_COLORS[3],      # Green
    'idle': STREAMLIT_COLORS[2],         # Blue
    'maintenance': STREAMLIT_COLORS[4],  # Yellow
    'breakdown': STREAMLIT_COLORS[0],    # Red
    'offline': '#95A5A6',               # Gray (neutral)
    'scheduled': STREAMLIT_COLORS[2],    # Blue
    'in_progress': STREAMLIT_COLORS[4],  # Yellow
    'completed': STREAMLIT_COLORS[3],    # Green
    'cancelled': STREAMLIT_COLORS[0]     # Red
}

# Quality-specific color mappings
QUALITY_COLORS = {
    'pass': STREAMLIT_COLORS[3],         # Green
    'fail': STREAMLIT_COLORS[0],         # Red
    'rework': STREAMLIT_COLORS[4],       # Yellow
    'pending': STREAMLIT_COLORS[2]       # Blue
}

# Priority-specific color mappings
PRIORITY_COLORS = {
    'critical': STREAMLIT_COLORS[0],     # Red
    'high': STREAMLIT_COLORS[4],         # Yellow
    'medium': STREAMLIT_COLORS[2],       # Blue
    'low': STREAMLIT_COLORS[3]           # Green
}

# Performance level colors (for gauges, metrics, etc.)
PERFORMANCE_COLORS = {
    'excellent': STREAMLIT_COLORS[3],    # Green (>90%)
    'good': STREAMLIT_COLORS[2],         # Blue (80-90%)
    'fair': STREAMLIT_COLORS[4],         # Yellow (60-80%)
    'poor': STREAMLIT_COLORS[0]          # Red (<60%)
}

# Color scales for continuous data (compatible with both themes)
COLOR_SCALES = {
    'performance': ['#FF6B6B', '#FFEAA7', '#96CEB4'],  # Red to Yellow to Green
    'quality': ['#96CEB4', '#FFEAA7', '#FF6B6B'],      # Green to Yellow to Red
    'utilization': ['#96CEB4', '#FFEAA7', '#FF6B6B'],  # Green to Yellow to Red
    'blues': ['#E3F2FD', '#45B7D1', '#1976D2'],        # Light to Dark Blue
    'reds': ['#FFEBEE', '#FF6B6B', '#C62828']          # Light to Dark Red
}

# Theme-compatible neutral colors
NEUTRAL_COLORS = {
    'white': '#FFFFFF',
    'light_gray': '#F5F5F5',
    'medium_gray': '#BDBDBD',
    'dark_gray': '#424242',
    'black': '#000000',
    'border': '#E0E0E0',
    'text_primary': '#212121',
    'text_secondary': '#757575'
}

def get_performance_color(value, thresholds=None):
    """
    Get color based on performance value.
    
    Args:
        value: Performance value (0-100)
        thresholds: Custom thresholds dict with 'excellent', 'good', 'fair' keys
    
    Returns:
        Color string from Streamlit palette
    """
    if thresholds is None:
        thresholds = {'excellent': 90, 'good': 80, 'fair': 60}
    
    if value >= thresholds['excellent']:
        return PERFORMANCE_COLORS['excellent']
    elif value >= thresholds['good']:
        return PERFORMANCE_COLORS['good']
    elif value >= thresholds['fair']:
        return PERFORMANCE_COLORS['fair']
    else:
        return PERFORMANCE_COLORS['poor']

def get_status_color_map(status_list):
    """
    Get color mapping for a list of status values.
    
    Args:
        status_list: List of status strings
        
    Returns:
        Dictionary mapping status to color
    """
    color_map = {}
    for i, status in enumerate(status_list):
        status_lower = status.lower()
        if status_lower in STATUS_COLORS:
            color_map[status] = STATUS_COLORS[status_lower]
        else:
            # Fallback to Streamlit colors
            color_map[status] = STREAMLIT_COLORS[i % len(STREAMLIT_COLORS)]
    
    return color_map

def get_chart_template():
    """
    Get standard chart template for consistent styling.
    
    Returns:
        Dictionary with plotly template settings
    """
    return {
        'template': 'plotly_white',
        'color_discrete_sequence': STREAMLIT_COLORS,
        'height': 400,
        'title': {'font': {'size': 16}},
        'legend': {
            'orientation': 'h',
            'yanchor': 'bottom',
            'y': 1.02,
            'xanchor': 'right',
            'x': 1
        }
    }

def apply_theme_compatibility(fig):
    """
    Apply theme compatibility settings to a plotly figure.
    
    Args:
        fig: Plotly figure object
        
    Returns:
        Modified plotly figure with theme compatibility
    """
    # Ensure white backgrounds and dark text for readability
    fig.update_layout(
        plot_bgcolor='white',
        paper_bgcolor='white',
        font_color=NEUTRAL_COLORS['text_primary']
    )
    
    # Update axis styling for better visibility
    fig.update_xaxes(
        gridcolor=NEUTRAL_COLORS['light_gray'],
        linecolor=NEUTRAL_COLORS['medium_gray']
    )
    
    fig.update_yaxes(
        gridcolor=NEUTRAL_COLORS['light_gray'],
        linecolor=NEUTRAL_COLORS['medium_gray']
    )
    
    return fig