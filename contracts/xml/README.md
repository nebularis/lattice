<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# XML kits

Versioned XSLT kits of the transformation sidecar ([ADR-A119](../../docs/architecture/decisions/ADR-A119-xslt-transformation-sidecar.md)). Each kit is a directory `<kit>/<version>/` holding its stylesheet and a `manifest.json` that names its direction, its input, its parameters and its output. A stylesheet uses no extension function, so any conformant XSLT 3.0 processor gives the kit's output without our code.

| Kit | Direction | Reads | Gives |
|---|---|---|---|
| [`document-to-wording/1.0.0`](document-to-wording/1.0.0/manifest.json) | ingress | a document in LATTICE's markup ([ADR-A137](../../docs/architecture/decisions/ADR-A137-document-markup-vocabulary.md), [`contracts/document`](../document/README.md)) | its Wording graph as canonical sorted N-Triples |

The Configuration Studio's service runs a kit in-process with Saxon-HE. The tests of `platform/config-studio-authoring` pin `document-to-wording` to its `expected/` outputs, which are the graphs the Word add-in's first service gave for the same documents.
