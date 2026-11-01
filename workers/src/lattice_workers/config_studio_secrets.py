# SPDX-License-Identifier: MPL-2.0
"""Secrets read from the environment or from a file the environment names, the env and file reference implementations of
the `SecretProvider` seam (ADR-A71).

A secret `NAME` is read from `NAME_FILE` when that is set, the path of a file holding the value alone, as Docker and
Kubernetes secrets and the Vault Agent and CSI driver write them, or else from `NAME`. Setting both is refused, since one
of them would be ignored without a word. The file is read each time the secret is asked for, so a rotated value is used
from the next job without a restart. One trailing line ending is dropped, since most editors and `echo` add one, and
nothing else is changed. A secret's value is never put into an error message or a log."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping, Optional


def secret(env: Mapping[str, str], name: str) -> Optional[str]:
    """The secret's value, or None when neither `name` nor `name_FILE` is set or the value is empty."""
    path = (env.get(f"{name}_FILE") or "").strip()
    if path and (env.get(name) or "").strip():
        raise ValueError(f"{name} and {name}_FILE are both set, and only one may be")
    if not path:
        return (env.get(name) or "").strip() or None
    try:
        value = Path(path).read_text(encoding="utf-8")
    except OSError as error:
        raise ValueError(f"{name}_FILE names {path}, which cannot be read: {error.strerror}") from None
    value = value[:-2] if value.endswith("\r\n") else value[:-1] if value.endswith("\n") else value
    if not value:
        raise ValueError(f"{name}_FILE names {path}, which is empty")
    return value
