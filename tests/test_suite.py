"""The data suite (meridian.suites), each case this version presents mapped
to the plugin's own work on the responses committed with it: a company
whose ticker resolves to no instrument reported missing, a subject declined,
a standing want withdrawn, and its datasets' licences read.

This version records nothing in the lake: a Carbon Arc panel is a value over
time for a company, and the contract has no row kind for one yet. So every
case about a kind of row it would record is named here as not presented,
with why; the panels' cases come with their dataset.

The cases every suite holds that the SDK answers (a replacement, the
template catalogue, an event group heard) are the SDK's.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from pathlib import Path

from meridian.plugin.v1 import operations_pb2 as ops
from meridian.roles.data.testing import RATES_CASES, RATES_NOT_PRESENTED
from meridian.suites import ANSWERED_BY_SDK, Recorder, run

from conftest import CARDS, INSTANCE, instruments, role, want

PRESENTED = (
    "an-asset-that-does-not-resolve",
    "a-subject-declined",
    "a-standing-want-withdrawn",
    "reads-its-datasets-licences",
)
#: Why this version records none of a kind: no dataset until the platform
#: has a row kind for a panel's value over time.
NONE_YET = "it records nothing in this version: a panel waits on a row kind for a value over time"
NOT_PRESENTED = {
    **{c: NONE_YET for c in RATES_NOT_PRESENTED if c not in PRESENTED},
    **{c: NONE_YET for c in RATES_CASES},
    "records-a-datasets-liveness": "it streams nothing: it reads Carbon Arc every hour",
    "reads-a-calendar": "it declares no dataset, so no calendar",
    "asks-for-a-settlement-date": "a panel settles nothing",
    "reports-its-feed-delay": NONE_YET,
    "records-a-derived-series": "Carbon Arc's own derived insights and scores are not carried",
    "a-filing-recorded": "Carbon Arc publishes no filings",
    "resolves-a-filer": "Carbon Arc publishes no filings",
    "a-fact-restated": "Carbon Arc publishes no filings",
    "a-fact-confirmed": "Carbon Arc publishes no filings",
    "a-complete-holdings-report": "Carbon Arc publishes no holdings",
    "a-cusip-used-as-key": "Carbon Arc publishes no holdings",
    "a-stake-crossed": "Carbon Arc publishes no holdings",
    "a-dividend-declared": "Carbon Arc publishes no corporate actions",
    "a-rating-action": "Carbon Arc publishes no ratings, and none is carried",
}


def producers(tmp: Path) -> dict[str, Callable[[Recorder], Awaitable[None]]]:
    async def unresolved(recorder: Recorder) -> None:
        # Carbon Arc's ticker names no exchange, and Fabrikam's, FBKM, meets
        # two of the deployment's instruments: reported missing as
        # ambiguous, counted, never guessed.
        instruments(recorder)

        def resolve(params: ops.ResolveIdentifierParams) -> ops.ResolveIdentifierResult:
            if any(i.value == "FBKM" for i in params.identifiers):
                return ops.ResolveIdentifierResult(miss_reason=ops.MISS_REASON_AMBIGUOUS)
            return ops.ResolveIdentifierResult(found=True, instrument_id="INS-HELD")

        recorder.answer("ResolveIdentifier", resolve)
        work = role(tmp, recorder, frameworks=[CARDS])
        await work.check()
        assert work.counts()["unresolved"] == 1
        assert work.status.entities[900003].miss == "two instruments hold its ticker"

    async def declined(recorder: Recorder) -> None:
        work = role(tmp, recorder)
        asked = want("w-2", ["INS-NORTHWIND"]).message
        recorder.answer("ObservationsWanted", lambda _: asked)
        await recorder.hear(work, "ObservationsWanted")

    async def withdrawn(recorder: Recorder) -> None:
        work = role(tmp, recorder)
        recorder.answer(
            "WantWithdrawn",
            lambda _: ops.WantWithdrawnEvent(
                want_id="w-standing", dataset=f"{INSTANCE}:carbon_arc_panels"
            ),
        )
        await recorder.hear(work, "WantWithdrawn")

    async def licences(recorder: Recorder) -> None:
        recorder.answer("ListDatasets", lambda _: ops.ListDatasetsResult())
        work = role(tmp, recorder)
        await work.wants.read_licences()
        assert work.wants.licensed == set()

    return {
        "an-asset-that-does-not-resolve": unresolved,
        "a-subject-declined": declined,
        "a-standing-want-withdrawn": withdrawn,
        "reads-its-datasets-licences": licences,
    }


def test_the_data_suite_passes(tmp_path: Path) -> None:
    report = run("data", producers(tmp_path), not_presented=NOT_PRESENTED, instance_id=INSTANCE)
    assert report.passed, report.failures
    assert sorted(report.not_presented) == sorted(NOT_PRESENTED)
    assert sorted(report.passed_cases) == sorted([*PRESENTED, *ANSWERED_BY_SDK])
    assert report.answered_by_sdk == list(ANSWERED_BY_SDK)
