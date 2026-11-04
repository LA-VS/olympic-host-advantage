"""Export the normalised tables and the analysis panel as CSV for the Power BI report.

Writes to data/processed/powerbi/. See docs/powerbi.md for the model and visuals.
"""

import duckdb

from olympic_hosts.build import build
from olympic_hosts.paths import DB_PATH, PROCESSED_DIR

TABLES = ["nation", "noc_map", "games", "medal_result", "participation", "nation_year_economics", "analysis_panel"]

if __name__ == "__main__":
    build()
    out = PROCESSED_DIR / "powerbi"
    out.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(DB_PATH), read_only=True) as con:
        for table in TABLES:
            con.sql(f"SELECT * FROM {table}").write_csv(str(out / f"{table}.csv"))
            print(f"Wrote {out / table}.csv")
