"""Tests for SQL safety: query validation and read-only engine enforcement."""

import os
import sqlite3
import tempfile

import pytest

from app_factory.shared.database import DatabaseManager
from app_factory.shared.sql_safety import validate_readonly_query


class TestValidateReadonlyQuery:
    """Structural validation of model-generated SQL."""

    def test_simple_select_valid(self):
        assert validate_readonly_query("SELECT * FROM WorkOrders LIMIT 10")["valid"]

    def test_cte_valid(self):
        query = "WITH recent AS (SELECT * FROM WorkOrders) SELECT COUNT(*) FROM recent"
        assert validate_readonly_query(query)["valid"]

    def test_empty_query_invalid(self):
        assert not validate_readonly_query("   ")["valid"]

    @pytest.mark.parametrize("stmt", [
        "INSERT INTO WorkOrders VALUES (1)",
        "UPDATE Machines SET Status = 'idle'",
        "DELETE FROM Inventory",
        "DROP TABLE Products",
        "ATTACH DATABASE '/tmp/x.db' AS x",
        "PRAGMA writable_schema = ON",
    ])
    def test_write_statements_invalid(self, stmt):
        assert not validate_readonly_query(stmt)["valid"]

    def test_cte_wrapped_write_invalid(self):
        query = "WITH x AS (SELECT 1) INSERT INTO WorkOrders SELECT * FROM x"
        assert not validate_readonly_query(query)["valid"]

    def test_multi_statement_invalid(self):
        query = "SELECT 1; DROP TABLE Products"
        assert not validate_readonly_query(query)["valid"]

    def test_trailing_semicolon_ok(self):
        assert validate_readonly_query("SELECT 1;")["valid"]

    # Regression: old substring denylist blocked these legitimate queries
    def test_identifier_containing_update_valid(self):
        query = "SELECT LastUpdated FROM Inventory WHERE LastUpdated > '2026-01-01'"
        assert validate_readonly_query(query)["valid"]

    def test_identifier_containing_delete_valid(self):
        query = "SELECT IsDeleted, CreatedAt FROM Machines"
        assert validate_readonly_query(query)["valid"]

    def test_keyword_inside_string_literal_valid(self):
        query = "SELECT * FROM WorkOrders WHERE Status = 'update pending'"
        assert validate_readonly_query(query)["valid"]

    def test_keyword_inside_comment_valid(self):
        query = "SELECT 1 -- update note\n"
        assert validate_readonly_query(query)["valid"]

    def test_unmatched_parens_invalid(self):
        assert not validate_readonly_query("SELECT COUNT( FROM x")["valid"]

    def test_select_star_without_limit_warns(self):
        result = validate_readonly_query("SELECT * FROM WorkOrders")
        assert result["valid"]
        assert result["warnings"]


class TestReadOnlyEngine:
    """The read-only engine must reject writes at the connection level."""

    @pytest.fixture
    def db_file(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        conn = sqlite3.connect(path)
        conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, name TEXT)")
        conn.execute("INSERT INTO t (name) VALUES ('a'), ('b')")
        conn.commit()
        conn.close()
        yield path
        for suffix in ("", "-wal", "-shm"):
            candidate = path + suffix
            if os.path.exists(candidate):
                os.remove(candidate)

    def test_read_only_engine_allows_select(self, db_file):
        db = DatabaseManager(db_path=db_file, read_only=True)
        result = db.execute_query("SELECT * FROM t")
        assert result["success"]
        assert result["row_count"] == 2

    def test_read_only_engine_rejects_write(self, db_file):
        db = DatabaseManager(db_path=db_file, read_only=True)
        result = db.execute_query("INSERT INTO t (name) VALUES ('c')")
        assert not result["success"]
        # Data unchanged
        check = db.execute_query("SELECT COUNT(*) AS n FROM t")
        assert check["rows"][0]["n"] == 2

    def test_read_write_engine_allows_write(self, db_file):
        db = DatabaseManager(db_path=db_file, read_only=False)
        with db.engine.connect() as conn:
            from sqlalchemy import text
            conn.execute(text("INSERT INTO t (name) VALUES ('c')"))
            conn.commit()
        result = db.execute_query("SELECT COUNT(*) AS n FROM t")
        assert result["rows"][0]["n"] == 3


class TestAgentToolsUseReadOnly:
    """Agent database tools must run on a read-only manager."""

    def test_mes_tools_manager_read_only(self):
        from app_factory.mes_agents.tools import database_tools as mes_db
        mes_db._db_manager = None
        assert mes_db._get_db_manager().read_only is True

    def test_pm_tools_manager_read_only(self):
        from app_factory.production_meeting_agents.tools import database_tools as pm_db
        pm_db._readonly_db_manager = None
        assert pm_db._get_readonly_db_manager().read_only is True
