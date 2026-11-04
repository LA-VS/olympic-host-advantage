"""Build the interactive HTML dashboard: one self contained page with the data embedded."""

import json
from pathlib import Path

from olympic_hosts.build import query
from olympic_hosts.paths import DB_PATH

TEMPLATE = Path(__file__).with_name("dashboard.html")
PLACEHOLDER = "/*DATA*/"

HOSTINGS_SQL = """
WITH h AS (
    SELECT p.nation_id, p.nation_name, p.season, p.games_id, p.year, p.medals, p.golds,
           p.medal_share AS host_share, g.city
    FROM analysis_panel AS p JOIN games AS g USING (games_id)
    WHERE p.host = 1
)
SELECT h.games_id, any_value(h.year) AS year, any_value(h.season) AS season,
       any_value(h.city) AS city, h.nation_id, any_value(h.nation_name) AS nation,
       any_value(h.medals) AS medals, any_value(h.golds) AS golds,
       any_value(h.host_share) AS host_share, avg(p.medal_share) AS usual_share
FROM h JOIN analysis_panel AS p
  ON p.nation_id = h.nation_id AND p.season = h.season AND p.games_id <> h.games_id
GROUP BY h.games_id, h.nation_id
ORDER BY year, season
"""


def dashboard_data(db_path: Path = DB_PATH) -> dict:
    """Each hosting against its usual share, and each host's event study rows."""
    hostings = query(HOSTINGS_SQL, db_path)
    hostings[["medals", "golds"]] = hostings[["medals", "golds"]].astype(int)
    # Rounded so the page is identical on every build: parallel sums differ in the last bits.
    hostings[["host_share", "usual_share"]] = hostings[["host_share", "usual_share"]].round(6)
    events = query("event_study.sql", db_path)[["host_games", "rel", "change_pp"]].round({"change_pp": 4})
    return {"hostings": hostings.to_dict(orient="records"), "events": events.to_dict(orient="records")}


def render(data: dict) -> str:
    """The dashboard page with `data` embedded as a JavaScript literal."""
    payload = json.dumps(data, default=float, allow_nan=False).replace("</", "<\\/")
    template = TEMPLATE.read_text(encoding="utf-8")
    if template.count(PLACEHOLDER) != 1:
        raise ValueError(f"{TEMPLATE.name} must contain {PLACEHOLDER} exactly once")
    return template.replace(PLACEHOLDER, payload)


def write_dashboard(out_path: Path, db_path: Path = DB_PATH) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render(dashboard_data(db_path)), encoding="utf-8")
    return out_path
