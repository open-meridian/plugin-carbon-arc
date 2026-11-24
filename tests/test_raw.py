"""Carbon Arc's answers kept as received, never the key, nothing kept where
the admin says so, and months moved past their window through the SDK."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from carbon_arc.carbon import VERSIONS_PATH, Fetched, entity_path, metadata_path
from carbon_arc.raw import RawStore, name_of

from conftest import AT, CARDS, KEY


def test_an_answer_is_kept_as_received(tmp_path: Path) -> None:
    store = RawStore(tmp_path)
    path = entity_path(900001)
    noted = {"carc_id": 900001, "ontology_version": "v2026.10.2"}
    key = store.keep(Fetched(path, 200, b'{"carc_id": 900001}', AT, {"x": KEY}), noted)
    assert key == "responses/2026-11/20261124T150000000000Z-entity-900001.json.gz"
    kept = store.read(key)
    assert kept is not None and kept["path"] == path and kept["status"] == 200
    assert kept["body"] == '{"carc_id": 900001}' and kept["noted"] == noted
    assert KEY not in str(kept)
    assert store.read("../outside.json.gz") is None
    assert name_of(metadata_path(CARDS)) == f"framework-{CARDS}-metadata"
    assert name_of(VERSIONS_PATH) == "ontology-versions"


def test_nothing_is_kept_when_the_admin_says_so(tmp_path: Path) -> None:
    store = RawStore(tmp_path)
    store.keeping = False
    assert store.keep(Fetched(VERSIONS_PATH, 200, b"{}", AT)) == ""
    assert store.keys() == []


class Plugin:
    def __init__(self) -> None:
        self.moved: list[tuple[str, str]] = []
        self.stored: list[Any] = []

    async def archive_unit(self, kind: str, unit: str, **_: Any) -> None:
        self.moved.append(("archived", unit))

    async def delete_unit(self, kind: str, unit: str, **_: Any) -> None:
        self.moved.append(("deleted", unit))


async def test_months_past_the_window_are_moved(tmp_path: Path) -> None:
    store = RawStore(tmp_path)
    store._given, store._root, store._granted = tmp_path, tmp_path, True
    old = datetime(2025, 1, 5, tzinfo=UTC)
    store.keep(Fetched(VERSIONS_PATH, 200, b"{}", old))
    store.keep(Fetched(VERSIONS_PATH, 200, b"{}", AT))
    plugin = Plugin()
    done = await store.tend(plugin, 30, "deleted", AT)  # type: ignore[arg-type]
    assert done["deleted"] == 1 and plugin.moved == [("deleted", "responses/2025-01")]
    assert plugin.stored[0].record_count == 2
    kept = await store.tend(Plugin(), 30, "kept", AT)  # type: ignore[arg-type]
    assert kept["kept"] == 1
