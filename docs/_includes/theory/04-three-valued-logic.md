## 4. Three-valued logic: living with "we don't know yet"
{: #threeval}

Classical logic assumes every proposition is either true or false, and nothing else. That's a convenient fiction for pure mathematics, but it's a bad fit for a graph that's frequently, legitimately incomplete — and LATTICE deliberately doesn't force the fit. Eligibility's decisions, and Quantification's comparisons, both resolve to one of **three** values, not two:

| Value | Eligibility's reading | Quantification's reading |
|---|---|---|
| **True** / **Permitted** | Evidence demonstrates satisfaction. | The comparison holds. |
| **False** / **Denied** | Evidence demonstrates failure. | The comparison does not hold. |
| **Undetermined** | Evidence is missing, malformed, incompatible, or insufficient. | A value is absent, unresolved, insufficiently granular, or an operation isn't permitted for the spaces involved. |

This is the same move logicians make with **Kleene's strong three-valued logic**: rather than defaulting an unknown input to either true or false, "unknown" is treated as its own value that propagates honestly through a computation instead of silently resolving to a guess. Concretely: if a candidate range's lower bound is present but its upper bound is missing, the right answer to "is this contained in the required interval" isn't a coin-flip between Permitted and Denied — it's a distinct, first-class Undetermined, with its own recorded reason (missing value, insufficient granularity, an absent conversion context, and so on), because those different reasons call for different remediation.

There's a quiet but important reason this pairs naturally with the open-world assumption from [Section 1](#dl): an open-world reasoner already refuses to treat "the graph doesn't say X" as "X is false," so a two-valued decision procedure built on top of it would have to invent a default somewhere — and any invented default is a policy decision masquerading as a logical one. Three-valued evaluation removes the need to invent anything: "don't know" stays "don't know," all the way out to whoever has to act on the answer.
