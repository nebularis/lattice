Prompt:
@"/Users/t4/Desktop/policy-ish.txt" Let's sidestep for a minute. Attached is a fragment of a policy. Can you please process this into representations mapping to lattice's ontological layers, especially the `instrument` layer, then write up a summary of what you've found? 

Please work autonomously and put your outputs into a new folder in `.local`. Be as detailed as possible.
---

LLM Output:
I'll place the generator in `.local/policy-mapping/` alongside its output, then write the hand-authored components it incorporates—header, words and conditions, stated meaning, and parties.

Next is CPL 5 and the parties. After that I'll add the atomic conditions to the generator.

Now the conditions table in the generator. It emits atoms, negations and composites, plus the run that stitches everything together.

Generated and parsed: 4,794 triples. Next I run the instantiator and then validate against every layer's shapes.

The instantiator finished with no reports. Next, validation against every layer's shapes, run on the stated graph and on the stated plus bound graph.

Validation is slow, so it keeps running in the background. Meanwhile I'm checking the bound meaning for the behaviours I expected.

Name clash with the stdlib `inspect` module. Renaming the script.

The results show "Policy Period" still binds to its stated condition with placeholders intact, but the two generated interval conditions lost their evidence bindings, and one trigger plus one composite got regenerated while the regime's word trigger didn't. I'll now check which specific trigger and composite were affected.

The trigger was bound since GTC 4's offer power names it, while the regime names the same trigger unbound—creating two possible readings. I'll now re-serialize the bound meaning using readable prefixes, keeping the content unchanged.

Validation is still running. Meanwhile I'm writing the clause map.

I'll be notified when validation finishes. Meanwhile I'm copying the generator and its parts into the output folder, as you asked.

Of 102 leaves, 77 carry stated meaning and 5 are reviewed NoMeaning. The other 20 are unassessed: 11 structural and 9 genuine gaps. While validation finishes, I'm writing the README.

A few counts in the README need checking against the data before it's final.

Validation is still running, now at 25 minutes. Its output is buffered until the end, so I'll wait for it.

I introduced a bug where 19 money variables reference `ex:usd` instead of `ex:usd-space`, causing 38 violations; the other issues (I13 placeholder flag, I17 warnings) are expected. I'll fix the unit reference, then regenerate and rerun validation on the combined graph, saving full output to a file.

While that runs, I'm updating the README's regeneration steps and I-1. The I13 shape catches I-1, which makes it a confirmed finding.

Validation is clean apart from what was expected. The 2 violations are I-1. The 20 warnings are exactly the 20 unassessed leaves: 11 structural and 9 gaps. Next I'm writing `validation.md`.

I've mapped the policy fragment onto LATTICE's layers, run the reference instantiator over it, and validated the result against all eight layers' shapes. Everything is in `.local/policy-mapping/`, anonymised: the insurer is "Acme Insurance Company" and the insured is "the Named Entity", with names, addresses, policy numbers, brand names and the producer withheld.

**Files**
- [README.md](.local/policy-mapping/README.md): the write-up. What maps, layer by layer, then 25 model gaps (G1–G25) and 6 instantiator findings (I-1 to I-6).
- [clause-map.md](.local/policy-mapping/clause-map.md): every leaf of the wording, what it maps to, its status and which gap applies.
- [nonprofit-portfolio.ttl](.local/policy-mapping/nonprofit-portfolio.ttl): the form's wording with its 32 declaration variables, the conditions, the stated meaning, and the instance.
- [bound-meaning.ttl](.local/policy-mapping/bound-meaning.ttl): the instantiator's output for the policy. It reported nothing.
- [validation.md](.local/policy-mapping/validation.md): the shape results.
- [generator/](.local/policy-mapping/generator/): the generator script you asked to see, [gen_policy.py](.local/policy-mapping/generator/gen_policy.py). It builds the wording tree, its variables and stored values, the 19 exclusion clauses (each becomes two exclusions), and 103 conditions. It also checks that every condition named is defined. Its four hand-written Turtle parts hold everything else. `serialise_bound.py` and `validate.py` sit alongside.

**What fits**
- Of 102 leaves, 77 carry stated meaning and 5 are marked as having none.
- The sectioning works as intended: Item 6 values such as Retention and Continuity Date resolve per section.
- Both insuring agreements arise per claim, with the parties owed resolved from the claim.
- Every exclusion's carve-back is represented.
- The relation-back clauses are represented as deemings.
- The Policy Period has a full lifecycle: signature, inception, cancellation by either party, a Transaction run-off with waiver, and expiry. The bar on cancelling after a Transaction follows from that lifecycle without a separate rule.

**Validation:** 2 violations and 20 warnings.
- The 2 violations are a real instantiator defect (I-1). The bound definition of "Policy Period" still holds its date placeholders, because `_means_one` in `tools/instrument_instantiator.py` doesn't copy a condition meaning the way scope slots do. LATTICE's own law-I13 shape catches it.
- The 20 warnings are the 20 leaves deliberately left unassessed: 11 whose meaning sits under another clause's term, and 9 genuine gaps.
- My first run also had 38 violations of my own making (wrong value space on the money variables). I fixed and re-ran; the results above are from the clean run.

**The two findings that need design work**
- **G2, one limit over several relations.** A stated qualifier can qualify only one term or relation. The policy aggregate, the shared D&O/EPL limit, and a separate limit covering both insuring agreements plus defence costs all need several targets.
- **G11, one meaning stated across several clauses.** The Policy Period lifecycle draws on five clauses, but only one term can own it. The other leaves then look unassessed, and the encoding status has no value for "stated by another term".

**Other notable findings**
- **G1–G4, amounts and grouping:** limits and retentions carry no amount, Loss is not split into parts, and related Claims are not grouped.
- **I-2:** a condition regenerated during binding loses its evidence binding.
- **I-3:** the Transaction trigger is read one way by the lifecycle and another way by the power that also uses it.
- **G13, agency:** Party's delegation covers performing an obligation, not the Named Entity acting for all Insureds.
- **G21, knowledge:** "when the Risk Manager first becomes aware" and the knowledge-imputation rules are out of reach of evidence paths.
- **G10, consent:** the insurer's written consent appears five times, which bears on the open C9b question about `ins:Assent`.

Validation takes about 20 minutes with pyshacl on roughly 6,000 triples. Nothing in the repository was changed outside `.local`.