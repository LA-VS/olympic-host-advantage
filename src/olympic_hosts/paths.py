"""Repo paths and the hand curated reference tables."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = REPO_ROOT / "data" / "raw"
MEDAL_DIR = RAW_DIR / "medal_tables"
REFERENCE_DIR = REPO_ROOT / "data" / "reference"
PROCESSED_DIR = REPO_ROOT / "data" / "processed"
DB_PATH = PROCESSED_DIR / "olympics.duckdb"
SQL_DIR = REPO_ROOT / "sql"


def load_hosts() -> pd.DataFrame:
    hosts = pd.read_csv(REFERENCE_DIR / "hosts.csv", keep_default_na=False)
    hosts["future"] = hosts["note"].str.startswith("Future Games")
    return hosts


def load_noc_map() -> pd.DataFrame:
    return pd.read_csv(REFERENCE_DIR / "noc_map.csv", keep_default_na=False)
