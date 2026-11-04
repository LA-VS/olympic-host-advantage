import pytest

from olympic_hosts.fetch import parse_medal_template, parse_participants

MEDAL_PAGE = """
Intro text {{Infobox|x=1}}
{{Medals table
 | caption = 1960 table<ref>{{cite web |title=IOC}}</ref>
 | host    = ITA
 | gold_URS = 43 | silver_URS = 29 | bronze_URS = 31
 | gold_ITA = 13 | silver_ITA = 10 | bronze_ITA = 13 | host_ITA = yes
 | gold_NZL = 2 | silver_NZL = 0 | bronze_NZL = 1
 | bronze_ZZZ = 4
}}
{{Medals table
 | gold_XXX = 99
}}
"""


def test_parse_medal_template_reads_counts_and_host():
    df = parse_medal_template(MEDAL_PAGE).set_index("noc")
    assert df.loc["URS", ["gold", "silver", "bronze"]].tolist() == [43, 29, 31]
    assert df.loc["ZZZ", ["gold", "silver", "bronze"]].tolist() == [0, 0, 4]
    assert df["template_host"].sum() == 1 and df.loc["ITA", "template_host"]


def test_parse_medal_template_stops_at_the_first_template():
    assert "XXX" not in set(parse_medal_template(MEDAL_PAGE)["noc"])


def test_parse_medal_template_requires_a_template():
    with pytest.raises(ValueError, match="No"):
        parse_medal_template("no table here")


def flags(codes):
    return "\n".join(f"* {{{{flagIOCteam|{c}|1960 Summer}}}}" for c in codes)


def test_parse_participants_reads_subsection_and_stops_at_next_section():
    codes = ["USA", "URS", "ITA", "GBR", "FRA", "JPN", "AUS", "CAN", "SWE", "HUN", "rom"]
    page = (
        f"== History ==\n{flags(['XXX'] * 12)}\n"
        f"== Participants ==\n=== Participating nations ===\n{flags(codes)}\n"
        f"== Venues ==\n{flags(['YYY'])}"
    )
    result = parse_participants(page)
    assert result == sorted(c.upper() for c in codes)


def test_parse_participants_returns_none_without_a_list():
    assert parse_participants("== Participating NOCs ==\nAll 204 NOCs took part.\n== Next ==") is None
