"""Shared cached database access for dashboard tabs.

Provides a @st.cache_resource DatabaseManager and a @st.cache_data query
wrapper so that frequent SQL calls don't re-execute on every Streamlit rerun.
"""

import json

import streamlit as st

from app_factory.shared.database import DatabaseManager


@st.cache_resource
def get_shared_db_manager() -> DatabaseManager:
    """Single DatabaseManager shared across all dashboard tabs."""
    return DatabaseManager()


@st.cache_data(ttl=300)
def cached_query(sql: str, params: str = "") -> dict:
    """Execute a SQL query with 5-min cache.

    ``params`` is a JSON string so Streamlit can hash it; pass empty string
    for no-parameter queries.
    """
    db = get_shared_db_manager()
    param_dict = json.loads(params) if params else None
    return db.execute_query(sql, param_dict)
