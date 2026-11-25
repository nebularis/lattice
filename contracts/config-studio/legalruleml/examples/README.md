<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# LegalRuleML examples

Two LegalRuleML documents, the RDF each gives, and the stylesheet that makes it. The RDF is what the LegalRuleML mapping pack reads. The studio's mapping mode runs over RDF, so a Turtle file here is a sample source for it.

| File | What it is |
|---|---|
| [`ex5-section29new-compact.lrml`](ex5-section29new-compact.lrml) | an OASIS example in the compact syntax, an Australian credit-licensing rule set with a prohibition, a strong permission, an override and two penalties |
| [`ex5-section29new-normal.lrml`](ex5-section29new-normal.lrml) | the same example in the normal syntax, which the stylesheet reads |
| [`ex5-section29new-normal.ttl`](ex5-section29new-normal.ttl) | the RDF of the normal form |
| [`cover-exclusion-condition.lrml`](cover-exclusion-condition.lrml) | the project's own document in the normal syntax, a cover, an exclusion that overrides it and a condition the cover depends on |
| [`cover-exclusion-condition.ttl`](cover-exclusion-condition.ttl) | the RDF of that document |
| [`../xslt/triplifyMerger-ids-noxi.xsl`](../xslt/triplifyMerger-ids-noxi.xsl) | the OASIS stylesheet that makes the RDF |

## How the RDF is made

The stylesheet reads a document in the normal syntax with its prefixes evaluated, and writes RDF/XML in the terms of the LegalRuleML metamodel (the files of [`../rdfs/`](../rdfs)). It runs on Saxon-HE, which `platform/mork-transforms` ships, and needs no XInclude. The Turtle files are that RDF/XML read and written as Turtle, and `tools/test_config_studio_stage.py` makes each again and checks that it is the same graph, so a document and its RDF stay equal. To make one by hand, run `java -cp platform/mork-transforms/target/mork-transforms.jar net.sf.saxon.Transform -s:<document> -xsl:contracts/config-studio/legalruleml/xslt/triplifyMerger-ids-noxi.xsl -o:<rdf>` after `mise run bootstrap:mork-transforms`.

OASIS also publishes a normalizer that turns the compact syntax into the normal one. It imports its modules from a host that was not reachable, so the normal form of the OASIS example is a copy of the one OASIS publishes and the compact form is kept beside it for reading.

## Provenance of the OASIS copies

The three OASIS files are copies of the following under <https://docs.oasis-open.org/legalruleml/legalruleml-core-spec/v1.0/os/>, taken on 2026-11-25 and unmodified, their line endings being LF already, part of the [LegalRuleML Core Specification Version 1.0](https://docs.oasis-open.org/legalruleml/legalruleml-core-spec/v1.0/os/legalruleml-core-spec-v1.0-os.html), an OASIS Standard of 30 August 2021.

| Copy | Taken from |
|---|---|
| `ex5-section29new-compact.lrml` | `examples/compactified/ex5-section29new-compact.lrml` |
| `ex5-section29new-normal.lrml` | `examples/normalized/ex5-section29new-normal.lrml` |
| `../xslt/triplifyMerger-ids-noxi.xsl` | `xslt/lrml-rdf/triplifyMerger-ids-noxi.xsl` |

The notice of [`../README.md`](../README.md) applies to them and to the Turtle files made from the first two. Copyright © OASIS Open 2021. All Rights Reserved.

The stylesheet `triplifyMerger-ids.xsl` beside it on the host is the same transformation with XInclude. Its output points at other documents to be included, so the version without XInclude is the one kept.

## Provenance of the project's own document

`cover-exclusion-condition.lrml` was written by the project on 2026-11-25 as a clean-room document from generic meaning. Its author held the generic meaning of an insurance cover, an exclusion and a condition, and the LegalRuleML normal syntax from the schema. It is not taken from any policy wording, market form or other document, and names no insurer, broker or client. Its names, such as `claim` and `indemnify`, are generic. It states three rules.

- **A cover.** For a claim of damage by an insured event for which the condition holds, an indemnity is obligatory.
- **An exclusion.** For a claim of loss the insured caused on purpose, an indemnity is prohibited, and the exclusion overrides the cover.
- **A condition.** The condition holds for a claim where the premium for the period of the loss was paid.

It is valid against OASIS's normal-syntax schema (`xsd-schema/normal/lrml-normal.xsd`, fetched to check it and not kept). Its licence is `CC-BY-SA-4.0`, and it is public applied content.
