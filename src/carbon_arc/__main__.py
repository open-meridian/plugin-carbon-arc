"""Carbon Arc as an Open Meridian data plugin, stage 1: it reads the
frameworks a firm has already bought, with the firm's own key, and resolves
the companies they measure to the deployment's instruments. It never prices
or buys a framework, and records nothing in the lake in this version: the
panels' values wait on a kind of record the contract does not have yet
(declared.py).

It runs its data role class, `Lake` (frameworks.py's `Frameworks`, with its
lifecycle here), with `meridian.run` on the sidecar it is launched beside,
declaring its storage and its settings (declaration.py); `meridian.run`
delivers the settings, serves its pages (page.py), hands it what the lake
wants of it, and sets the data role's figures on each heartbeat. It reads
the purchased frameworks at start and every hour, at the pace its settings
allow (limits.py). What Carbon Arc answered is kept in the storage the
deployment grants (raw.py), unless a deployment admin says not to, and
moved past its window as the settings say. It holds nothing else: a restart
reads Carbon Arc again.

While the key is unset it asks Carbon Arc nothing, and its status and
figures name the setting.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import Any

import meridian

from .carbon import api
from .declaration import DECLARATION, PORT
from .frameworks import Frameworks
from .limits import Limiter
from .page import figures, hold, pages
from .raw import RawStore
from .settings import API_KEY, Config, config_from

log = logging.getLogger("carbon_arc")

#: How often the purchased frameworks are read, in seconds.
CHECK_SECONDS = 3600
#: How often storage is tended past its window, in seconds: daily.
TEND_SECONDS = 86_400
#: How often the datasets' licences are read again.
LICENCES_SECONDS = 60


class Lake(Frameworks):
    """The data role's class with its lifecycle: `meridian.run` delivers each
    settings to `on_settings` -- the first before anything is heard -- and
    starts `run`, again after a backoff should it fail."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.config = Config()
        self.limiter = Limiter()
        self.wake = asyncio.Event()

    async def on_settings(self, delivered: Any) -> None:
        """Apply each delivery of the settings: the key, the frameworks, the
        pace, whether answers are kept, sample data on or off, and the
        answers' window, tended at once."""
        config = config_from(delivered.values)
        self.config = config
        self.limiter.set_rate(config.per_minute)
        self.raw.keeping = config.keep
        if config.waiting:
            log.warning("waiting: %s %s", API_KEY, config.waiting)
        self.use(
            api(config.sample_data, config.key, self.limiter),
            config.frameworks,
            config.waiting,
            config.unread,
        )
        self.wake.set()
        await self.raw.tend(self.plugin, config.window_days, config.past_window, self.now())

    async def on_start(self) -> None:
        """Its storage read once registered: on an instance run as shards or
        with a standby pod, the shard's own folder."""
        await super().on_start()
        self.raw.open()

    async def on_stop(self) -> None:
        """Its storage forgotten: registered again, it is read afresh."""
        self.raw.close()
        await super().on_stop()

    async def run(self) -> None:
        """The purchased frameworks read, storage tended, and the licences
        read."""
        await asyncio.gather(self._check(), self._tend(), self._licences())

    async def _check(self) -> None:
        while True:
            self.wake.clear()
            try:
                await self.check()
            except meridian.MeridianError as failed:
                self.status.error = f"the deployment refused a call: {failed}"
                log.warning("this check stopped: %s", failed)
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(self.wake.wait(), timeout=CHECK_SECONDS)

    async def _tend(self) -> None:
        while True:
            await asyncio.sleep(TEND_SECONDS)
            config = self.config
            await self.raw.tend(self.plugin, config.window_days, config.past_window, self.now())

    async def _licences(self) -> None:
        while True:
            try:
                await self.wants.read_licences()
            except meridian.MeridianError as failed:
                log.warning("the datasets' licences were not read this time: %s", failed)
            await asyncio.sleep(LICENCES_SECONDS)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    limiter = Limiter()
    lake = Lake(api(False, "", limiter), RawStore(), waiting="is not set")
    lake.limiter = limiter
    hold(lake)
    meridian.run(
        declaration=DECLARATION,
        roles=[lake],
        pages=pages,
        port=PORT,
        on_settings=lake.on_settings,
        figures=lambda: figures(lake.status, lake),
    )


if __name__ == "__main__":
    main()
