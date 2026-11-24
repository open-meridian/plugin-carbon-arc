"""Carbon Arc's purchased frameworks, read with the firm's own key, and the
companies they measure resolved to the deployment's instruments.

**What a framework is.** Carbon Arc sells data per framework: an insight
(what is measured, such as card spend) over entities (a company, a brand, a
location), with filters and an aggregation, priced before it is bought and
then read by its ID (https://docs.carbonarc.ai/developers/querying-data-for-devs/explorer-api).
The firm names the frameworks it has bought in `carbon_arc_frameworks`; the
plugin reads each one's metadata, and never prices, quotes or buys one
(carbon.py allows reads alone).

**Entities.** Carbon Arc resolves everything to its own entities, each with a
`carc_id` and representations such as a ticker, under a mapping it versions
monthly (https://docs.carbonarc.ai/reference/ontology-overview/ontology-versions).
An entity a framework measures as a company or a ticker is read as a ticker
(`/v2/ontology/entities/<carc_id>?entity_representation=ticker`) and that
ticker resolved to the deployment's instrument. One that does not resolve is
reported missing and counted, never guessed. Each entity's answer is kept
with the mapping version it was read under noted beside it, so a resolution
can be traced to Carbon Arc's own ID and mapping. An entity Carbon Arc
measures as a brand, a location, a person or a digital property is counted
apart: the platform has no such kind of subject yet.

**Nothing is recorded in the lake in this version.** A panel's values over
time need a row kind the contract does not have yet (declared.py). Every
want the lake hands this plugin is declined, `not_covered`.

The class is the plugin's data role class, its acts made on itself:
registered with `meridian.run`, or bound to the suite's `Recorder` in its
tests.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import meridian
from meridian.plugin.v1 import operations_pb2 as ops
from meridian.roles import data

from . import carbon
from .declared import KEYS
from .raw import RawStore

log = logging.getLogger("carbon_arc")

#: The source this plugin names on what it reports missing.
SOURCE = "carbon-arc"
#: The representations of a listed company: read as a ticker.
COMPANY = ("ticker", "company")
#: How long the mapping's versions are kept before they are read again, in seconds.
VERSIONS_SECONDS = 86_400


def _ns(moment: datetime) -> int:
    return int(moment.timestamp() * 1_000_000) * 1000


@dataclass(frozen=True)
class Entity:
    """One of Carbon Arc's entities as a framework names it."""

    carc_id: int
    representation: str


@dataclass(frozen=True)
class Metadata:
    """A purchased framework's metadata, as far as the plugin reads it."""

    entities: tuple[Entity, ...]
    insight: str
    aggregate: str
    version: str


def _text(value: object) -> str:
    return "" if value is None else str(value).strip()


def metadata_of(answer: object) -> Metadata:
    """A framework's metadata: its entities, insight, aggregation and the
    mapping version it names, from the framework as Carbon Arc's SDK builds
    it (`entities`, `insight`, `filters`, `aggregate`), whether at the top
    or under `framework`. What does not read is left out."""
    held: Mapping[str, Any] = answer if isinstance(answer, Mapping) else {}
    inner = held.get("framework")
    body: Mapping[str, Any] = inner if isinstance(inner, Mapping) else held
    named = body.get("entities")
    rows = named if isinstance(named, list) else [named] if isinstance(named, Mapping) else []
    entities = []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        try:
            carc_id = int(str(row.get("carc_id", "")).strip())
        except ValueError:
            continue
        entities.append(Entity(carc_id, _text(row.get("representation")).lower()))
    insight = body.get("insight")
    if isinstance(insight, Mapping):
        insight = insight.get("insight_id")
    version = held.get("ontology_version") or body.get("ontology_version") or ""
    return Metadata(tuple(entities), _text(insight), _text(body.get("aggregate")), _text(version))


def version_of(answer: object) -> str:
    """The mapping's current version from Carbon Arc's list of them: its
    `latest`, or the first version listed; empty where none reads."""
    if isinstance(answer, Mapping):
        if answer.get("latest"):
            return _text(answer["latest"])
        answer = answer.get("versions")
    if isinstance(answer, list) and answer:
        first = answer[0]
        return _text(first.get("version") if isinstance(first, Mapping) else first)
    return ""


@dataclass
class EntityState:
    """One entity as the plugin last resolved it, for the Frameworks page."""

    carc_id: int
    representation: str
    name: str = ""
    ticker: str = ""
    instrument_id: str = ""
    #: Why it is not an instrument: not resolved, or a kind not yet held.
    miss: str = ""
    version: str = ""
    raw: str = ""


@dataclass
class FrameworkState:
    """One purchased framework as the plugin last read it."""

    framework_id: str
    #: Held, Not held (Carbon Arc answers none for this key), or Failing.
    state: str = "Not read yet"
    insight: str = ""
    aggregate: str = ""
    version: str = ""
    entities: list[int] = field(default_factory=list)
    read_at: datetime | None = None
    error: str = ""


@dataclass
class Status:
    """What the plugin last did, for its pages; held in memory, lost on a
    restart and read again by the first check."""

    mode: str = "live"
    #: Why the key will not do, while it will not; empty once it will.
    waiting: str = ""
    started_at: datetime | None = None
    checked_at: datetime | None = None
    read_at: datetime | None = None
    error: str = ""
    fetches: int = 0
    version: str = ""
    versions_at: datetime | None = None
    frameworks: dict[str, FrameworkState] = field(default_factory=dict)
    entities: dict[int, EntityState] = field(default_factory=dict)
    #: Each table row that is not a framework ID.
    unread: tuple[str, ...] = ()


class Failed(Exception):  # noqa: N818 - what an answer was
    """Carbon Arc refused or did not answer; its words."""

    def __init__(self, said: str, status: int = 0) -> None:
        super().__init__(said)
        self.status = status


class Frameworks(data.Role):
    """The plugin's data role class: reading the purchased frameworks,
    resolving their companies, and declining every want."""

    def __init__(
        self,
        api: carbon.Api,
        raw: RawStore,
        now: Callable[[], datetime] = carbon.utc_now,
        frameworks: Sequence[str] = (),
        waiting: str = "",
    ) -> None:
        self.api = api
        self.raw = raw
        self.now = now
        self.frameworks = tuple(frameworks)
        self.wants = data.Wants(self, KEYS, clock_ns=lambda: _ns(self.now()))
        self.status = Status(mode=api.mode, waiting=waiting, started_at=now())
        self._resolved: dict[tuple[int, str], EntityState] = {}

    def use(
        self,
        api: carbon.Api,
        frameworks: Sequence[str],
        waiting: str,
        unread: Sequence[str] = (),
    ) -> None:
        """Read from `api` from now on, keeping `frameworks` current: the
        settings changed."""
        if api.mode != self.api.mode:
            self._resolved.clear()
            self.status.entities.clear()
        self.api = api
        self.frameworks = tuple(frameworks)
        self.status.mode = api.mode
        self.status.waiting = waiting
        self.status.unread = tuple(unread)
        for gone in set(self.status.frameworks) - set(self.frameworks):
            del self.status.frameworks[gone]

    @property
    def waiting(self) -> str:
        """Why Carbon Arc is not asked: the key's problem, live; empty where
        it may be asked."""
        return "" if self.api.mode == "synthetic" else self.status.waiting

    # ── Asking Carbon Arc ───────────────────────────────────────────────

    async def ask(self, path: str, noted: dict[str, Any] | None = None) -> tuple[Any, str]:
        """One answer's JSON and its key in storage (empty where answers are
        not kept); Failed where Carbon Arc refused or did not answer."""
        try:
            fetched = await self.api.get(path)
        except carbon.Unreachable as failed:
            raise Failed(str(failed)) from failed
        self.status.fetches += 1
        key = self.raw.keep(fetched, noted)
        if fetched.status != 200:
            raise Failed(fetched.error, fetched.status)
        return fetched.json(), key

    async def version(self) -> str:
        """The mapping's current version, read once a day."""
        now = self.now()
        at = self.status.versions_at
        if at is not None and (now - at).total_seconds() < VERSIONS_SECONDS:
            return self.status.version
        try:
            answer, _ = await self.ask(carbon.VERSIONS_PATH)
        except Failed as failed:
            log.warning("the mapping's versions were not read: %s", failed)
            return self.status.version
        self.status.version, self.status.versions_at = version_of(answer), now
        return self.status.version

    # ── Resolving ───────────────────────────────────────────────────────

    async def resolve(self, entity: Entity, version: str) -> EntityState:
        """An entity as the deployment's instrument, once per mapping
        version: a company read as its ticker and resolved; anything else,
        or a ticker that does not resolve, counted with why."""
        cached = self._resolved.get((entity.carc_id, version))
        if cached is not None:
            return cached
        held = EntityState(entity.carc_id, entity.representation, version=version)
        if entity.representation not in COMPANY:
            kind = entity.representation or "subject"
            held.miss = f"a {kind} entity: no such kind of subject yet"
        else:
            await self._resolve_company(held, version)
        self._resolved[(entity.carc_id, version)] = held
        self.status.entities[entity.carc_id] = held
        return held

    async def _resolve_company(self, held: EntityState, version: str) -> None:
        noted = {"carc_id": held.carc_id, "ontology_version": version}
        try:
            answer, held.raw = await self.ask(carbon.entity_path(held.carc_id), noted)
        except Failed as failed:
            held.miss = f"not read: {failed}"
            return
        said = answer if isinstance(answer, Mapping) else {}
        held.name = _text(said.get("carc_name"))
        held.ticker = _text(said.get("ticker")).upper()
        if not held.ticker:
            held.miss = "Carbon Arc names no ticker for it"
            return
        named = [ops.Identifier(scheme="ticker", value=held.ticker)]
        as_of = _ns(self.now())
        found = await self.resolve_identifier(identifiers=named, as_of_ns=as_of)
        if found.found and found.instrument_id:
            held.instrument_id = str(found.instrument_id)
            return
        reason = found.miss_reason or ops.MISS_REASON_NOT_FOUND
        await self.report_missing_instrument(
            source=SOURCE, identifiers=named, as_of_ns=as_of, reason=reason
        )
        held.miss = (
            "two instruments hold its ticker"
            if reason == ops.MISS_REASON_AMBIGUOUS
            else "no instrument holds its ticker"
        )

    # ── Keeping the frameworks current ──────────────────────────────────

    async def read(self, framework_id: str, version: str) -> FrameworkState:
        """One purchased framework's metadata, its entities resolved."""
        held = self.status.frameworks.setdefault(framework_id, FrameworkState(framework_id))
        try:
            answer, _ = await self.ask(carbon.metadata_path(framework_id))
        except Failed as failed:
            held.state = "Not held" if failed.status == 404 else "Failing"
            held.error = str(failed)
            return held
        read = metadata_of(answer)
        held.state, held.error, held.read_at = "Held", "", self.now()
        held.insight, held.aggregate = read.insight, read.aggregate
        held.version = read.version or version
        held.entities = [e.carc_id for e in read.entities]
        for entity in read.entities:
            await self.resolve(entity, held.version)
        return held

    async def check(self) -> None:
        """Read every purchased framework named, resolving its entities."""
        self.status.checked_at = self.now()
        if self.waiting:
            self.status.error = ""
            return
        version = await self.version()
        errors: list[str] = []
        for framework_id in self.frameworks:
            held = await self.read(framework_id, version)
            if held.error:
                errors.append(f"{framework_id}: {held.error}")
        self.status.error = errors[0] if errors else ""
        if self.frameworks and len(errors) < len(self.frameworks):
            self.status.read_at = self.now()

    # ── Counting ────────────────────────────────────────────────────────

    def counts(self) -> dict[str, int]:
        """The entities read: resolved to an instrument, not resolved, and
        of a kind the platform does not hold yet."""
        held = list(self.status.entities.values())
        resolved = sum(1 for e in held if e.instrument_id)
        other = sum(1 for e in held if e.representation not in COMPANY)
        return {"resolved": resolved, "unresolved": len(held) - resolved - other, "other": other}

    # ── Wants ───────────────────────────────────────────────────────────

    async def on_observations_wanted(
        self, heard: meridian.Heard[ops.ObservationsWantedEvent]
    ) -> None:
        """Every want declined: this version records nothing in the lake."""
        await self.wants.hear(heard, self.answer)

    async def on_want_withdrawn(self, heard: meridian.Heard[ops.WantWithdrawnEvent]) -> None:
        self.wants.withdraw(heard.message.want_id)
        log.info("want %s withdrawn", heard.message.want_id)

    async def answer(
        self,
        want: ops.ObservationsWantedEvent,
        key: str,
        subjects: list[str],
        kinds: tuple[int, ...],
    ) -> dict[str, str]:
        """A want declined for every subject: no dataset is served yet."""
        return {s: "not_covered" for s in subjects}
