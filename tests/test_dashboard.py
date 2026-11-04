"""Checks on the data behind the HTML dashboard and on the page it writes."""

import json

import pytest

from olympic_hosts.build import build
from olympic_hosts.dashboard import PLACEHOLDER, dashboard_data, render
from olympic_hosts.paths import REPO_ROOT


@pytest.fixture(scope="module")
def data(tmp_path_factory):
    return dashboard_data(build(tmp_path_factory.mktemp("db") / "test.duckdb"))


def test_one_row_per_hosting_matching_the_readme(data):
    hostings = data["hostings"]
    assert len(hostings) == 35
    assert len({h["games_id"] for h in hostings}) == 35
    assert sum(h["host_share"] > h["usual_share"] for h in hostings) == 29


def test_event_rows_belong_to_hostings(data):
    ids = {h["games_id"] for h in data["hostings"]}
    assert {e["host_games"] for e in data["events"]} <= ids
    assert {e["rel"] for e in data["events"]} <= set(range(-3, 4))


def test_render_embeds_valid_json(data):
    page = render(data)
    assert PLACEHOLDER not in page
    start = page.index("const DATA = ") + len("const DATA = ")
    end = page.index(";\n", start)
    assert json.loads(page[start:end].replace("<\\/", "</")) == json.loads(json.dumps(data, default=float))


def test_committed_dashboard_is_up_to_date(data):
    assert (REPO_ROOT / "docs" / "index.html").read_text(encoding="utf-8") == render(data)
