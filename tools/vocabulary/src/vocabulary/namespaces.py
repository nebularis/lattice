# SPDX-License-Identifier: MPL-2.0
"""Namespaces used by the Vocabulary resolver.

VVP is the validation-profile-only namespace documented in
ontology/vocabulary/shapes/constraints.ttl's header: it is not part of
spec/vocabulary.ttl and is used only by fixtures and shapes/tests that need
to state a versioned record's own resolution time.
"""

from __future__ import annotations

from rdflib import Namespace

VOC = Namespace("https://www.nebularis.org/neuro-semantic/lattice/vocabulary#")
FND = Namespace("https://www.nebularis.org/neuro-semantic/lattice/foundation#")
VVP = Namespace(
    "https://www.nebularis.org/neuro-semantic/lattice/vocabulary/validation-profile#"
)
