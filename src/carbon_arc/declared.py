"""What this version declares beside its role, `data`, built from code and
used twice: `__main__` registers with it, and `meridian plugin upload` reads
it from the built image (pyproject.toml's `[tool.meridian] declaration`).

**The catalogue: none in this version.** Carbon Arc's purchased panels are
values over time for an entity, and the contract has no row kind for such a
value yet: its series kind holds a listed contract's terms. The panels'
dataset, `carbon_arc_panels`, comes with that kind, and nothing is recorded
in the lake before it. This version connects with the firm's key, reads the
frameworks it has bought, and resolves their companies to instruments, so
the dataset can be added without changing anything else.

**Storage:** Carbon Arc's answers (raw.py), archivable, a year by default,
or none kept where a deployment admin says so.
"""

from __future__ import annotations

from meridian import DatasetDeclaration
from meridian.declaration import RecordKind

from .raw import DEFAULT_WINDOW_DAYS, RESPONSES

#: The datasets this version serves: none yet.
KEYS: tuple[str, ...] = ()
CATALOGUE: list[DatasetDeclaration] = []

VENDOR = "Carbon Arc"

#: Carbon Arc's terms, in plain words, as docs/terms.md summarises them.
TERMS = (
    "Carbon Arc licenses its data to each firm that buys it, under that firm's own agreement: "
    "each deployment uses its own key, and nothing is shared between deployments. Data is "
    "bought per framework, priced before purchase; this plugin never prices or buys. Whether "
    "bought data may be kept, and for how long, is the firm's contract with Carbon Arc; the "
    "plugin keeps what its settings say and enforces nothing. Work product shared outside the "
    "firm credits Carbon Arc as its terms ask."
)

RESPONSES_KIND = RecordKind(RESPONSES, "Raw responses", window_days=DEFAULT_WINDOW_DAYS)
