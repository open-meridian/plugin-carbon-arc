"""The plugin never prices, quotes or buys a framework.

Carbon Arc prices a framework before it is bought, and buying spends the
firm's credits. Every call that does either is a POST to Carbon Arc's
`framework/order`, `framework/buy` or the batch quote at
`framework/metadata`. The client sends GET alone, to the addresses it
allows; these tests hold it to that, and hold the source to having no other
way out."""

from __future__ import annotations

import ast
import asyncio
import urllib.request
from pathlib import Path

import pytest

from carbon_arc import carbon
from carbon_arc.carbon import LiveApi, NotAllowed, SyntheticApi, allowed
from carbon_arc.limits import Limiter

from conftest import AT, BRANDS, CARDS, KEY, NOT_BOUGHT, role

SRC = Path(carbon.__file__).parent

#: Carbon Arc's calls that quote, price, order, buy or touch the account's
#: money, as its SDK makes them: none may be asked.
SPENDING = (
    "/v2/framework/order",
    "/v2/framework/buy",
    "/v2/framework/metadata",
    "/v2/framework/filters",
    f"/v2/framework/{CARDS}/data?fetch_all=true",
    "/v2/clients/payments/balance-summary",
    "/v2/clients/me/orders",
    "/v2/library/data",
)


@pytest.mark.parametrize("path", SPENDING)
def test_a_spending_or_unlisted_address_is_refused(path: str) -> None:
    with pytest.raises(NotAllowed):
        allowed(path)


def test_the_live_client_refuses_before_sending(monkeypatch: pytest.MonkeyPatch) -> None:
    sent: list[object] = []
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: sent.append(a))
    live = LiveApi(KEY, Limiter())
    for path in SPENDING:
        with pytest.raises(NotAllowed):
            asyncio.run(live.get(path))
    assert sent == []


def test_the_live_client_has_no_verb_but_get() -> None:
    public = {n for n in dir(LiveApi) if not n.startswith("_")}
    assert public == {"get", "mode"}
    source = (SRC / "carbon.py").read_text()
    tree = ast.parse(source)
    methods = [
        kw.value.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        for kw in node.keywords
        if kw.arg == "method" and isinstance(kw.value, ast.Constant)
    ]
    assert methods == ["GET"]
    # urlopen is never given a body, so nothing is ever POSTed.
    assert "data=" not in source


def test_no_source_names_a_purchase_or_quote() -> None:
    for path in SRC.rglob("*.py"):
        text = path.read_text()
        for word in ("/buy", "/order", "check_framework", "buy_frameworks", 'method="POST"'):
            assert word not in text, f"{path.name} names {word}"


def test_a_check_asks_only_what_it_allows(tmp_path: Path) -> None:
    api = SyntheticApi(lambda: AT)
    work = role(tmp_path, api=api, frameworks=[CARDS, BRANDS, NOT_BOUGHT])
    asyncio.run(work.check())
    assert api.asked and all(allowed(p) for p in api.asked)
    assert not any("buy" in p or "order" in p for p in api.asked)
