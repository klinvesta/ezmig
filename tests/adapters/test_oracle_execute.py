import pytest

from ezmig.adapters.base import SQLExecutionError
from ezmig.adapters.oracle import OracleAdapter


def test_normalize_statement_strips_trailing_semicolon_for_simple_sql():
    normalized = OracleAdapter._normalize_statement("CREATE TABLE users (name VARCHAR2(100));")
    assert normalized == "CREATE TABLE users (name VARCHAR2(100))"


def test_normalize_statement_keeps_semicolon_for_plsql_block():
    statement = "BEGIN\n    NULL;\nEND;"
    normalized = OracleAdapter._normalize_statement(statement)
    assert normalized == statement


def test_normalize_statement_keeps_semicolon_for_create_or_replace_procedure():
    statement = "CREATE OR REPLACE PROCEDURE p AS\nBEGIN\n    NULL;\nEND;"
    normalized = OracleAdapter._normalize_statement(statement)
    assert normalized == statement


def test_normalize_statement_strips_semicolon_for_create_or_replace_view():
    statement = "CREATE OR REPLACE VIEW users_v AS SELECT name FROM users;"
    normalized = OracleAdapter._normalize_statement(statement)
    assert normalized == "CREATE OR REPLACE VIEW users_v AS SELECT name FROM users"


def test_execute_raises_sql_execution_error_with_statement_context(mocker):
    adapter = OracleAdapter("oracle://test")
    cursor = mocker.MagicMock()
    cursor.execute.side_effect = [None, RuntimeError("ORA-00900: invalid SQL statement")]
    connection = mocker.MagicMock()
    connection.cursor.return_value = cursor
    adapter.conn = connection

    with pytest.raises(SQLExecutionError) as exc_info:
        adapter.execute("SELECT 1;\nSELECT FROM dual;")

    error = exc_info.value
    assert error.statement == "SELECT FROM dual"
    assert error.statement_index == 2
    assert error.total_statements == 2
    assert "statement 2/2" in str(error)


def test_strip_sqlplus_commands_removes_known_commands():
    sql = """
SET DEFINE OFF
PROMPT applying migration
SPOOL run.log
REM this should be ignored
WHENEVER SQLERROR EXIT SQL.SQLCODE
CREATE TABLE users (id NUMBER);
SPOOL OFF
"""

    cleaned = OracleAdapter._strip_sqlplus_commands(sql)

    assert "SET DEFINE OFF" not in cleaned
    assert "PROMPT applying migration" not in cleaned
    assert "SPOOL run.log" not in cleaned
    assert "WHENEVER SQLERROR EXIT SQL.SQLCODE" not in cleaned
    assert "REM this should be ignored" not in cleaned
    assert "CREATE TABLE users (id NUMBER);" in cleaned


def test_execute_ignores_sqlplus_commands(mocker):
    adapter = OracleAdapter("oracle://test")
    cursor = mocker.MagicMock()
    connection = mocker.MagicMock()
    connection.cursor.return_value = cursor
    adapter.conn = connection

    adapter.execute(
        """
        SET DEFINE OFF
        PROMPT start
        CREATE TABLE users (id NUMBER);
        """
    )

    cursor.execute.assert_called_once_with("CREATE TABLE users (id NUMBER)")


def test_normalize_statement_ignores_comment_only_statement():
    statement = """
--show errors
/*
comment only block
*/
REM sqlplus comment
"""

    normalized = OracleAdapter._normalize_statement(statement)

    assert normalized == ""


def test_execute_ignores_comment_only_statements(mocker):
    adapter = OracleAdapter("oracle://test")
    cursor = mocker.MagicMock()
    connection = mocker.MagicMock()
    connection.cursor.return_value = cursor
    adapter.conn = connection

    adapter.execute(
        """
        --show errors;
        /* only comments */;
        CREATE TABLE users (id NUMBER);
        """
    )

    cursor.execute.assert_called_once_with("CREATE TABLE users (id NUMBER)")


def test_execute_ignores_double_dash_show_errors_comment(mocker):
    adapter = OracleAdapter("oracle://test")
    cursor = mocker.MagicMock()
    connection = mocker.MagicMock()
    connection.cursor.return_value = cursor
    adapter.conn = connection

    adapter.execute("--show errors")

    cursor.execute.assert_not_called()
