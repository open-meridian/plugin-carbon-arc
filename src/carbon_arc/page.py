"""The plugin's pages, under Manage alone: the data role's common pages,
Connection and Datasets, and Carbon Arc's Frameworks, each also a read tool
for agents on the deployment's MCP (`read_connection`, `read_datasets`,
`read_purchased_frameworks`). Each record is the role's
(`meridian.roles.data`), extended with Carbon Arc's fields; each template is
the role's, with Carbon Arc's nuance at its blocks.

A data plugin shows its connectivity, its datasets and how its subjects
resolve, and no data:

- **Connection** (`/`): the mode (Live, Sample data or No key while the key
  is unset), whether the key is set (never its value), Carbon Arc's limits
  and the pace kept, whether answers are kept; it does not stream.
- **Datasets** (`/datasets`): none served in this version, with why, and
  Carbon Arc's terms in words.
- **Frameworks** (`/frameworks`): each purchased framework the firm named,
  its state, insight and mapping version, and each entity it measures with
  the instrument it resolved to or why none.

None shows a panel's values, and none buys, prices or changes anything:
settings change through core's tools.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import meridian
from meridian.roles import data

from . import records
from .carbon import HOST
from .declared import CATALOGUE, TERMS
from .frameworks import Frameworks, Status
from .limits import MOST_PER_HOUR, MOST_PER_MINUTE
from .settings import API_KEY

TITLE = "Carbon Arc"
#: The kit these pages are built on.
KIT = "0.13.0"

pages = meridian.Pages(TITLE, templates=Path(__file__).parent / "templates", kit=KIT)

CONNECTION = "/"
DATASETS = "/datasets"
FRAMEWORKS = "/frameworks"

#: Why no dataset is served in this version, as Datasets says it.
NOT_YET = (
    "No dataset yet. Carbon Arc's panels are values over time for a company, and the platform "
    "has no kind of record for such a value yet. The panels' dataset comes with it; until "
    "then nothing is recorded in the lake, and every want is declined."
)

_held: dict[str, Frameworks] = {}


def hold(frameworks: Frameworks) -> None:
    """The role class the pages read, once the plugin has registered."""
    _held["frameworks"] = frameworks


def _status() -> tuple[Status, Frameworks | None]:
    held = _held.get("frameworks")
    return (held.status if held is not None else Status(waiting="is not set"), held)


def _iso(moment: datetime | None) -> str:
    return moment.astimezone(UTC).isoformat(timespec="seconds") if moment else ""


def _waiting(status: Status) -> str:
    return "" if status.mode == "synthetic" else status.waiting


def _mode(status: Status) -> str:
    if status.mode == "synthetic":
        return "Sample data"
    return "No key" if status.waiting else "Live"


def _state(status: Status, held: Frameworks | None) -> tuple[str, str, str]:
    """The head's status: its state, what it means, and its detail."""
    if _waiting(status):
        return "warn", f"Waiting for {API_KEY}", f"{API_KEY} {_waiting(status)}"
    if status.error and status.read_at is None:
        return "error", "Not answering", status.error
    if status.error:
        return "warn", "Answering", status.error
    if held is not None and not held.frameworks:
        return "ok", "No frameworks named", "Name the purchased frameworks in Settings"
    if status.read_at is None:
        return "busy", "Reading Carbon Arc", ""
    if status.unread:
        return "warn", "A framework row is not an ID", ", ".join(status.unread)
    unresolved = held.counts()["unresolved"] if held is not None else 0
    if unresolved:
        plural = "company" if unresolved == 1 else "companies"
        return "warn", f"{unresolved} {plural} not resolved", "See Frameworks"
    return "ok", "Sample data" if status.mode == "synthetic" else "Answering", ""


def connection_read(status: Status, held: Frameworks | None) -> records.ConnectionRead:
    state, said, _ = _state(status, held)
    keeping = held.raw.keeping if held is not None else True
    kept = held.raw.keys() if held is not None else []
    window = ""
    if held is not None and not keeping:
        window = "none: answers are read and not kept, as carbon_arc_keep_responses says"
    elif held is not None and held.raw.granted:
        window = "in the storage the deployment grants, as its responses settings say"
    elif held is not None:
        window = "in a directory of the plugin's own: this deployment grants no storage"
    rate = held.api.limiter.rate if held is not None else 0
    return records.ConnectionRead(
        mode=_mode(status),
        credentials=[data.Credential("API key", status.waiting != "is not set")],
        entitled_at_vendor=(
            "" if _waiting(status) else "The frameworks your firm has bought, read only"
        ),
        limit=(
            f"Carbon Arc's {MOST_PER_MINUTE} requests a minute and {MOST_PER_HOUR} an hour; "
            f"this plugin asks one at a time, at most {rate} a minute, and pauses after a 429"
        ),
        calls=status.fetches,
        rate_limited=held.api.limiter.refused if held is not None else 0,
        last_call_at=_iso(status.checked_at),
        last_error=status.error,
        sessions=None,
        state=state,
        said=said,
        source=(
            "The responses committed with the plugin"
            if status.mode == "synthetic"
            else f"{HOST}, the purchased frameworks' metadata and the entity mapping"
        ),
        checked_at=_iso(status.checked_at),
        waiting=f"{API_KEY} {_waiting(status)}" if _waiting(status) else "",
        per_minute=rate,
        frameworks_kept=len(held.frameworks) if held is not None else 0,
        keeping=keeping,
        responses_kept=len(kept),
        kept_for=window,
    )


def datasets_read(held: Frameworks | None) -> records.DatasetsRead:
    instance = held.plugin.identity.instance_id if held is not None else "carbon-arc"
    return records.DatasetsRead(
        served=data.served(CATALOGUE, instance, held.wants if held is not None else None, ""),
        wants=list(data.want_rows(held.wants)) if held is not None else [],
        reads_instruments=True,
        not_yet=NOT_YET,
        terms=TERMS,
    )


def frameworks_read(status: Status, held: Frameworks | None) -> records.FrameworksRead:
    counts = held.counts() if held is not None else {"resolved": 0, "unresolved": 0, "other": 0}
    named = held.frameworks if held is not None else ()
    return records.FrameworksRead(
        frameworks=[
            records.FrameworkRead(
                framework_id=f.framework_id,
                state=f.state,
                insight=f.insight,
                aggregate=f.aggregate,
                version=f.version,
                entities=list(f.entities),
                read_at=_iso(f.read_at),
                last_error=f.error,
            )
            for f in (status.frameworks.get(i) for i in named)
            if f is not None
        ],
        entities=[
            records.EntityRead(
                carc_id=e.carc_id,
                representation=e.representation,
                name=e.name,
                ticker=e.ticker,
                version=e.version,
                instrument_id=e.instrument_id,
                miss=e.miss,
            )
            for _, e in sorted(status.entities.items())
        ],
        resolved=counts["resolved"],
        unresolved=counts["unresolved"],
        other_kinds=counts["other"],
        unread=list(status.unread),
        version=status.version,
    )


def figures(status: Status, held: Frameworks | None) -> list[meridian.Figure]:
    """The data role's figures, in its order (`meridian.roles.data`), then
    the plugin's own: the companies resolved."""
    state, said, why = _state(status, held)
    if status.mode == "synthetic" and state == "ok":
        connection: Any = "Sample data"
    elif _waiting(status) or said == "Not answering":
        connection = meridian.Figure(
            "", said, state="error" if state == "error" else "warn", why=why[:200]
        )
    else:
        connection = meridian.Figure(
            "", "Answering", state="warn" if status.error else None, why=status.error[:200]
        )
    rate = held.api.limiter.rate if held is not None else 0
    counts = held.counts() if held is not None else {"resolved": 0, "unresolved": 0}
    return [
        *data.figures(
            connection=connection,
            entitled_at_vendor="0 of 0 datasets: none in this version",
            stream="Does not stream",
            rate_use=f"at most {rate} of {MOST_PER_MINUTE} a minute",
        ),
        meridian.Figure(
            "Companies resolved",
            f"{counts['resolved']} of {counts['resolved'] + counts['unresolved']}",
            state="warn" if counts["unresolved"] else None,
            why=f"{counts['unresolved']} not resolved" if counts["unresolved"] else "",
        ),
    ]


def _moment(value: str) -> str:
    """An ISO moment as a person reads it, to the minute in UTC."""
    if not value:
        return ""
    return datetime.fromisoformat(value).astimezone(UTC).strftime("%Y-%m-%d %H:%M UTC")


pages.environment.filters["moment"] = _moment


@pages.page(
    CONNECTION,
    "Connection",
    levels="admin",
    answers=records.ConnectionRead,
    name="read_connection",
    description=(
        "How this plugin reaches Carbon Arc, as every data plugin's Connection answers it: the "
        "mode (Live, Sample data, or No key while carbon_arc_api_key is unset), whether the key "
        "is set (never its value), Carbon Arc's limits of 100 requests a minute and 1,000 an "
        "hour and the pace kept, the requests made and refused, the last call and why it "
        "failed if it did; it does not stream. Then Carbon Arc's own: the purchased frameworks "
        "kept current, and whether and where its answers are kept. No panel's values."
    ),
)
async def connection(request: meridian.Request) -> meridian.Response:
    status, held = _status()
    read = connection_read(status, held)
    return pages.answer("connection.html", read, detail=_state(status, held)[2])


@pages.page(
    DATASETS,
    "Datasets",
    levels="admin",
    answers=records.DatasetsRead,
    name="read_datasets",
    description=(
        "What this plugin serves the lake, as every data plugin's Datasets answers it: no "
        "dataset in this version, with why (Carbon Arc's panels wait on a kind of record for a "
        "value over time), the wants it declined, and Carbon Arc's terms in words."
    ),
)
async def datasets(request: meridian.Request) -> meridian.Response:
    status, held = _status()
    read = datasets_read(held)
    return pages.answer(
        "datasets.html", read, state=_state(status, held), checked_at=_iso(status.checked_at)
    )


@pages.page(
    FRAMEWORKS,
    "Frameworks",
    levels="admin",
    answers=records.FrameworksRead,
    name="read_purchased_frameworks",
    description=(
        "The Carbon Arc frameworks your firm has bought and named in carbon_arc_frameworks: "
        "each one's state (Held, Not held, Failing), insight, aggregation and entity-mapping "
        "version, and each entity it measures by Carbon Arc's ID, with its ticker and the "
        "deployment's instrument, or why none (not resolved, or a brand, location, person or "
        "digital property, which the platform does not hold yet). Read only: it never prices "
        "or buys. No panel's values."
    ),
)
async def frameworks(request: meridian.Request) -> meridian.Response:
    status, held = _status()
    read = frameworks_read(status, held)
    return pages.answer(
        "frameworks.html", read, state=_state(status, held), checked_at=_iso(status.checked_at)
    )
