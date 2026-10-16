# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The spike's name for the Oxigraph adapter, which now lives in ``tools/testing/oxigraph`` (ADR-A125).

The adapter was written here, for formal-methods track H slices H1.3 and H1.4a, and moved when slice H2.4b made it a
maintained test-support package. This module keeps the spike's imports working. Install the package first with
``mise run bootstrap:testing-oxigraph``."""

from __future__ import annotations

from lattice_testing_oxigraph import OxigraphStore as OxigraphBackend
from lattice_testing_oxigraph import Term, XSD, bind_parameters, iri, literal

__all__ = ["OxigraphBackend", "bind_parameters", "iri", "literal", "Term", "XSD"]
