"""How fast the plugin asks Carbon Arc, and how it backs off.

Carbon Arc allows a client 100 requests a minute and 1,000 an hour, both at
once, and answers more with 429 and a `Retry-After`
(https://docs.carbonarc.ai/platform/rate-limits). The plugin keeps to its own
share, the `carbon_arc_requests_per_minute` setting (1 to 100, 10 by
default), and never more than 1,000 in any hour.

**The pace.** Requests are spaced evenly, one every `60/rate` seconds, one at
a time (a lock), so two tasks never share a slot. The hour's count is kept
over a sliding window of the last hour's requests.

**Backing off.** A 429 pauses every request for as long as `Retry-After`
says, otherwise 30 seconds, doubled after each refusal in a row up to an
hour. The refused request is not sent again here: what asked for it asks on
its next turn. The first answer that is not a refusal resets the pause.
"""

from __future__ import annotations

import asyncio
import math
import time
from collections import deque
from collections.abc import Awaitable, Callable

#: Carbon Arc's limits for one client.
MOST_PER_MINUTE = 100
MOST_PER_HOUR = 1000
#: The plugin's share by default.
DEFAULT_PER_MINUTE = 10
#: The first pause after a refusal, and the longest, in seconds.
FIRST_PAUSE = 30.0
LONGEST_PAUSE = 3600.0
HOUR_NS = 3600 * 1_000_000_000


def per_minute(asked: int) -> int:
    """The rate kept: the setting, held to 1 to Carbon Arc's 100."""
    return max(1, min(MOST_PER_MINUTE, int(asked)))


def retry_after(value: str | None) -> float | None:
    """The seconds a `Retry-After` header says, where it gives a delay."""
    said = (value or "").strip()
    return float(said) if said.isdigit() else None


class Limiter:
    """At most `rate` requests a minute and 1,000 an hour, one at a time,
    and a pause after a refusal. `clock` answers nanoseconds and `sleep`
    waits seconds, both the real ones unless a test gives its own."""

    def __init__(
        self,
        rate: int = DEFAULT_PER_MINUTE,
        clock: Callable[[], int] = time.monotonic_ns,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self.clock = clock
        self.sleep = sleep
        self.rate = per_minute(rate)
        self._lock = asyncio.Lock()
        self._next_ns = 0
        self._paused_until_ns = 0
        self._pause = FIRST_PAUSE
        self._hour: deque[int] = deque()
        #: Refusals seen since start, for the Connection page.
        self.refused = 0

    @property
    def spacing_ns(self) -> int:
        return math.ceil(60 * 1_000_000_000 / self.rate)

    def set_rate(self, rate: int) -> None:
        self.rate = per_minute(rate)

    @property
    def paused_until_ns(self) -> int:
        return self._paused_until_ns

    async def wait(self) -> None:
        """Wait for this request's slot, and take it."""
        async with self._lock:
            now = self.clock()
            at = max(now, self._next_ns, self._paused_until_ns)
            while self._hour and self._hour[0] <= at - HOUR_NS:
                self._hour.popleft()
            if len(self._hour) >= MOST_PER_HOUR:
                at = max(at, self._hour[0] + HOUR_NS)
            if at > now:
                await self.sleep((at - now) / 1e9)
            self._hour.append(at)
            self._next_ns = at + self.spacing_ns

    def answered(self, status: int, retry_after_seconds: float | None = None) -> None:
        """Note what Carbon Arc answered: a 429 pauses every request,
        anything else ends the pause."""
        if status != 429:
            self._pause = FIRST_PAUSE
            return
        self.refused += 1
        pause = retry_after_seconds if retry_after_seconds is not None else self._pause
        self._paused_until_ns = max(self._paused_until_ns, self.clock() + int(pause * 1e9))
        self._pause = min(LONGEST_PAUSE, self._pause * 2)
