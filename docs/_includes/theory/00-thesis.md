## 0. The thesis
{: #thesis}

Every non-trivial system that lets you *derive* things from a source of truth faces the same question sooner or later: how far can you trust the derived thing? LATTICE's answer, repeated at every layer in a different mathematical costume, is: **only as far as something has been mechanically proven.**

That single sentence is the thread running through this whole page. What changes from layer to layer is *which* branch of logic or theoretical computer science supplies the proof:

| Where | What's being trusted | The theory that bounds the trust |
|---|---|---|
| The graph itself | What can be concluded from a possibly-incomplete set of facts | Description logic and the open-world assumption |
| Layers, hierarchies, closures | That a dependency order or an ancestor relation is well-behaved | Order theory — partial orders, closure operators, well-foundedness |
| Surface's generated content | That restating a fact doesn't silently change what it means | Conservative extension, from model theory |
| Eligibility's decisions | What "we don't know yet" is allowed to mean | Three-valued logic |
| MORK's mapping proposals | That an automatically-proposed alignment is actually the best one | Category theory — profunctors, Galois connections, Formal Concept Analysis |
| SPC's live conversations | That a multi-party exchange can't deadlock or desynchronise | Session types, a type theory for communication protocols |
| Every compiled artefact | That regenerating something produces the same thing, not almost the same thing | Determinism and content-addressing |

None of this is decoration. Read on, and by the end each row above should read as an obvious consequence of the theory next to it, not as jargon bolted on afterward.
