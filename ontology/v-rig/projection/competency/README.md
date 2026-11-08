<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Competency queries

One file per target layer, each a sequence of questions the layer's encoding should answer about a projected case, written against the layer and never against any rig. A question is a line `# question <name>: <the question in words>` followed by its SPARQL `SELECT`, and the `PREFIX` lines before the first question apply to every query in the file. The verification rig tool runs each query over the projected layer graph and reports a question that returns nothing as a finding of kind empty query, which says only that the projection has no answer, whether because the encoding has no way to say the fact or because the case does not state it. The consumer that reads the finding decides which.
