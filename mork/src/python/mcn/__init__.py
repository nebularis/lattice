"""
mcn -- thin re-export package.

The actual implementation lives in the flat modules mcn_decoder.py and
mcn_codebook.py (matching this repository's existing convention of one
module per top-level tool, e.g. mork2rml.py, morkSC.py). This package
exists only so that `import mcn` works for consumers who expect a package
literally named `mcn` with `decode`/`lint`/`canonical_ntriples` as
top-level functions -- e.g. the MTP-L0/L2 teaching-pack generator sketches
in mork/docs/, whose mcnio.InProcessTool does `import mcn` and then calls
`mcn.decode(...)` / `mcn.lint(...)`.

There is no encode() here: MCN's RDF->MCN encoding direction (spec §15) is
not implemented. Consumers that check `getattr(mcn, "encode", None)` will
correctly treat it as absent.
"""

from __future__ import annotations

from mcn_decoder import (  # noqa: F401
    DCT,
    FND,
    MORK,
    RML,
    RR,
    SH,
    SKOS,
    SWRL,
    SWRLB,
    LintFinding,
    McnLintError,
    McnSyntaxError,
    Profile,
    canonical_ntriples,
    decode,
    lint,
)

import mcn_codebook as codebook  # noqa: F401

__all__ = [
    "decode",
    "lint",
    "canonical_ntriples",
    "McnSyntaxError",
    "McnLintError",
    "Profile",
    "LintFinding",
    "codebook",
    "MORK",
    "SKOS",
    "SH",
    "SWRL",
    "SWRLB",
    "RR",
    "RML",
    "FND",
    "DCT",
]
