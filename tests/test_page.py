"""The three pages under Manage, and their read tools: what each shows, to
whom, that a tool answers what its page shows, that a missing key is named
and never shown, and that no page offers a purchase."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from meridian.testing import PageClient

from carbon_arc import page as page_module
from carbon_arc.carbon import SyntheticApi
from carbon_arc.page import CONNECTION, DATASETS, FRAMEWORKS, figures, hold, pages

from conftest import AT, BRANDS, CARDS, KEY, NOT_BOUGHT, lake, role, want


@pytest.fixture
def client(tmp_path: Path) -> PageClient:
    work = role(tmp_path, frameworks=[CARDS, BRANDS, NOT_BOUGHT])

    async def run() -> None:
        await work.check()
        await work.on_observations_wanted(want("w-day", ["INS-NORTHWIND"]))

    asyncio.run(run())
    hold(work)
    return PageClient(pages)


def test_each_page_is_managed_alone(client: PageClient) -> None:
    served = {(r.page.path, r.level): r.response.status for r in client.every_page()}
    assert served == {
        (path, level): 200 if level == "admin" else 403
        for path in (CONNECTION, DATASETS, FRAMEWORKS)
        for level in ("admin", "write", "read")
    }


def test_connection_says_how_carbon_arc_is_reached(client: PageClient) -> None:
    text = client.get(CONNECTION, "admin").text
    order = ["<h2>Key</h2>", "<tr data-frameworks>", "<h2>Limits"]
    assert [text.index(t) for t in order] == sorted(text.index(t) for t in order)
    assert "<h2>Sessions</h2>" not in text and "Does not stream" in text
    assert "3 kept current, read only" in text
    assert "<tr data-pace>" in text and "10 requests a minute at most" in text
    assert 'href="/.meridian/ui/0.13.0/meridian.css"' in text


def test_datasets_says_why_none_is_served(client: PageClient) -> None:
    text = client.get(DATASETS, "admin").text
    assert "No dataset yet" in text and "<h2>Terms</h2>" in text
    assert "never prices or buys" in text
    read = client.call_tool("read_datasets").data
    assert read["served"] == [] and read["wants"][0]["want_id"] == "w-day"
    assert read["wants"][0]["declined"] == 1


def test_frameworks_lists_each_and_its_entities(client: PageClient) -> None:
    text = client.get(FRAMEWORKS, "admin").text
    assert text.count("<tr data-framework=") == 3 and text.count("<tr data-entity=") == 4
    assert "INS-NORTHWIND" in text and "no instrument holds its ticker" in text
    assert "Not held" in text and "never prices or buys" in text
    read = client.call_tool("read_purchased_frameworks").data
    assert (read["resolved"], read["unresolved"], read["other_kinds"]) == (2, 1, 1)
    assert [f["state"] for f in read["frameworks"]] == ["Held", "Held", "Not held"]
    assert read["version"] == "v2026.10.2"


def test_the_tools_are_reads_alone(client: PageClient) -> None:
    assert {t.name for t in pages.tools} == {
        "read_connection", "read_datasets", "read_purchased_frameworks"
    }  # fmt: skip
    data = client.call_tool("read_connection").data
    assert data["mode"] == "Sample data" and data["sessions"] is None
    assert data["frameworks_kept"] == 3 and data["per_minute"] == 10 and data["keeping"]


def test_a_missing_key_is_named(tmp_path: Path) -> None:
    api = SyntheticApi(lambda: AT)
    api.mode = "live"
    work = role(tmp_path, lake(), api=api, waiting="is not set")
    hold(work)
    client = PageClient(pages)
    text = client.get(CONNECTION, "admin").text
    assert "Waiting: carbon_arc_api_key is not set" in text
    data = client.call_tool("read_connection").data
    assert data["mode"] == "No key" and data["waiting"] == "carbon_arc_api_key is not set"
    assert data["credentials"] == [{"label": "API key", "set": False}]
    said = figures(work.status, work)
    assert said[0].value == "Waiting for carbon_arc_api_key" and said[0].state == "warn"


def test_the_key_is_never_shown(tmp_path: Path) -> None:
    work = role(tmp_path, frameworks=[CARDS])
    asyncio.run(work.check())
    hold(work)
    client = PageClient(pages)
    for path in (CONNECTION, DATASETS, FRAMEWORKS):
        assert KEY not in client.get(path, "admin").text


def test_before_the_first_check() -> None:
    page_module._held.clear()
    client = PageClient(pages)
    assert "Waiting for carbon_arc_api_key" in client.get(CONNECTION, "admin").text
    assert "No frameworks read yet" in client.get(FRAMEWORKS, "admin").text
    assert "No wants yet" in client.get(DATASETS, "admin").text


def test_the_figures_are_the_data_roles_then_its_own(client: PageClient) -> None:
    work = page_module._held["frameworks"]
    said = figures(work.status, work)
    assert [f.label for f in said] == [
        "Connection",
        "Entitled at the vendor",
        "Stream",
        "Rate use",
        "Companies resolved",
    ]
    assert said[3].value == "at most 10 of 100 a minute"
    assert said[4].value == "2 of 3" and said[4].state == "warn"
