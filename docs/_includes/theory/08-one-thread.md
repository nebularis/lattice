## 8. One thread
{: #thread}

Pull the thread all the way through and every section above turns out to be one recurring move, dressed in the mathematics that fits the specific question being asked:

- Description logic bounds what can be concluded from an incomplete graph, and SHACL is reached for exactly where that bound would otherwise be too weak.
- Order theory gives layering, hierarchies, and closures a precise shape — and a precise notion of when that shape is broken (a cycle) rather than a vague sense that something's off.
- Conservative extension is the mechanical test that decides whether a generated fact is safe to discard, applied literally, not just invoked as a slogan.
- Three-valued logic refuses to let "we don't know" collapse into a guess dressed up as an answer.
- Category theory turns "which mapping is correct" from a matter of taste into an optimisation with a checkable, provably-optimal solution once enough evidence exists.
- Session types turn "will this conversation go wrong" from a testing question into a typing question, decidable before anything runs.
- Determinism and content-addressing turn "do I trust this artefact" into "did recomputing it produce the same bytes," which anyone — human or CI job — can just go and check.

And the practical, cross-cutting expression of all of it is the authority ceiling repeated at nearly every layer that generates anything: a derived artefact may declare itself `Advisory` or, at most, `CachedReproducible` — trustworthy *because* it's provably reproducible from its source, and never higher, because a derived thing outranking the declaration it came from would invert the entire relationship this page has been describing. Every theory above exists to make that one sentence something a compiler can enforce, rather than something a README merely asks you to believe.
