"""The typed records the pages answer, for a person's page and an agent's
tool alike: the data role's common records (`meridian.roles.data`), each
extended with Carbon Arc's own fields, and the purchased frameworks'. The
Connection page is `read_connection`, Datasets `read_datasets` and
Frameworks `read_purchased_frameworks`, each answering what its page shows.

None holds a panel's values: a data plugin's pages show its connection, its
datasets and how its subjects resolve. A framework's metadata (its insight,
its entities) is what the firm bought, not the data it measures.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from meridian.roles import data


@dataclass(frozen=True)
class ConnectionRead(data.ConnectionRead):
    """Connection's common fields, then Carbon Arc's: the head's status and
    what it means, where it reads, the last check, why it waits (the key
    unset, naming the setting), the pace kept, the frameworks kept current,
    and the answers kept."""

    state: str = ""
    said: str = ""
    source: str = ""
    checked_at: str = ""
    waiting: str = ""
    per_minute: int = 0
    frameworks_kept: int = 0
    keeping: bool = True
    responses_kept: int = 0
    kept_for: str = ""


@dataclass(frozen=True)
class DatasetsRead(data.DatasetsRead):
    """Datasets' common fields, then Carbon Arc's: why no dataset is served
    yet, and its terms in words."""

    served: list[data.Served] = field(default_factory=list)
    wants: list[data.WantHeard] = field(default_factory=list)  # type: ignore[assignment]
    not_yet: str = ""
    terms: str = ""


@dataclass(frozen=True)
class EntityRead:
    """One of Carbon Arc's entities a purchased framework measures: its
    `carc_id`, how the framework names it, Carbon Arc's name and ticker for
    it, the mapping version it was read under, and the deployment's
    instrument or why there is none."""

    carc_id: int
    representation: str
    name: str = ""
    ticker: str = ""
    version: str = ""
    instrument_id: str = ""
    miss: str = ""


@dataclass(frozen=True)
class FrameworkRead:
    """One purchased framework the firm named: its state (Held, Not held,
    Failing or Not read yet), its insight and aggregation, the mapping
    version, its entities by `carc_id`, when it was last read and the last
    error."""

    framework_id: str
    state: str
    insight: str = ""
    aggregate: str = ""
    version: str = ""
    entities: list[int] = field(default_factory=list)
    read_at: str = ""
    last_error: str = ""


@dataclass(frozen=True)
class FrameworksRead:
    """The purchased frameworks the firm named, their entities, how many
    resolved to an instrument, how many did not, how many are of a kind the
    platform does not hold yet, and each row of the setting that is not a
    framework ID."""

    frameworks: list[FrameworkRead] = field(default_factory=list)
    entities: list[EntityRead] = field(default_factory=list)
    resolved: int = 0
    unresolved: int = 0
    other_kinds: int = 0
    unread: list[str] = field(default_factory=list)
    version: str = ""
