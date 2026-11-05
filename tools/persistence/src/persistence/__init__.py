# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The LATTICE persistence profile compiler (ADR-A78, ADR-A79).

Turns an adopter's ``ontology/persistence`` configuration into a
``dal:CompiledProfile`` graph (the ``compile`` stage), and optionally that
graph into portable SPARQL text, built by each operation's builder (the
``instantiate`` stage). Neither stage requires a live backend or an SPI.
"""

__version__ = "0.1.0"
