<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# MORK transforms

The transform backends for MORK ([ADR-A148](../../docs/architecture/decisions/ADR-A148-mork-transform-backends.md)). It runs a generated XSLT 3.0 stylesheet on Saxon-HE and a generated JOLT chain on Bazaarvoice JOLT. It is a library (`Transforms.xslt`, `Transforms.jolt`) and a command line. A worker that takes a run from RabbitMQ follows when the studio runs transforms. The compilers are in [`tools/mork_transforms`](../../tools/mork_transforms).

```bash
java -jar target/mork-transforms.jar xslt <stylesheet-file> < source.xml
java -jar target/mork-transforms.jar jolt <chain-file> < source.json
```

The source is read from standard input and the result written to standard output, both as UTF-8. A usage error or a failed transform prints one line to standard error and exits 2. Source XML with a document type declaration is refused. Error messages name the failed step and never carry the input's content.

Build with `mise run bootstrap:mork-transforms` and test with `mise run check:mork-transforms`.
