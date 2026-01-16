"""
Database utility functions for DB-agnostic date handling.

This module provides date utility functions that calculate dates in Python
instead of SQL, enabling DB-agnostic patterns that work across SQLite,
PostgreSQL, and other databases.
"""

from datetime import datetime, timedelta
from typing import Optional


def days_ago(n: int, reference_date: Optional[datetime] = None) -> str:
    """
    Return date string for N days ago.

    Args:
        n: Number of days to go back
        reference_date: Reference date (defaults to now)

    Returns:
        Date string in YYYY-MM-DD format
    """
    ref = reference_date or datetime.now()
    return (ref - timedelta(days=n)).strftime('%Y-%m-%d')


def days_ahead(n: int, reference_date: Optional[datetime] = None) -> str:
    """
    Return date string for N days from now.

    Args:
        n: Number of days ahead
        reference_date: Reference date (defaults to now)

    Returns:
        Date string in YYYY-MM-DD format
    """
    ref = reference_date or datetime.now()
    return (ref + timedelta(days=n)).strftime('%Y-%m-%d')


def today() -> str:
    """
    Return today's date string.

    Returns:
        Today's date in YYYY-MM-DD format
    """
    return datetime.now().strftime('%Y-%m-%d')


def now_timestamp() -> str:
    """
    Return current timestamp string.

    Returns:
        Current timestamp in YYYY-MM-DD HH:MM:SS format
    """
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def date_diff_days(date1: str, date2: str) -> int:
    """
    Calculate days between two date strings.

    This replaces SQLite julianday arithmetic with Python calculation.

    Args:
        date1: First date string (YYYY-MM-DD format)
        date2: Second date string (YYYY-MM-DD format)

    Returns:
        Number of days between dates (date1 - date2)
    """
    d1 = datetime.strptime(date1[:10], '%Y-%m-%d')
    d2 = datetime.strptime(date2[:10], '%Y-%m-%d')
    return (d1 - d2).days


def parse_date(date_str: str) -> datetime:
    """
    Parse a date string to datetime object.

    Handles both date-only and datetime formats.

    Args:
        date_str: Date string to parse

    Returns:
        datetime object
    """
    # Try date-only format first
    if len(date_str) == 10:
        return datetime.strptime(date_str, '%Y-%m-%d')
    # Try datetime format
    try:
        return datetime.strptime(date_str[:19], '%Y-%m-%d %H:%M:%S')
    except ValueError:
        # Fallback to date-only
        return datetime.strptime(date_str[:10], '%Y-%m-%d')


def format_date(dt: datetime) -> str:
    """
    Format a datetime object to date string.

    Args:
        dt: datetime object

    Returns:
        Date string in YYYY-MM-DD format
    """
    return dt.strftime('%Y-%m-%d')


def format_datetime(dt: datetime) -> str:
    """
    Format a datetime object to datetime string.

    Args:
        dt: datetime object

    Returns:
        Datetime string in YYYY-MM-DD HH:MM:SS format
    """
    return dt.strftime('%Y-%m-%d %H:%M:%S')


def date_range_start(date_str: str) -> str:
    """
    Get the start of a day for range queries.

    Args:
        date_str: Date string (YYYY-MM-DD format)

    Returns:
        Datetime string for start of day (YYYY-MM-DD 00:00:00)
    """
    return f"{date_str[:10]} 00:00:00"


def date_range_end(date_str: str) -> str:
    """
    Get the end of a day for range queries.

    Args:
        date_str: Date string (YYYY-MM-DD format)

    Returns:
        Datetime string for end of day (YYYY-MM-DD 23:59:59)
    """
    return f"{date_str[:10]} 23:59:59"
