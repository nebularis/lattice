# SPDX-License-Identifier: MPL-2.0

"""The environment banner (tools/conftest.py) names exactly the tools that are absent."""

from conftest import missing_tools


def test_banner_names_the_tools_that_are_absent(monkeypatch) -> None:
    import conftest
    monkeypatch.setattr(conftest, "_TOOLS", (
        ("here", lambda: True, "x", "y"),
        ("gone", lambda: False, "lost", "fix"),
    ))
    assert missing_tools() == [("gone", "lost", "fix")]
