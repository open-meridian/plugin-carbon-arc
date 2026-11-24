"""The plugin's settings, declared to the SDK, and what it makes of them.

In the data role's order: no `environment` (Carbon Arc has one API); the
credential; the plugin's own; then the role's sample data.

- `carbon_arc_api_key` -- the firm's own Carbon Arc API key, from Carbon
  Arc's user portal. Required and secret: while it is missing the plugin
  asks Carbon Arc nothing and its status names the setting. Each deployment
  enters its own.
- `carbon_arc_frameworks` -- the frameworks the firm has already bought that
  the plugin keeps current, a typed table of one column, each a framework
  ID. The plugin never buys or prices one: a framework not bought answers
  that it is not held.
- `carbon_arc_requests_per_minute` -- the plugin's share of Carbon Arc's
  limit of 100 requests a minute: 1 to 100, 10 by default.
- `carbon_arc_keep_responses` -- whether Carbon Arc's answers are kept in
  the plugin's storage (for as long as the responses window says) or read
  and let go. Kept by default.
- `sample_data` -- a developer's setting: the responses committed under
  responses/ in place of Carbon Arc, for trying the plugin offline.

The SDK declares the storage's two settings from the declaration's kind:
`responses_window_days` and `responses_past_window`. Their names are the
SDK's, and read here only.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import meridian

from .carbon import FRAMEWORK_ID
from .limits import DEFAULT_PER_MINUTE, MOST_PER_MINUTE, per_minute
from .raw import DEFAULT_WINDOW_DAYS, RESPONSES

API_KEY = "carbon_arc_api_key"
FRAMEWORKS = "carbon_arc_frameworks"
PER_MINUTE = "carbon_arc_requests_per_minute"
KEEP = "carbon_arc_keep_responses"
#: The table's one column: a framework's ID.
FRAMEWORK = "framework_id"
SAMPLE_DATA = "sample_data"
WINDOW = f"{RESPONSES}_window_days"
PAST_WINDOW = f"{RESPONSES}_past_window"
#: The most frameworks the table holds.
MOST_FRAMEWORKS = 200


@meridian.settings
class Declared:
    """The settings as declared, in the data role's order."""

    carbon_arc_api_key: str = meridian.setting(
        "API key",
        required=True,
        secret=True,
        description=(
            "Your firm's own Carbon Arc API key, from Carbon Arc's user portal. Never shown or "
            "logged. Nothing is asked of Carbon Arc until it is set."
        ),
    )
    carbon_arc_frameworks: list = meridian.setting(  # type: ignore[type-arg]
        "Purchased frameworks",
        description=(
            "The frameworks your firm has already bought that this plugin keeps current, one "
            "framework ID per row. The plugin never prices or buys a framework."
        ),
        columns=[
            meridian.Column(
                FRAMEWORK,
                kind="text",
                label="Framework ID",
                required=True,
                description="The framework's ID, as Carbon Arc shows it once bought",
            )
        ],
        most_rows=MOST_FRAMEWORKS,
    )
    carbon_arc_requests_per_minute: int = meridian.setting(
        "Requests a minute",
        default=DEFAULT_PER_MINUTE,
        at_least=1,
        at_most=MOST_PER_MINUTE,
        unit="requests a minute",
        description=(
            "This plugin's share of Carbon Arc's limit of 100 requests a minute and 1,000 an "
            "hour. Lower it where other tools at your firm use the same key."
        ),
    )
    carbon_arc_keep_responses: bool = meridian.setting(
        "Keep Carbon Arc's answers",
        default=True,
        description=(
            "On, each answer is kept in the plugin's storage for the responses window. Off, "
            "answers are read and not kept. Whether bought data may be kept is your firm's "
            "contract with Carbon Arc."
        ),
    )
    sample_data: bool = meridian.sample_data(
        description=(
            "Serve the responses committed with the plugin instead of asking Carbon Arc: two "
            "fictitious frameworks in Carbon Arc's layout. Runs without a key. Development "
            "deployments only."
        )
    )


DECLARED = Declared


@dataclass(frozen=True)
class Config:
    key: str = ""
    frameworks: tuple[str, ...] = ()
    #: Each row that is not a framework ID, as entered.
    unread: tuple[str, ...] = ()
    per_minute: int = DEFAULT_PER_MINUTE
    keep: bool = True
    sample_data: bool = False
    window_days: int = DEFAULT_WINDOW_DAYS
    past_window: str = "kept"

    @property
    def waiting(self) -> str:
        """Why Carbon Arc is not asked: the key unset; empty where it may be."""
        return "" if self.key or self.sample_data else "is not set"


def _frameworks(rows: object) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """The table's framework IDs, once each, in its order; and the rows that
    are not one."""
    held: list[str] = []
    unread: list[str] = []
    if not isinstance(rows, Sequence) or isinstance(rows, str):
        return (), ()
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        entry = str(row.get(FRAMEWORK, "")).strip()
        if not entry:
            continue
        if not FRAMEWORK_ID.fullmatch(entry):
            unread.append(entry[:80])
        elif entry.lower() not in held:
            held.append(entry.lower())
    return tuple(held[:MOST_FRAMEWORKS]), tuple(unread)


def config_from(values: Mapping[str, object]) -> Config:
    """The configuration a delivery of the settings says."""
    key = values.get(API_KEY)
    rate = values.get(PER_MINUTE)
    window = values.get(WINDOW)
    past = values.get(PAST_WINDOW)
    keep = values.get(KEEP)
    frameworks, unread = _frameworks(values.get(FRAMEWORKS))
    return Config(
        key=key.strip() if isinstance(key, str) else "",
        frameworks=frameworks,
        unread=unread,
        per_minute=per_minute(rate) if isinstance(rate, int) else DEFAULT_PER_MINUTE,
        keep=keep is not False,
        sample_data=values.get(SAMPLE_DATA) is True,
        window_days=window if isinstance(window, int) and window > 0 else DEFAULT_WINDOW_DAYS,
        past_window=past if isinstance(past, str) and past else "kept",
    )
