# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""Entry point so the package runs as ``python -m persistence``."""

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
