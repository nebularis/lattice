<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Verification rig vectors

`vectors.schema.json` is the schema of the test vectors the verification rig tool generates from a case of a rig under one reading, `lattice-v-rig-vectors/1`. A vector carries the case digest and the rig digest, the reading as a key and a token with the documents that state it, the programme's currency and period, each layer's attachment, limit, documents and placements, and each event's inputs by the names the rig's extension binds. Every fact is in one of three states, each its own shape, stated with a value, stated as not known, or absent, and a limit written as a formula is stated with its expression and the names it reads. The vectors are the inputs of the differential tests between the reference semantics and each compiled implementation, and a consumer outside the repository reads them by the schema alone. The vocabulary they are generated from is [`ontology/v-rig`](../../ontology/v-rig/README.md).
