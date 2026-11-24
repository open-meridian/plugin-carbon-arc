"""The pace: never above the setting, Carbon Arc's 100 a minute or 1,000 an
hour, one request at a time, and a pause after a 429."""

from __future__ import annotations

import asyncio

from carbon_arc.limits import (
    FIRST_PAUSE,
    LONGEST_PAUSE,
    MOST_PER_HOUR,
    Limiter,
    per_minute,
    retry_after,
)

SECOND = 1_000_000_000
MINUTE = 60 * SECOND
HOUR = 60 * MINUTE


class Clock:
    """A clock that moves only when the limiter sleeps."""

    def __init__(self) -> None:
        self.now = 0

    def __call__(self) -> int:
        return self.now

    async def sleep(self, seconds: float) -> None:
        self.now += int(seconds * 1e9)


def most_in_any(times: list[int], span: int) -> int:
    return max(sum(1 for t in times if start <= t < start + span) for start in times)


async def _sent(limiter: Limiter, clock: Clock, n: int) -> list[int]:
    times = []
    for _ in range(n):
        await limiter.wait()
        times.append(clock.now)
    return times


async def test_never_above_the_set_rate() -> None:
    for rate in (1, 10, 60):
        clock = Clock()
        limiter = Limiter(rate, clock=clock, sleep=clock.sleep)
        times = await _sent(limiter, clock, 3 * rate)
        assert most_in_any(times, MINUTE) == rate


async def test_never_above_carbon_arcs_limits() -> None:
    clock = Clock()
    limiter = Limiter(250, clock=clock, sleep=clock.sleep)
    assert limiter.rate == 100 and per_minute(0) == 1
    times = await _sent(limiter, clock, 1500)
    assert most_in_any(times, MINUTE) <= 100
    assert most_in_any(times, HOUR) <= MOST_PER_HOUR


async def test_tasks_asking_at_once_share_the_pace() -> None:
    clock = Clock()
    limiter = Limiter(10, clock=clock, sleep=clock.sleep)
    times: list[int] = []

    async def ask() -> None:
        await limiter.wait()
        times.append(clock.now)

    await asyncio.gather(*(ask() for _ in range(30)))
    assert most_in_any(sorted(times), MINUTE) <= 10


async def test_a_429_pauses_and_retry_after_is_kept() -> None:
    clock = Clock()
    limiter = Limiter(10, clock=clock, sleep=clock.sleep)
    limiter.answered(429)
    assert limiter.paused_until_ns == FIRST_PAUSE * SECOND
    limiter.answered(429, retry_after("120"))
    assert limiter.paused_until_ns == 120 * SECOND
    for _ in range(20):
        limiter.answered(429)
    assert limiter.paused_until_ns <= clock.now + LONGEST_PAUSE * SECOND
    assert limiter.refused == 22
    limiter.answered(403)
    assert limiter.refused == 22, "a refused key is not a rate limit"
    assert retry_after("Wed, 21 Oct 2026 07:28:00 GMT") is None and retry_after(None) is None
