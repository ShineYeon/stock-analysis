"""Apply the project's PostgreSQL schema and versioned SQL migrations."""

import argparse
from pathlib import Path
from typing import Iterable

from db.connection import get_db_connection


DB_DIR = Path(__file__).resolve().parent
INIT_SCHEMA = DB_DIR / "init_schema.sql"
MIGRATIONS_DIR = DB_DIR / "migrations"


def migration_files() -> Iterable[Path]:
    return sorted(MIGRATIONS_DIR.glob("[0-9][0-9][0-9]_*.sql"))


def ensure_migration_table(cursor) -> None:
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS public.schema_migrations (
            version VARCHAR(255) PRIMARY KEY,
            applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """
    )


def is_applied(cursor, version: str) -> bool:
    cursor.execute(
        "SELECT EXISTS(SELECT 1 FROM public.schema_migrations WHERE version = %s)",
        (version,),
    )
    return cursor.fetchone()[0]


def apply_sql_file(cursor, path: Path) -> None:
    cursor.execute(path.read_text(encoding="utf-8-sig"))


def apply_migrations(dry_run: bool = False) -> list[str]:
    """Apply init schema once, then unapplied migration files in name order."""
    candidates = [INIT_SCHEMA, *migration_files()]
    if not INIT_SCHEMA.exists():
        raise FileNotFoundError(f"Missing initial schema: {INIT_SCHEMA}")

    applied: list[str] = []
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            ensure_migration_table(cursor)
            for path in candidates:
                version = path.name
                if is_applied(cursor, version):
                    continue
                if dry_run:
                    applied.append(version)
                    continue

                apply_sql_file(cursor, path)
                cursor.execute(
                    "INSERT INTO public.schema_migrations (version) VALUES (%s)",
                    (version,),
                )
                applied.append(version)

            if dry_run:
                connection.rollback()
            else:
                connection.commit()
    return applied


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply PostgreSQL schema migrations.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print migrations that would be applied without changing the database",
    )
    args = parser.parse_args()
    applied = apply_migrations(dry_run=args.dry_run)
    if not applied:
        print("Database schema is already current.")
        return
    action = "Would apply" if args.dry_run else "Applied"
    for version in applied:
        print(f"{action}: {version}")


if __name__ == "__main__":
    main()
