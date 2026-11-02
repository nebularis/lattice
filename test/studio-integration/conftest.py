# SPDX-License-Identifier: MPL-2.0
"""Options and the marker of the studio integration suite. The suite starts a studio, so `check` never collects it."""

from __future__ import annotations


def pytest_addoption(parser) -> None:  # type: ignore[no-untyped-def]
    parser.addoption("--runner", choices=("processes", "compose"), default="processes", help="how each topology's components run")


def pytest_configure(config) -> None:  # type: ignore[no-untyped-def]
    config.addinivalue_line("markers", "studio_integration: starts a Configuration Studio, on demand only (`mise run studio:integration`)")
