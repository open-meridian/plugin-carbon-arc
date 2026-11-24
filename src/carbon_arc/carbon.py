"""Carbon Arc's API, read only, and its stand-in.

Carbon Arc serves its data at `https://api.carbonarc.co`, under `/v2`, to a
bearer token (`Authorization: Bearer <key>`), as its Python SDK sends it
(https://pypi.org/project/carbonarc/, `utils/auth.py` and `base.py`).

**Never buy.** Carbon Arc prices a framework before it is bought, and buying
spends the firm's credits. Every call of Carbon Arc's that prices, orders or
buys is a POST. This client sends GET alone, and only to the addresses
`READS` allows; anything else is refused before a byte is sent
(`NotAllowed`). So no code path in this plugin can price or buy a framework,
and `tests/test_never_buys.py` holds it to that.

What it reads, and nothing else:

- `/v2/framework/<id>/metadata` -- one framework the firm already bought;
- `/v2/ontology/entities/<carc_id>?entity_representation=ticker` -- one of
  Carbon Arc's entities as a ticker, to resolve it to an instrument;
- `/v2/ontology/ontology-versions` -- the entity mapping's versions.

**The key.** The `carbon_arc_api_key` setting, added to a request only as it
is sent. It is never logged, kept with an answer, put in an error or shown.

**How fast.** Every request waits for its slot (limits.py).

`SyntheticApi` answers from the responses committed under responses/
(responses/index.json), in the shapes Carbon Arc's documentation and SDK
show, so the tests and sample data run offline and the same on any day.
"""

from __future__ import annotations

import asyncio
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from importlib import resources
from typing import Any, Protocol

from .limits import Limiter, retry_after

HOST = "https://api.carbonarc.co"
VERSION = "/v2"
TIMEOUT = 60.0
#: The most of an answer read.
MOST_BYTES = 16 * 1024 * 1024

#: A framework's ID, as Carbon Arc gives it: a UUID.
_HEX = "[0-9a-fA-F]"
FRAMEWORK_ID = re.compile(rf"{_HEX}{{8}}-{_HEX}{{4}}-{_HEX}{{4}}-{_HEX}{{4}}-{_HEX}{{12}}")

#: Every address this client may read, as a pattern on its path; GET alone.
READS = (
    re.compile(rf"/v2/framework/{FRAMEWORK_ID.pattern}/metadata"),
    re.compile(r"/v2/ontology/entities/\d{1,18}"),
    re.compile(r"/v2/ontology/ontology-versions"),
)


def metadata_path(framework_id: str) -> str:
    if not FRAMEWORK_ID.fullmatch(framework_id):
        raise ValueError(f"{framework_id!r} is not a framework ID")
    return f"{VERSION}/framework/{framework_id.lower()}/metadata"


def entity_path(carc_id: int, representation: str = "ticker") -> str:
    return f"{VERSION}/ontology/entities/{int(carc_id)}?" + urllib.parse.urlencode(
        {"entity_representation": representation}
    )


VERSIONS_PATH = f"{VERSION}/ontology/ontology-versions"


class NotAllowed(Exception):  # noqa: N818 - what the address is
    """An address this client never asks: anything but a read it allows."""


def allowed(path: str) -> str:
    """The path, where it is one this client may read; NotAllowed otherwise."""
    bare = urllib.parse.urlsplit(path).path
    if not any(read.fullmatch(bare) for read in READS):
        raise NotAllowed(f"{bare} is not a read this plugin makes")
    return path


class Unreachable(Exception):  # noqa: N818 - what Carbon Arc was
    """Carbon Arc could not be asked: no answer, or not in time."""


@dataclass(frozen=True)
class Fetched:
    """One answer of Carbon Arc's, as received."""

    path: str
    status: int
    body: bytes
    fetched_at: datetime
    headers: dict[str, str] = field(default_factory=dict)

    @property
    def text(self) -> str:
        return self.body.decode("utf-8", errors="replace")

    def json(self) -> Any:
        """The answer's JSON; None where it holds none."""
        try:
            return json.loads(self.body)
        except ValueError:
            return None

    @property
    def error(self) -> str:
        bare = urllib.parse.urlsplit(self.path).path
        if self.status in (401, 403):
            return (
                f"{bare} answered {self.status}: Carbon Arc refused the key; "
                "check carbon_arc_api_key"
            )
        if self.status == 404:
            return f"{bare} answered 404: Carbon Arc holds no such item for this key"
        if self.status == 429:
            return f"{bare} answered 429: too many requests; paused"
        return f"{bare} answered {self.status}"


class Api(Protocol):
    mode: str
    limiter: Limiter

    async def get(self, path: str) -> Fetched: ...


def utc_now() -> datetime:
    return datetime.now(UTC)


class LiveApi:
    """Carbon Arc itself, read with `key`, paced by `limiter`. It has one
    method, `get`; there is no other verb."""

    mode = "live"

    def __init__(self, key: str, limiter: Limiter, now: Callable[[], datetime] = utc_now) -> None:
        self._key = key.strip()
        self.limiter = limiter
        self._now = now

    async def get(self, path: str) -> Fetched:
        allowed(path)
        await self.limiter.wait()
        got = await asyncio.to_thread(self._get, path)
        self.limiter.answered(got.status, retry_after(got.headers.get("retry-after")))
        return got

    def _get(self, path: str) -> Fetched:
        request = urllib.request.Request(
            HOST + path,
            method="GET",
            headers={"Authorization": f"Bearer {self._key}", "Accept": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT) as answer:  # noqa: S310 - Carbon Arc's https address
                body = answer.read(MOST_BYTES + 1)
                status = answer.status
                headers = {k.lower(): v for k, v in answer.headers.items()}
        except urllib.error.HTTPError as refused:
            body = refused.read(MOST_BYTES + 1) if refused.fp else b""
            status = refused.code
            headers = {k.lower(): v for k, v in (refused.headers or {}).items()}
        except (urllib.error.URLError, TimeoutError, OSError) as failed:
            reason = getattr(failed, "reason", failed)
            bare = urllib.parse.urlsplit(path).path
            raise Unreachable(f"{bare}: {type(reason).__name__}") from failed
        if len(body) > MOST_BYTES:
            raise Unreachable(f"{path}: answered more than {MOST_BYTES} bytes")
        return Fetched(path, status, body, self._now(), headers)


class SyntheticApi:
    """The responses committed under responses/: each address answered as
    its file says, anything else 404. It allows the same reads as Carbon
    Arc's client, and refuses the same."""

    mode = "synthetic"

    def __init__(self, now: Callable[[], datetime] = utc_now) -> None:
        self._now = now
        self.limiter = Limiter()
        held = resources.files(__package__).joinpath("responses")
        index = json.loads(held.joinpath("index.json").read_text(encoding="utf-8"))
        self.answers: dict[str, Any] = {
            path: json.loads(held.joinpath(name).read_text(encoding="utf-8"))
            for path, name in index["answers"].items()
        }
        self.asked: list[str] = []

    async def get(self, path: str) -> Fetched:
        allowed(path)
        self.asked.append(path)
        at = self._now()
        if path not in self.answers:
            return Fetched(path, 404, b'{"detail": "Not Found"}', at)
        return Fetched(path, 200, json.dumps(self.answers[path]).encode(), at)


def api(synthetic: bool, key: str, limiter: Limiter, now: Callable[[], datetime] = utc_now) -> Api:
    return SyntheticApi(now) if synthetic else LiveApi(key, limiter, now)
