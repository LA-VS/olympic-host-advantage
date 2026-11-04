"""Build the DuckDB database from raw and reference data, and run the .sql files."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from olympic_hosts.paths import DB_PATH, RAW_DIR, REFERENCE_DIR, SQL_DIR


def build(db_path: Path = DB_PATH) -> Path:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(db_path)) as con:
        for name in ("schema.sql", "panel.sql"):
            sql = (SQL_DIR / name).read_text().format(raw=RAW_DIR.as_posix(), ref=REFERENCE_DIR.as_posix())
            con.execute(sql)
        _check(con)
    return db_path


def _check(con: duckdb.DuckDBPyConnection) -> None:
    unmapped = con.sql("SELECT DISTINCT games_id, noc FROM medal_result WHERE nation_id IS NULL").fetchall()
    if unmapped:
        raise ValueError(f"Medal NOCs missing from noc_map.csv: {unmapped}")
    bad_hosts = con.sql("SELECT games_id FROM games WHERE host_nation_id IS NULL").fetchall()
    if bad_hosts:
        raise ValueError(f"Hosts missing from noc_map.csv: {bad_hosts}")


def query(sql: str, db_path: Path = DB_PATH) -> pd.DataFrame:
    """Run SQL text, or the name of a file in sql/, against the database."""
    if sql.endswith(".sql"):
        sql = (SQL_DIR / sql).read_text()
    with duckdb.connect(str(db_path), read_only=True) as con:
        return con.sql(sql).df()


def panel(db_path: Path = DB_PATH) -> pd.DataFrame:
    return query("SELECT * FROM analysis_panel ORDER BY season, nation_id, year", db_path)
