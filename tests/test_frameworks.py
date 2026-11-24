"""The purchased frameworks read, their companies resolved, what does not
resolve counted and never guessed, every want declined, and the key never
kept or shown."""

from __future__ import annotations

import asyncio
import gzip
import json
from pathlib import Path

from meridian.plugin.v1 import operations_pb2 as ops

from carbon_arc.carbon import SyntheticApi
from carbon_arc.frameworks import metadata_of, version_of

from conftest import AT, BRANDS, CARDS, KEY, NOT_BOUGHT, lake, role, want


def test_a_purchased_framework_is_read_and_its_companies_resolved(tmp_path: Path) -> None:
    work = role(tmp_path, frameworks=[CARDS])
    asyncio.run(work.check())
    held = work.status.frameworks[CARDS]
    assert held.state == "Held" and held.insight == "248" and held.aggregate == "sum"
    assert held.version == "v2026.10.2" and held.entities == [900001, 900002, 900003]
    entities = work.status.entities
    assert entities[900001].instrument_id == "INS-NORTHWIND"
    assert entities[900002].instrument_id == "INS-CONTOSO"
    assert work.status.read_at == AT and not work.status.error


def test_an_unresolved_company_is_counted_and_not_guessed(tmp_path: Path) -> None:
    recorder = lake()
    work = role(tmp_path, recorder, frameworks=[CARDS])
    asyncio.run(work.check())
    fabrikam = work.status.entities[900003]
    assert fabrikam.ticker == "FBKM" and not fabrikam.instrument_id
    assert fabrikam.miss == "no instrument holds its ticker"
    assert work.counts() == {"resolved": 2, "unresolved": 1, "other": 0}
    (missed,) = recorder.on("ReportMissingInstrument")
    assert [(i.scheme, i.value) for i in missed.identifiers] == [("ticker", "FBKM")]
    assert missed.source == "carbon-arc"


def test_a_brand_waits_for_its_kind_and_a_company_is_resolved_once(tmp_path: Path) -> None:
    recorder = lake()
    work = role(tmp_path, recorder, frameworks=[CARDS, BRANDS])
    asyncio.run(work.check())
    brand = work.status.entities[910001]
    assert brand.representation == "brand" and not brand.instrument_id
    assert "no such kind of subject yet" in brand.miss
    assert work.counts() == {"resolved": 2, "unresolved": 1, "other": 1}
    # Northwind, in both frameworks, is resolved once under the mapping version.
    tickers = [i.value for p in recorder.on("ResolveIdentifier") for i in p.identifiers]
    assert tickers.count("NWTX") == 1


def test_a_framework_not_bought_is_said_not_held(tmp_path: Path) -> None:
    work = role(tmp_path, frameworks=[NOT_BOUGHT, CARDS])
    asyncio.run(work.check())
    held = work.status.frameworks[NOT_BOUGHT]
    assert held.state == "Not held" and "404" in held.error
    assert work.status.read_at == AT  # the other framework was read


def test_a_missing_key_leaves_the_plugin_waiting(tmp_path: Path) -> None:
    api = SyntheticApi(lambda: AT)
    api.mode = "live"
    work = role(tmp_path, api=api, frameworks=[CARDS], waiting="is not set")
    asyncio.run(work.check())
    assert work.waiting == "is not set"
    assert api.asked == [] and not work.status.frameworks


def test_each_entity_is_kept_with_its_id_and_mapping_version(tmp_path: Path) -> None:
    work = role(tmp_path, frameworks=[CARDS])
    asyncio.run(work.check())
    key = work.status.entities[900001].raw
    document = work.raw.read(key)
    assert document is not None
    assert document["noted"] == {"carc_id": 900001, "ontology_version": "v2026.10.2"}
    assert json.loads(document["body"])["carc_id"] == 900001


def test_answers_not_kept_when_the_admin_says_so(tmp_path: Path) -> None:
    work = role(tmp_path, frameworks=[CARDS])
    work.raw.keeping = False
    asyncio.run(work.check())
    assert work.raw.keys() == []
    assert work.status.entities[900001].instrument_id == "INS-NORTHWIND"


def test_the_key_is_never_kept(tmp_path: Path) -> None:
    work = role(tmp_path, frameworks=[CARDS, BRANDS])
    asyncio.run(work.check())
    for path in tmp_path.rglob("*.json.gz"):
        assert KEY not in gzip.decompress(path.read_bytes()).decode()


def test_every_want_is_declined(tmp_path: Path) -> None:
    recorder = lake()
    work = role(tmp_path, recorder)
    asyncio.run(work.on_observations_wanted(want("w-1", ["INS-NORTHWIND"])))
    (declined,) = recorder.on("DeclineWant")
    assert declined.want_id == "w-1"
    assert [s.entity_id for s in declined.subjects] == ["INS-NORTHWIND"]
    assert declined.reason == ops.UNANSWERED_REASON_NOT_COVERED


def test_the_shapes_read_defensively() -> None:
    read = metadata_of({"entities": {"carc_id": "7", "representation": "Ticker"}, "insight": 9})
    assert [(e.carc_id, e.representation) for e in read.entities] == [(7, "ticker")]
    assert read.insight == "9" and read.version == ""
    assert metadata_of(None).entities == ()
    assert version_of({"versions": [{"version": "v2026.09.1"}]}) == "v2026.09.1"
    assert version_of(["v1", "v0"]) == "v1" and version_of(None) == ""
