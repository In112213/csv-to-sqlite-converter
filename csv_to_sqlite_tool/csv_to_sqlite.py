from __future__ import annotations

import argparse
import csv
import re
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path


class CSVImportError(Exception):
    """Raised when the CSV file cannot be imported safely."""


@dataclass(frozen=True)
class ImportResult:
    csv_path: Path
    db_path: Path
    table_name: str
    columns: tuple[str, ...]
    rows_imported: int
    rows_skipped: int


def normalize_identifier(raw_name: str | None, fallback: str) -> str:
    """Turn a file/header name into a SQLite-friendly identifier."""
    value = (raw_name or "").strip().lower()
    value = re.sub(r"\W+", "_", value, flags=re.UNICODE).strip("_")

    if not value:
        value = fallback
    if value[0].isdigit():
        value = f"_{value}"

    return value


def make_unique_identifiers(raw_names: list[str]) -> tuple[str, ...]:
    used: set[str] = set()
    result: list[str] = []

    for index, raw_name in enumerate(raw_names, start=1):
        base_name = normalize_identifier(raw_name, f"column_{index}")
        name = base_name
        suffix = 2

        while name in used:
            name = f"{base_name}_{suffix}"
            suffix += 1

        used.add(name)
        result.append(name)

    return tuple(result)


def quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def parse_delimiter(value: str | None) -> str | None:
    if value is None or value == "":
        return None
    if value.lower() == "tab" or value == r"\t":
        return "\t"
    if len(value) != 1:
        raise CSVImportError("Delimiter must be one character, for example ',' or ';'.")
    return value


def build_manual_dialect(delimiter: str) -> type[csv.excel]:
    class ManualDialect(csv.excel):
        pass

    ManualDialect.delimiter = delimiter
    return ManualDialect


def choose_dialect(handle, delimiter: str | None) -> type[csv.Dialect]:
    parsed_delimiter = parse_delimiter(delimiter)
    if parsed_delimiter is not None:
        return build_manual_dialect(parsed_delimiter)

    sample = handle.read(8192)
    handle.seek(0)

    if not sample.strip():
        raise CSVImportError("CSV file is empty.")

    try:
        return csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        return csv.excel


def table_exists(connection: sqlite3.Connection, table_name: str) -> bool:
    cursor = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    )
    return cursor.fetchone() is not None


def existing_columns(connection: sqlite3.Connection, table_name: str) -> tuple[str, ...]:
    cursor = connection.execute(f"PRAGMA table_info({quote_identifier(table_name)})")
    return tuple(row[1] for row in cursor.fetchall())


def import_csv_to_sqlite(
    csv_path: str | Path,
    db_path: str | Path,
    table_name: str | None = None,
    delimiter: str | None = None,
    encoding: str = "utf-8-sig",
    if_exists: str = "replace",
    strict: bool = True,
) -> ImportResult:
    csv_file = Path(csv_path)
    sqlite_file = Path(db_path)

    if if_exists not in {"replace", "append", "fail"}:
        raise CSVImportError("if_exists must be: replace, append, or fail.")
    if not csv_file.exists():
        raise CSVImportError(f"CSV file was not found: {csv_file}")
    if not csv_file.is_file():
        raise CSVImportError(f"CSV path is not a file: {csv_file}")

    sqlite_file.parent.mkdir(parents=True, exist_ok=True)
    safe_table_name = normalize_identifier(table_name or csv_file.stem, "data")

    with csv_file.open("r", encoding=encoding, newline="") as handle:
        dialect = choose_dialect(handle, delimiter)
        reader = csv.reader(handle, dialect)

        try:
            raw_headers = next(reader)
        except StopIteration as exc:
            raise CSVImportError("CSV file has no header row.") from exc

        if not any(header.strip() for header in raw_headers):
            raise CSVImportError("CSV header row is empty.")

        columns = make_unique_identifiers(raw_headers)
        quoted_table = quote_identifier(safe_table_name)
        quoted_columns = ", ".join(quote_identifier(column) for column in columns)
        column_defs = ", ".join(f"{quote_identifier(column)} TEXT" for column in columns)
        placeholders = ", ".join("?" for _ in columns)
        insert_sql = (
            f"INSERT INTO {quoted_table} ({quoted_columns}) "
            f"VALUES ({placeholders})"
        )

        rows_imported = 0
        rows_skipped = 0

        with sqlite3.connect(sqlite_file) as connection:
            exists = table_exists(connection, safe_table_name)

            if if_exists == "fail" and exists:
                raise CSVImportError(f"Table already exists: {safe_table_name}")

            if if_exists == "replace":
                connection.execute(f"DROP TABLE IF EXISTS {quoted_table}")
                exists = False

            if if_exists == "append" and exists:
                old_columns = existing_columns(connection, safe_table_name)
                if old_columns != columns:
                    raise CSVImportError(
                        "Existing table columns do not match CSV headers. "
                        f"Expected {old_columns}, got {columns}."
                    )

            connection.execute(f"CREATE TABLE IF NOT EXISTS {quoted_table} ({column_defs})")

            for row_number, row in enumerate(reader, start=2):
                if not row or all(not cell.strip() for cell in row):
                    continue

                if len(row) != len(columns):
                    message = (
                        f"Bad row {row_number}: expected {len(columns)} cells, "
                        f"got {len(row)}."
                    )
                    if strict:
                        raise CSVImportError(message)
                    rows_skipped += 1
                    continue

                connection.execute(insert_sql, row)
                rows_imported += 1

    return ImportResult(
        csv_path=csv_file,
        db_path=sqlite_file,
        table_name=safe_table_name,
        columns=columns,
        rows_imported=rows_imported,
        rows_skipped=rows_skipped,
    )


def ask(prompt: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default else ""
    answer = input(f"{prompt}{suffix}: ").strip()
    return answer or (default or "")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Import a CSV file into an SQLite database.",
    )
    parser.add_argument("csv_path", nargs="?", help="Path to the CSV file.")
    parser.add_argument("-d", "--database", help="Path to the SQLite database.")
    parser.add_argument("-t", "--table", help="SQLite table name.")
    parser.add_argument(
        "--delimiter",
        help=r"CSV delimiter. Examples: ',' ';' '|' or '\t'. Auto-detected by default.",
    )
    parser.add_argument(
        "--encoding",
        default="utf-8-sig",
        help="CSV encoding. Default: utf-8-sig.",
    )
    parser.add_argument(
        "--if-exists",
        choices=("replace", "append", "fail"),
        default="replace",
        help="What to do if the table already exists. Default: replace.",
    )
    parser.add_argument(
        "--skip-bad-rows",
        action="store_true",
        help="Skip rows with a wrong number of cells instead of stopping.",
    )
    parser.add_argument(
        "-i",
        "--interactive",
        action="store_true",
        help="Ask for missing values in a simple dialog mode.",
    )
    return parser


def collect_interactive_values(args: argparse.Namespace) -> argparse.Namespace:
    csv_path = args.csv_path or ask("CSV file path")
    if not csv_path:
        raise CSVImportError("CSV file path is required.")

    default_db = str(Path(csv_path).with_suffix(".sqlite3"))
    args.csv_path = csv_path
    args.database = args.database or ask("SQLite database path", default_db)
    args.table = args.table or ask("Table name", Path(csv_path).stem)
    args.delimiter = args.delimiter or ask("Delimiter, leave empty for auto-detect", "")
    return args


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.interactive:
            args = collect_interactive_values(args)
        elif not args.csv_path:
            parser.error("csv_path is required unless --interactive is used.")

        csv_path = Path(args.csv_path)
        db_path = Path(args.database) if args.database else csv_path.with_suffix(".sqlite3")

        result = import_csv_to_sqlite(
            csv_path=csv_path,
            db_path=db_path,
            table_name=args.table,
            delimiter=args.delimiter,
            encoding=args.encoding,
            if_exists=args.if_exists,
            strict=not args.skip_bad_rows,
        )
    except (CSVImportError, sqlite3.Error, UnicodeDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print("OK: CSV imported into SQLite")
    print(f"CSV: {result.csv_path}")
    print(f"Database: {result.db_path}")
    print(f"Table: {result.table_name}")
    print(f"Columns: {', '.join(result.columns)}")
    print(f"Rows imported: {result.rows_imported}")
    print(f"Rows skipped: {result.rows_skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
