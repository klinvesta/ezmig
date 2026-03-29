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
