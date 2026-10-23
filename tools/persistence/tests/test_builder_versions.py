# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""H2.6: a builder's version follows the text it renders (plan 4.4). The record is fixtures/ir/builder-goldens.json, kept by
`builder_goldens.py`. Validation Pack: docs/developer/validation/FMH-H2-6.md. Test IDs are H2.6-Tn."""

from __future__ import annotations

import dataclasses

import pytest

import builder_goldens as goldens
from persistence.builders import BUILDERS
from persistence.contract import BUILDER_VERSIONS, OPERATION_KINDS, stem_of


def test_h2_6_t12_every_builder_has_a_version_and_a_logical_kind():
    stems = {stem_of(key) for key in BUILDERS}
    assert set(BUILDER_VERSIONS) == set(OPERATION_KINDS) == stems  # every operation has a builder since H2.7 ported the value guard (TD-43)


@pytest.mark.parametrize("key", sorted(BUILDERS))
def test_h2_6_t13_the_recorded_version_and_digest_of_a_builder_are_those_of_its_rendered_text(key):
    """A changed text fails here until `BUILDER_VERSIONS` is bumped and `builder_goldens.py --update` records it."""
    assert goldens.current()[key] == goldens.recorded()[key], (
        f"{key}: the text it renders changed, or its version did. Bump BUILDER_VERSIONS and run "
        "mise run build:persistence-builder-goldens"
    )


def test_h2_6_t14_the_record_names_no_builder_that_does_not_exist():
    assert set(goldens.recorded()) == set(BUILDERS)


def test_h2_6_t15_the_update_refuses_a_changed_text_under_an_unchanged_version(monkeypatch, capsys):
    now = goldens.current()
    key = next(iter(now))
    tampered = {**now, key: {**now[key], "sha256": "0" * 64}}
    monkeypatch.setattr(goldens, "recorded", lambda: tampered)
    assert goldens.main(["--update"]) == 1
    assert key in capsys.readouterr().out
    bumped = {**now, key: {"version": now[key]["version"] - 1, "sha256": "0" * 64}}
    monkeypatch.setattr(goldens, "recorded", lambda: bumped)
    monkeypatch.setattr(goldens.GOLDEN.__class__, "write_text", lambda self, *a, **k: 0)
    assert goldens.main(["--update"]) == 0


def test_h2_9_t1_a_builders_recorded_text_belongs_to_its_operation_and_no_fixture_can_move_it(monkeypatch):
    """H2.9-Q2 (the finding of H2.6c). The goldens are rendered from one canonical context, so adding, removing or changing a fixture moves no
    builder's text. Taking every fixture away leaves the record as it is."""
    from persistence import witness

    def no_fixtures(*_a, **_k):
        raise AssertionError("a golden read a fixture")

    monkeypatch.setattr(witness, "compile_fixtures", no_fixtures)
    monkeypatch.setattr(witness, "_load_fixture", no_fixtures)
    assert goldens.current() == goldens.recorded()
