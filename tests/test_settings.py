"""The settings as declared, in the data role's order, and read back."""

from __future__ import annotations

from meridian._settings import declared_by

from carbon_arc.settings import DECLARED, config_from

from conftest import BRANDS, CARDS, KEY


def test_declared_in_the_roles_order() -> None:
    declared = declared_by(DECLARED)
    assert [s.name for s in declared] == [
        "carbon_arc_api_key",
        "carbon_arc_frameworks",
        "carbon_arc_requests_per_minute",
        "carbon_arc_keep_responses",
        "sample_data",
    ]
    key, frameworks, rate, keep, sample = declared
    assert key.required and key.secret and key.kind is str
    assert frameworks.kind is list and [c.name for c in frameworks.columns] == ["framework_id"]
    assert rate.kind is int and rate.default == 10
    assert keep.kind is bool and keep.default is True
    assert sample.developer


def test_read_back() -> None:
    config = config_from(
        {
            "carbon_arc_api_key": f"  {KEY} ",
            "carbon_arc_requests_per_minute": 30,
            "carbon_arc_frameworks": [{"framework_id": f" {CARDS.upper()} "},
                                      {"framework_id": BRANDS}, {"framework_id": CARDS},
                                      {"framework_id": "not-an-id"}, {"other": "x"}],
            "carbon_arc_keep_responses": False,
            "responses_window_days": 30,
            "responses_past_window": "archived",
        }
    )  # fmt: skip
    assert config.key == KEY and config.waiting == ""
    assert config.frameworks == (CARDS, BRANDS) and config.unread == ("not-an-id",)
    assert config.per_minute == 30 and not config.keep
    assert config.window_days == 30 and config.past_window == "archived"


def test_a_missing_key_is_waited_for() -> None:
    assert config_from({}).waiting == "is not set"
    assert config_from({"sample_data": True}).waiting == ""
    assert config_from({}).keep and config_from({}).per_minute == 10
    assert config_from({"carbon_arc_requests_per_minute": 400}).per_minute == 100
