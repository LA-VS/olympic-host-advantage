"""Fetch medal tables from Wikipedia and economics from the World Bank.

Medal tables come from the `{{Medals table}}` template on each
"<year> <season> Olympics medal table" article, which stores medals by IOC code
(for example `gold_URS = 43`). Each page is pinned to a revision id in
data/raw/medal_tables_manifest.csv so a rerun fetches exactly the same text.
Wikipedia text is licensed CC BY-SA 4.0.

GDP (NY.GDP.MKTP.CD) and population (SP.POP.TOTL) come from the World Bank
World Development Indicators API, licensed CC BY 4.0.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime

import pandas as pd
import requests

from olympic_hosts.paths import MEDAL_DIR, RAW_DIR, load_hosts

USER_AGENT = "olympic-host-advantage/0.1 (https://github.com/LA-VS/olympic-host-advantage)"
WIKI_API = "https://en.wikipedia.org/w/api.php"
WB_API = "https://api.worldbank.org/v2/country/all/indicator/{indicator}"
WB_INDICATORS = {"gdp_usd": "NY.GDP.MKTP.CD", "population": "SP.POP.TOTL"}

_MEDAL = re.compile(r"\|\s*(gold|silver|bronze)_([A-Z]{3})\s*=\s*(\d+)")
_HOST = re.compile(r"\|\s*host_([A-Z]{3})\s*=\s*yes", re.IGNORECASE)


def parse_medal_template(wikitext: str) -> pd.DataFrame:
    """Extract gold, silver and bronze counts per NOC from the first Medals table template."""
    start = wikitext.find("{{Medals table")
    if start < 0:
        raise ValueError("No {{Medals table}} template found")
    body = _template_body(wikitext, start)
    rows: dict[str, dict[str, int]] = {}
    for medal, noc, count in _MEDAL.findall(body):
        rows.setdefault(noc, {"gold": 0, "silver": 0, "bronze": 0})[medal] = int(count)
    hosts = {m.upper() for m in _HOST.findall(body)}
    df = pd.DataFrame.from_dict(rows, orient="index").rename_axis("noc").reset_index()
    df["template_host"] = df["noc"].isin(hosts)
    return df[["noc", "gold", "silver", "bronze", "template_host"]]


def _template_body(text: str, start: int) -> str:
    """Return the template text from `start` to its matching closing braces."""
    depth, i = 0, start
    while i < len(text) - 1:
        pair = text[i : i + 2]
        if pair == "{{":
            depth, i = depth + 1, i + 2
        elif pair == "}}":
            depth, i = depth - 1, i + 2
            if depth == 0:
                return text[start:i]
        else:
            i += 1
    raise ValueError("Unclosed {{Medals table}} template")


def _wiki_revision(title: str, revid: int | None = None) -> dict:
    params = {
        "action": "query",
        "prop": "revisions",
        "rvprop": "content|ids|timestamp",
        "rvslots": "main",
        "format": "json",
        "formatversion": 2,
    }
    if revid is None:
        params |= {"titles": title, "redirects": 1}
    else:
        params["revids"] = revid
    r = requests.get(WIKI_API, params=params, headers={"User-Agent": USER_AGENT}, timeout=60)
    r.raise_for_status()
    page = r.json()["query"]["pages"][0]
    rev = page["revisions"][0]
    return {
        "title": page["title"],
        "revid": rev["revid"],
        "timestamp": rev["timestamp"],
        "text": rev["slots"]["main"]["content"],
    }


def fetch_medal_tables(pinned: bool = True) -> pd.DataFrame:
    """Download every medal table. With pinned=True, reuse the revision ids in the manifest."""
    MEDAL_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path = RAW_DIR / "medal_tables_manifest.csv"
    old = pd.read_csv(manifest_path).set_index("games_id") if pinned and manifest_path.exists() else None
    hosts = load_hosts()
    rows = []
    for g in hosts[~hosts["future"]].itertuples():
        title = f"{g.year} {g.season} Olympics medal table"
        revid = int(old.loc[g.games_id, "revid"]) if old is not None and g.games_id in old.index else None
        rev = _wiki_revision(title, revid)
        table = parse_medal_template(rev["text"])
        table.insert(0, "games_id", g.games_id)
        table.to_csv(MEDAL_DIR / f"{g.games_id}.csv", index=False)
        retrieved = (
            old.loc[g.games_id, "retrieved_utc"]
            if revid is not None
            else datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        )
        rows.append(
            {
                "games_id": g.games_id,
                "title": rev["title"],
                "revid": rev["revid"],
                "revision_timestamp": rev["timestamp"],
                "retrieved_utc": retrieved,
                "url": f"https://en.wikipedia.org/w/index.php?oldid={rev['revid']}",
            }
        )
    manifest = pd.DataFrame(rows)
    manifest.to_csv(manifest_path, index=False)
    return manifest


_HEADING = re.compile(r"^(==+)\s*([^=\n]*)\s*\1\s*$", re.MULTILINE)
_FLAG = re.compile(r"\{\{\s*flagIOC\w*\s*\|\s*([A-Z]{3})\b", re.IGNORECASE)


def parse_participants(wikitext: str, min_codes: int = 10) -> list[str] | None:
    """IOC codes listed under a participating nations heading, or None if the page has no list.

    Takes the first heading (any level) containing "particip" whose section, up to the
    next heading of the same or higher level, holds at least `min_codes` IOC flags.
    """
    headings = list(_HEADING.finditer(wikitext))
    for i, h in enumerate(headings):
        if "particip" not in h.group(2).lower():
            continue
        level = len(h.group(1))
        end = next((n.start() for n in headings[i + 1 :] if len(n.group(1)) <= level), len(wikitext))
        codes = {c.upper() for c in _FLAG.findall(wikitext[h.end() : end])}
        if len(codes) >= min_codes:
            return sorted(codes)
    return None


def fetch_participants(pinned: bool = True) -> pd.DataFrame:
    """Download the participating NOCs for every Games into data/raw/participants.csv."""
    manifest_path = RAW_DIR / "participants_manifest.csv"
    old = pd.read_csv(manifest_path).set_index("games_id") if pinned and manifest_path.exists() else None
    hosts = load_hosts()
    rows, manifest = [], []
    for g in hosts[~hosts["future"]].itertuples():
        title = f"{g.year} {g.season} Olympics"
        revid = int(old.loc[g.games_id, "revid"]) if old is not None and g.games_id in old.index else None
        rev = _wiki_revision(title, revid)
        codes = parse_participants(rev["text"])
        rows += [{"games_id": g.games_id, "noc": c} for c in codes or []]
        retrieved = (
            old.loc[g.games_id, "retrieved_utc"]
            if revid is not None
            else datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        )
        manifest.append(
            {
                "games_id": g.games_id,
                "title": rev["title"],
                "revid": rev["revid"],
                "revision_timestamp": rev["timestamp"],
                "retrieved_utc": retrieved,
                "url": f"https://en.wikipedia.org/w/index.php?oldid={rev['revid']}",
                "participants_listed": len(codes or []),
            }
        )
    out = pd.DataFrame(rows)
    out.to_csv(RAW_DIR / "participants.csv", index=False)
    pd.DataFrame(manifest).to_csv(manifest_path, index=False)
    return out


def fetch_world_bank(start: int = 1960, end: int = 2025) -> pd.DataFrame:
    """Download GDP and population for every country and year into data/raw/world_bank.csv."""
    frames = []
    for column, indicator in WB_INDICATORS.items():
        r = requests.get(
            WB_API.format(indicator=indicator),
            params={"format": "json", "per_page": 20000, "date": f"{start}:{end}"},
            headers={"User-Agent": USER_AGENT},
            timeout=120,
        )
        r.raise_for_status()
        meta, data = r.json()
        if meta["pages"] != 1:
            raise RuntimeError("World Bank response was paginated; raise per_page")
        frame = pd.DataFrame(
            {"iso3": d["countryiso3code"], "year": int(d["date"]), column: d["value"]}
            for d in data
            if d["countryiso3code"]
        )
        frames.append(frame.set_index(["iso3", "year"]))
    out = pd.concat(frames, axis=1).reset_index().sort_values(["iso3", "year"])
    out.to_csv(RAW_DIR / "world_bank.csv", index=False)
    return out
