# SPDX-License-Identifier: MPL-2.0
"""The verification rig tool. Reads a rig in the stated format into the `vrig:` intermediate representation
(ontology/v-rig) and writes its projections under an ignored path. Nothing from a rig enters a tracked file."""

from .canon import VERSION
from .lift import lift
from .rig import Rig, RigError, read_rig
from .out import OutError, resolve_out, write_outputs

__all__ = ["VERSION", "Rig", "RigError", "OutError", "read_rig", "lift", "resolve_out", "write_outputs"]
