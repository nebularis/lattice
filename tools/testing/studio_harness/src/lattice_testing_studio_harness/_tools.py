# SPDX-License-Identifier: MPL-2.0
"""Reaches the repository's tool scripts, `tools/lattice_repo_catalogue.py` and `tools/config_studio_stack.py`, which are modules and not an installed package."""

from __future__ import annotations

import sys
from pathlib import Path

# ponytail: found from __file__ because the catalogue reader that STD-273 names is itself in this folder. Add the scripts to a package if they ever need to install.
_TOOLS = Path(__file__).resolve().parents[4]
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

import config_studio_stack as stack  # noqa: E402
import lattice_repo_catalogue as catalogue  # noqa: E402

__all__ = ["stack", "catalogue"]
