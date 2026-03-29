from pathlib import Path


def write_versioned(path: Path, up_sql: str, down_sql: str) -> None:
    path.write_text(
        f"-- ezmig:apply\n{up_sql}\n\n-- ezmig:rollback\n{down_sql}\n",
        encoding="utf-8",
    )
