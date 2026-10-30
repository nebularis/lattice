# Mapping packs, trials and sample sources

Where the MORK mapping packs for published standards live, what each proposal trial left behind, and how to explore and run them in the Configuration Studio's mapping mode. Paths are from the repository root.

## ODRL 2.2

| What | Path |
|---|---|
| the hand-made pack, ODRL to stated meaning | `contracts/config-studio/odrl/odrl-instrument.mork.ttl` |
| ODRL's vocabulary and JSON-LD context, bundled so nothing is fetched | `contracts/config-studio/odrl/odrl22.ttl`, `contracts/config-studio/odrl/odrl.jsonld` |
| the sample policy, a software licence, as JSON-LD for the Meaning view's ODRL import | `contracts/config-studio/odrl/software-licence.odrl.jsonld` |
| the same policy as Turtle, the sample source for mapping mode | `contracts/config-studio/odrl/trial/software-licence.ttl` |
| the trial: a language model's proposal, each attempt with the check's answer, and its notes and score | `contracts/config-studio/odrl/trial/README.md`, `contracts/config-studio/odrl/trial/run-1/` |
| the trial's history, the proposal with each mapping reviewed against the pack | `contracts/config-studio/odrl/trial/history.ttl` |

## LegalRuleML

| What | Path |
|---|---|
| the OASIS RDFS schemas the trial read, with their notice | `contracts/config-studio/legalruleml/rdfs/`, `contracts/config-studio/legalruleml/README.md` |
| the metamodel as one Turtle source | `contracts/config-studio/legalruleml/trial/legalruleml-metamodel.ttl` |
| the cold run, with no history, and the warm run, given the ODRL trial's lessons | `contracts/config-studio/legalruleml/trial/cold/`, `contracts/config-studio/legalruleml/trial/warm/`, `contracts/config-studio/legalruleml/trial/odrl-lessons.txt` |
| both runs with their reviews, including the amended reviews of right | `contracts/config-studio/legalruleml/trial/history.ttl` |

LegalRuleML has no hand-made pack and no sample source yet, so its proposals can be explored in mapping mode but not run.

## Trying them in the studio

1. Start the studio with `mise run studio:up -- --dev` and open http://127.0.0.1:4175.
2. Make a new workspace from the sample **ODRL mappings** or **LegalRuleML mappings**. The samples are listed in `contracts/config-studio/samples/samples.ttl`, and `mise run build:config-studio-assets` stages them.
3. Switch to **Mapping** mode. Pick a scheme from the list, the hand-made pack first, and pick a mapping to see its review and edit it.
4. To run the mappings, use **Load a file** under **Sample source** and choose `contracts/config-studio/odrl/trial/software-licence.ttl`, or paste its text. The run repeats whenever a mapping or the sample changes.

The review of what the proposing agents were given, and what to change, is in [mapping-proposer-review.md](mapping-proposer-review.md).
