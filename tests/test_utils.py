from ezmig.utils import parse_oracle_connection, split_sql


def test_parse_oracle_connection_url_with_query_service_name():
    dsn, user, password = parse_oracle_connection(
        "oracle://system:oracle@localhost:1521/?service_name=XEPDB1"
    )

    assert dsn == "localhost:1521/?service_name=XEPDB1"
    assert user == "system"
    assert password == "oracle"


def test_parse_oracle_connection_url_with_path_service_name():
    dsn, user, password = parse_oracle_connection("oracle://scott:tiger@dbhost:1521/XEPDB1")

    assert dsn == "dbhost:1521/XEPDB1"
    assert user == "scott"
    assert password == "tiger"


def test_parse_oracle_connection_legacy_dsn():
    dsn, user, password = parse_oracle_connection("oracle://system/oracle@localhost:1521/XEPDB1")

    assert dsn == "system/oracle@localhost:1521/XEPDB1"
    assert user is None
    assert password is None


def test_parse_oracle_connection_plain_dsn_passthrough():
    dsn, user, password = parse_oracle_connection("system/oracle@localhost:1521/XEPDB1")

    assert dsn == "system/oracle@localhost:1521/XEPDB1"
    assert user is None
    assert password is None


def test_single_statement():
    sql = "SELECT 1;"
    assert split_sql(sql) == ["SELECT 1;"]


def test_multiple_semicolon_statements():
    sql = "CREATE TABLE a (id INT);\nCREATE TABLE b (id INT);"
    result = split_sql(sql)
    assert result == ["CREATE TABLE a (id INT);", "CREATE TABLE b (id INT);"]


def test_multiline_statement():
    sql = "CREATE TABLE users (\n    id INT,\n    name TEXT\n);"
    result = split_sql(sql)
    assert len(result) == 1
    assert "CREATE TABLE users" in result[0]
    assert "name TEXT" in result[0]


def test_plsql_slash_block():
    sql = "BEGIN\n    NULL;\nEND;\n/"
    result = split_sql(sql)
    assert len(result) == 1
    assert "BEGIN" in result[0]
    assert "END;" in result[0]


def test_mixed_semicolon_and_slash():
    sql = "CREATE TABLE t (id INT);\n\nCREATE OR REPLACE PROCEDURE p IS\nBEGIN\n    NULL;\nEND;\n/"
    result = split_sql(sql)
    assert len(result) == 2
    assert result[0] == "CREATE TABLE t (id INT);"
    assert "PROCEDURE p" in result[1]
    assert "END;" in result[1]


def test_empty_string():
    assert split_sql("") == []


def test_whitespace_only():
    assert split_sql("   \n   \n  ") == []


def test_trailing_content_without_terminator():
    sql = "SELECT 1;\nSELECT 2"
    result = split_sql(sql)
    assert result == ["SELECT 1;", "SELECT 2"]


def test_strips_surrounding_whitespace():
    sql = "\n  SELECT 1;  \n"
    result = split_sql(sql)
    assert result == ["SELECT 1;"]


def test_comment_lines_preserved():
    sql = "-- create users\nCREATE TABLE users (id INT);"
    result = split_sql(sql)
    assert len(result) == 1
    assert "-- create users" in result[0]
    assert "CREATE TABLE users" in result[0]
