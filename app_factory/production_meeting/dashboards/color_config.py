"""
Shared color configuration for production meeting dashboards.
Uses Plotly defaults and minimal custom colors for dark/light mode compatibility.
"""

import plotly.express as px

# Use Plotly's default qualitative color sequence - works in both themes
# This is the standard Plotly color palette that's designed for visibility
DEFAULT_COLORS = px.colors.qualitative.Plotly

# Semantic colors for status indicators (using standard web colors that work in both themes)
STATUS_COLORS = {
    'running': '#00CC96',      # Green
    'idle': '#636EFA',         # Blue
    'maintenance': '#FFA15A',  # Orange
    'breakdown': '#EF553B',    # Red
    'offline': '#7F7F7F',      # Gray
    'scheduled': '#636EFA',    # Blue
    'in_progress': '#FFA15A',  # Orange
    'completed': '#00CC96',    # Green
    'cancelled': '#EF553B',    # Red
    'planned': '#636EFA',      # Blue
    'unplanned': '#EF553B'     # Red
}

# Quality result colors
QUALITY_COLORS = {
    'pass': '#00CC96',    # Green
    'fail': '#EF553B',    # Red
    'rework': '#FFA15A',  # Orange
    'pending': '#636EFA'  # Blue
}

# Priority colors
PRIORITY_COLORS = {
    'critical': '#EF553B',  # Red
    'high': '#FFA15A',      # Orange
    'medium': '#636EFA',    # Blue
    'low': '#00CC96'        # Green
}


def get_performance_color(value, thresholds=None):
    """
    Get color based on performance value.
    Uses standard Plotly colors that work in both light and dark themes.
    """
    if thresholds is None:
        thresholds = {'excellent': 85, 'good': 70, 'fair': 50}

    if value >= thresholds['excellent']:
        return '#00CC96'  # Green
    elif value >= thresholds['good']:
        return '#636EFA'  # Blue
    elif value >= thresholds['fair']:
        return '#FFA15A'  # Orange
    else:
        return '#EF553B'  # Red


def get_status_color_map(status_list):
    """Get color mapping for a list of status values."""
    color_map = {}
    for i, status in enumerate(status_list):
        status_lower = status.lower()
        if status_lower in STATUS_COLORS:
            color_map[status] = STATUS_COLORS[status_lower]
        else:
            # Fallback to Plotly default colors
            color_map[status] = DEFAULT_COLORS[i % len(DEFAULT_COLORS)]
    return color_map


def get_chart_template():
    """Get standard chart template - uses 'plotly' which auto-adapts to theme."""
    return {
        'template': 'plotly',  # Auto-adapts to light/dark
        'height': 400,
    }


def apply_theme_compatibility(fig):
    """
    Apply minimal theme compatibility - let Plotly/Streamlit handle backgrounds.
    Only set essential styling that works in both themes.
    """
    # Don't force backgrounds - let Streamlit theme control them
    fig.update_layout(
        template='plotly',  # Auto-adapts to theme
        margin=dict(l=40, r=40, t=60, b=40)
    )
    return fig
