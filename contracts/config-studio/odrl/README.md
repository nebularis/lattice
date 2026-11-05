<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ODRL import

What the studio's ODRL import reads, described in the [studio contract](../README.md) under "Importing an ODRL policy" and decided in ADR-A144.

| File | What it is |
|---|---|
| [`odrl-instrument.mork.ttl`](odrl-instrument.mork.ttl) | the MORK mapping scheme from an ODRL 2.2 policy to stated meaning, compiled by [`tools/mork_rdf`](../../../tools/mork_rdf/README.md) |
| [`odrl.jsonld`](odrl.jsonld) | the ODRL 2.2 JSON-LD context, so a policy is read without fetching it |
| [`odrl22.ttl`](odrl22.ttl) | the ODRL 2.2 vocabulary, for its actions' labels and their `includedIn` hierarchy |
| [`software-licence.odrl.jsonld`](software-licence.odrl.jsonld) | a sample policy, a software licence with a permission, a duty, constraints, a prohibition with a remedy and an obligation |

`odrl.jsonld` and `odrl22.ttl` are copies of <https://www.w3.org/ns/odrl.jsonld> and <https://www.w3.org/ns/odrl/2/ODRL22.ttl>, taken on 2026-10-29 unchanged. They are Copyright © World Wide Web Consortium, under the licence `odrl22.ttl` itself names, the [W3C copyright notice](https://www.w3.org/Consortium/Legal/2002/ipr-notice-20021231#Copyright), from the [ODRL Information Model 2.2](https://www.w3.org/TR/odrl-model/) and [ODRL Vocabulary & Expression 2.2](https://www.w3.org/TR/odrl-vocab/) Recommendations of the W3C Permissions and Obligations Expression Working Group.
