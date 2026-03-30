from urllib.parse import unquote, urlparse


def parse_oracle_connection(value: str) -> tuple[str, str | None, str | None]:
    if not value.startswith("oracle://"):
        return value, None, None

    parsed = urlparse(value)

    host = parsed.hostname or ""
    port = parsed.port
    user = unquote(parsed.username) if parsed.username else None
    password = unquote(parsed.password) if parsed.password else None

    if host:
        dsn = host
        if port:
            dsn = f"{dsn}:{port}"

        if parsed.path and parsed.path != "/":
            dsn = f"{dsn}{parsed.path}"
        elif parsed.query:
            dsn = f"{dsn}/?{parsed.query}"
    else:
        dsn = value.replace("oracle://", "", 1)

    return dsn, user, password


def split_sql(sql: str) -> list[str]:
    """
    Split a SQL string into individual statements.

    Handles:
    - Semicolon-terminated statements (standard SQL)
    - PL/SQL-style blocks terminated by a lone ``/`` on its own line.
      A ``/`` on its own line takes precedence: it emits whatever has
      accumulated in the buffer as a single statement, regardless of
      any semicolons inside the block.
    """
    statements: list[str] = []
    buffer: list[str] = []
    in_block = False  # True once we've seen a line that starts a block keyword

    # Keywords that open PL/SQL-style blocks
    _BLOCK_STARTERS = (
        "begin",
        "declare",
        "create or replace procedure",
        "create or replace function",
        "create or replace package",
        "create or replace package body",
        "create or replace trigger",
        "create or replace type",
        "create or replace type body",
    )

    for line in sql.splitlines():
        stripped = line.strip()

        if stripped == "/":
            # Close a PL/SQL block
            block = "\n".join(buffer).strip()
            if block:
                statements.append(block)
            buffer = []
            in_block = False
        else:
            if not in_block and stripped.lower().startswith(_BLOCK_STARTERS):
                in_block = True

            buffer.append(line)

            # Only flush on semicolon when NOT inside a PL/SQL block
            if not in_block and stripped.endswith(";"):
                stmt = "\n".join(buffer).strip()
                if stmt:
                    statements.append(stmt)
                buffer = []

    # Flush any trailing content with no terminator
    if buffer:
        trailing = "\n".join(buffer).strip()
        if trailing:
            statements.append(trailing)

    return statements
