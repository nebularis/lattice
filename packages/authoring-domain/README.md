<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Authoring Domain

TypeScript code shared by the Word authoring add-in (`apps/word-authoring-addin`) and the Configuration Studio (`apps/config-studio`). It holds the document model, the content-control tag codec, UTF-16 offset helpers, and the studio's RDF graph model with its namespaces. It has no UI, React or Office.js dependency, so any browser app can use it.

The document XML reader and writer will join it once the document XML vocabulary is defined. The conversion between Word's OOXML and the document XML stays in the add-in, since only Word needs it.

Both apps depend on it as a Yarn workspace (`"@lattice/authoring-domain": "workspace:*"`) and import its TypeScript source directly, so there is no build step.

## Checks

```bash
mise run check:authoring-domain   # type-check and unit tests
```

## Licence

MPL-2.0.
