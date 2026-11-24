"""What the version declares: no dataset yet, and its answers in storage."""

from __future__ import annotations

from carbon_arc.declaration import DECLARATION
from carbon_arc.declared import TERMS


def test_no_dataset_until_the_platform_has_a_kind_for_a_panel() -> None:
    assert list(DECLARATION.catalogue) == []


def test_carbon_arcs_terms_in_words() -> None:
    assert len(TERMS) <= 2000
    assert "own key" in TERMS and "never prices or buys" in TERMS
    assert "firm's contract with Carbon Arc" in TERMS


def test_the_answers_are_kept_in_storage() -> None:
    assert DECLARATION.storage is not None
    assert [k.name for k in DECLARATION.storage.kinds] == ["responses"]
