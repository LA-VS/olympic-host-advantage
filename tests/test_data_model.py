"""Checks on the committed raw data, reference tables and the built database."""

import pandas as pd
import pytest

from olympic_hosts.build import build, query
from olympic_hosts.paths import MEDAL_DIR, load_hosts, load_noc_map


@pytest.fixture(scope="module")
def db(tmp_path_factory):
    return build(tmp_path_factory.mktemp("db") / "test.duckdb")


def test_noc_windows_do_not_overlap():
    m = load_noc_map().sort_values(["noc", "from_year"])
    for _noc, g in m.groupby("noc"):
        assert (g["from_year"].iloc[1:].to_numpy() > g["to_year"].iloc[:-1].to_numpy()).all()


def test_every_host_matches_the_wikipedia_template_flag():
    hosts = load_hosts()
    for g in hosts[~hosts["future"]].itertuples():
        table = pd.read_csv(MEDAL_DIR / f"{g.games_id}.csv")
        assert table.loc[table["template_host"], "noc"].tolist() == [g.host_noc]


def test_every_medal_is_mapped_and_reconciles(db):
    assert query("SELECT count(*) FROM medal_result WHERE nation_id IS NULL", db).iloc[0, 0] == 0
    gaps = query(
        """SELECT p.games_id, sum(p.medals) AS nations, any_value(p.medals_awarded) AS awarded
           FROM analysis_panel p GROUP BY 1""",
        db,
    ).set_index("games_id")
    neutral = query(
        """SELECT games_id, sum(total) AS n FROM medal_result JOIN nation USING (nation_id)
           WHERE kind = 'neutral' GROUP BY 1""",
        db,
    ).set_index("games_id")["n"]
    diff = gaps["awarded"] - gaps["nations"]
    assert diff.equals(neutral.reindex(diff.index, fill_value=0).astype(diff.dtype))


def test_panel_has_one_row_per_nation_and_games(db):
    dupes = query("SELECT nation_id, games_id, count(*) n FROM analysis_panel GROUP BY ALL HAVING n > 1", db)
    assert dupes.empty


@pytest.mark.parametrize(
    ("nation", "games"),
    [("USA", "1980S"), ("RUS", "1984S"), ("GER", "1980S"), ("PRK", "1988S"), ("KEN", "1976S"), ("RSA", "1968S")],
)
def test_boycotts_and_bans_are_absent_not_zero(db, nation, games):
    rows = query(f"SELECT * FROM analysis_panel WHERE nation_id = '{nation}' AND games_id = '{games}'", db)
    assert rows.empty


def test_lineages_join_old_and_new_codes(db):
    russia = query("SELECT games_id FROM analysis_panel WHERE nation_id = 'RUS' AND season = 'Summer'", db)
    assert {"1960S", "1992S", "2016S", "2020S"} <= set(russia["games_id"])
    assert "2024S" not in set(russia["games_id"]), "Russia competed only as neutral athletes in 2024"


def test_every_hosting_is_flagged_once(db):
    hosts = query("SELECT games_id, nation_id FROM analysis_panel WHERE host = 1", db)
    assert len(hosts) == 35 and hosts["games_id"].is_unique
    nxt = query("SELECT games_id, nation_id FROM analysis_panel WHERE next_host = 1 AND games_id = '2024S'", db)
    assert nxt["nation_id"].tolist() == ["USA"]
