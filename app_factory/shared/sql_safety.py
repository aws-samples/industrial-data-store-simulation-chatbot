"""
SQL safety for model-generated queries.

Defense in depth:
1. validate_readonly_query() — fast structural check with word-boundary
   matching (no substring false-positives on identifiers like "LastUpdated").
2. The real enforcement is the read-only SQLite engine
   (DatabaseManager(read_only=True)); SQLite rejects any write at the
   connection level regardless of what the validator misses.
"""

import re
from typing import Any, Dict

# Statements that modify data or schema, or escape the database file.
# Matched on word boundaries so identifiers containing these words pass.
_FORBIDDEN = re.compile(
    r'\b(insert|update|delete|drop|alter|create|truncate|replace|'
    r'attach|detach|vacuum|reindex|pragma)\b',
    re.IGNORECASE,
)

_ALLOWED_START = re.compile(r'^\s*(select|with|explain)\b', re.IGNORECASE)


def _strip_literals_and_comments(query: str) -> str:
    """Remove string literals and comments so keywords inside them don't trip
    the forbidden-word check (e.g. WHERE Status = 'update pending')."""
    query = re.sub(r"'(?:[^']|'')*'", "''", query)
    query = re.sub(r'"(?:[^"]|"")*"', '""', query)
    query = re.sub(r'--[^\n]*', '', query)
    query = re.sub(r'/\*.*?\*/', '', query, flags=re.DOTALL)
    return query


def validate_readonly_query(query: str) -> Dict[str, Any]:
    """Validate that a query is a single read-only statement.

    Returns dict with 'valid' bool and, when invalid, 'error' + 'suggestions'.
    May also include non-fatal 'warnings'.
    """
    result: Dict[str, Any] = {'valid': True, 'warnings': [], 'suggestions': []}

    stripped = query.strip()
    if not stripped:
        result['valid'] = False
        result['error'] = 'Query cannot be empty'
        return result

    if not _ALLOWED_START.match(stripped):
        result['valid'] = False
        result['error'] = (
            'Only read-only queries are allowed. '
            'Start your query with SELECT (or WITH for CTEs).'
        )
        result['suggestions'] = ['Use SELECT statements to query data without modifying it']
        return result

    cleaned = _strip_literals_and_comments(stripped)

    # Reject multi-statement queries (a trailing semicolon is fine)
    if ';' in cleaned.rstrip().rstrip(';'):
        result['valid'] = False
        result['error'] = 'Multiple SQL statements are not allowed. Run one query at a time.'
        return result

    match = _FORBIDDEN.search(cleaned)
    if match:
        result['valid'] = False
        result['error'] = (
            f'Modifying operation "{match.group(0).upper()}" is not allowed. '
            'Use SELECT queries only.'
        )
        result['suggestions'] = ['Use SELECT statements to query data without modifying it']
        return result

    if cleaned.count('(') != cleaned.count(')'):
        result['valid'] = False
        result['error'] = 'Unmatched parentheses in query'
        return result

    lowered = cleaned.lower()
    if 'select *' in lowered and not re.search(r'\blimit\b', lowered):
        result['warnings'].append(
            'Consider using LIMIT clause with SELECT * for better performance'
        )
        result['suggestions'].append('Add "LIMIT 100" to limit results for testing')

    return result
