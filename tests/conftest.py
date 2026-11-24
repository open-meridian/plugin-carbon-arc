"""Shared stand-ins: Carbon Arc's responses committed with the plugin, a
fixed clock, the deployment's instruments, and the lake as the sidecar
answers it."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from meridian.plugin.v1 import operations_pb2 as ops
from meridian.receive import Heard
from meridian.roles.data.testing import Lake
from meridian.suites import Recorder

from carbon_arc.carbon import SyntheticApi
from carbon_arc.frameworks import Frameworks
from carbon_arc.raw import RawStore

#: 15:00 UTC on Tuesday 24 November 2026.
AT = datetime(2026, 11, 24, 15, 0, tzinfo=UTC)
INSTANCE = "carbon-arc"
#: The key the tests set: a placeholder, never a real key.
KEY = "test-placeholder-not-a-real-key"

#: The two fictitious frameworks the committed responses hold.
CARDS = "3f2b8c1e-5d4a-4b6e-9f10-2a7c8d9e0f11"  # three companies as tickers
BRANDS = "9a8b7c6d-5e4f-4a3b-8c2d-1e0f9a8b7c6d"  # a brand, and a company again
#: A framework the firm has not bought: Carbon Arc holds none for its key.
NOT_BOUGHT = "00000000-0000-4000-8000-000000000000"

#: The deployment's instrument for each ticker it holds; FBKM it does not.
INSTRUMENTS = {"NWTX": "INS-NORTHWIND", "CTSO": "INS-CONTOSO"}


def instruments(recorder: Recorder, held: dict[str, str] | None = None) -> dict[str, str]:
    """The deployment's instruments, answering ResolveIdentifier by ticker,
    as the platform does: not found where none holds it."""
    records = dict(INSTRUMENTS if held is None else held)

    def resolve(params: ops.ResolveIdentifierParams) -> ops.ResolveIdentifierResult:
        for identifier in params.identifiers:
            if identifier.scheme == "ticker" and identifier.value in records:
                return ops.ResolveIdentifierResult(
                    found=True, instrument_id=records[identifier.value]
                )
        return ops.ResolveIdentifierResult(found=False, miss_reason=ops.MISS_REASON_NOT_FOUND)

    recorder.answer("ResolveIdentifier", resolve)
    return records


def lake(held: dict[str, str] | None = None) -> Lake:
    """The lake as a test stands it in, holding the instruments."""
    recorder = Lake(INSTANCE)
    instruments(recorder, held)
    return recorder


def role(
    tmp: Path,
    recorder: Recorder | None = None,
    *,
    frameworks: Sequence[str] = (),
    api: Any = None,
    at: datetime = AT,
    waiting: str = "",
) -> Frameworks:
    """The plugin's data role class on Carbon Arc's committed responses, at
    `at`, bound to the lake."""
    held = recorder if recorder is not None else lake()
    return held.bind(
        Frameworks(
            api or SyntheticApi(lambda: at),
            RawStore(tmp),
            now=lambda: at,
            frameworks=frameworks,
            waiting=waiting,
        )
    )


def want(want_id: str, subjects: list[str], *, standing: bool = False) -> Heard:  # type: ignore[type-arg]
    return Heard(
        row="ObservationsWanted",
        message=ops.ObservationsWantedEvent(
            want_id=want_id,
            dataset=f"{INSTANCE}:carbon_arc_panels",
            subjects=[ops.SubjectRef(entity_id=s) for s in subjects],
            business_date="2026-11-20",
            standing=standing,
        ),
    )
