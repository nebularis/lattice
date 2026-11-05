# Mapping packs, trials and sample sources

Where the MORK mapping packs for published standards live, what each proposal trial left behind, how to explore and run them in the Configuration Studio's mapping mode, and how to try the language model proposer with them. Paths are from the repository root.

## ODRL 2.2

| What | Path |
|---|---|
| the hand-made pack, ODRL to stated meaning | `contracts/config-studio/odrl/odrl-instrument.mork.ttl` |
| ODRL's vocabulary and JSON-LD context, bundled so nothing is fetched | `contracts/config-studio/odrl/odrl22.ttl`, `contracts/config-studio/odrl/odrl.jsonld` |
| the sample policy, a software licence, as JSON-LD for the Meaning view's ODRL import | `contracts/config-studio/odrl/software-licence.odrl.jsonld` |
| the same policy as Turtle, the sample source for mapping mode | `contracts/config-studio/odrl/trial/software-licence.ttl` |
| the trial: a language model's proposals, each attempt with the check's answer, and its notes and score, run 2 with the improved tools | `contracts/config-studio/odrl/trial/README.md`, `contracts/config-studio/odrl/trial/run-1/`, `contracts/config-studio/odrl/trial/run-2/` |
| the trial's history, the proposal with each mapping reviewed against the pack | `contracts/config-studio/odrl/trial/history.ttl` |

## LegalRuleML

| What | Path |
|---|---|
| the OASIS RDFS schemas the trial read, with their notice | `contracts/config-studio/legalruleml/rdfs/`, `contracts/config-studio/legalruleml/README.md` |
| the metamodel as one Turtle source | `contracts/config-studio/legalruleml/trial/legalruleml-metamodel.ttl` |
| the cold run, with no history, the warm run, given the ODRL trial's lessons, and a second cold run with the improved tools | `contracts/config-studio/legalruleml/trial/cold/`, `contracts/config-studio/legalruleml/trial/warm/`, `contracts/config-studio/legalruleml/trial/cold-2/`, `contracts/config-studio/legalruleml/trial/odrl-lessons.txt` |
| both runs with their reviews, including the amended reviews of right | `contracts/config-studio/legalruleml/trial/history.ttl` |
| a sample source, a made-up supply agreement written in the metamodel by the team, for mapping mode and the check | `contracts/config-studio/legalruleml/trial/sample-supply-terms.ttl` |

LegalRuleML has no hand-made pack yet, so its proposals are reviewed against the reviews in its history rather than against a pack.

## Communities

The section observations, communities and projections drawn from the ODRL pack and the mappings both trials' reviews accepted are in `contracts/config-studio/communities-baseline.ttl`. `mise run mork:communities-baseline` writes it again after a review.

## Trying them in the studio

1. Start the studio with `mise run studio:up -- --dev` and open http://127.0.0.1:4175.
2. Make a new workspace from the sample **ODRL mappings** or **LegalRuleML mappings**. The samples are listed in `contracts/config-studio/samples/samples.ttl`, and `mise run build:config-studio-assets` stages them.
3. Switch to **Mapping** mode. Pick a scheme from the list, the hand-made pack first, and pick a mapping to see its review and edit it.
4. To run the mappings, use **Load a file** under **Sample source** and choose `contracts/config-studio/odrl/trial/software-licence.ttl` for ODRL or `contracts/config-studio/legalruleml/trial/sample-supply-terms.ttl` for LegalRuleML, or paste its text. The run repeats whenever a mapping or the sample changes.
5. The same sample checks a proposal outside the studio, its output held to the target layers' shapes: `mise run mork:propose -- check <proposal.mcn> --sample <sample.ttl>`.

## Trying the language model proposer

The proposer asks a language model, with MORK's proposal tools, for a mapping scheme from a source vocabulary to stated meaning, checks it over a sample source, and puts it beside the workspace's schemes for review. The ODRL and LegalRuleML samples are the demonstration, since each has a source vocabulary, a sample source and earlier reviews to compare against.

**1. Give the worker a model.** Only the worker reads these, so set them in the shell that starts the stack. With Anthropic's API, for example:

```bash
export LATTICE_PROPOSER_PROVIDER=anthropic LATTICE_PROPOSER_MODEL=claude-opus-5-5 LATTICE_PROPOSER_EFFORT=high
```

```bash
export LATTICE_PROPOSER_KEY_FILE=~/.config/lattice/proposer.key
```

Any Chat Completions endpoint works too, with `LATTICE_PROPOSER_PROVIDER=chat-completions` (the default) and `LATTICE_PROPOSER_URL`. The operations guide's [worker settings](../../operator/configuration-studio-operations.md#worker) list every variable, and its [secrets in files](../../operator/configuration-studio-operations.md#secrets-in-files) say how to write and protect the key's file.

**2. Start the studio** with `mise run studio:up -- --dev`, or `mise run studio:down` first if it is already running, since the worker reads its settings at start, and open http://127.0.0.1:4175.

**3. Make a workspace** from the sample **ODRL mappings**, and switch to **Mapping** mode. The hand-made pack is already there to compare against.

**4. Give it the sample source.** Under **Sample source**, use **Load a file** and choose `contracts/config-studio/odrl/trial/software-licence.ttl`.

**5. Propose.** Under **Propose with a language model**, use **Source vocabulary** to choose `contracts/config-studio/odrl/odrl22.ttl`, type its namespace `http://www.w3.org/ns/odrl/2/` in the box below, so only ODRL's own terms are read, and press **Propose**. It takes a few minutes. The ODRL trial's second run used about 107,000 tokens and 136 seconds, which the Anthropic provider's prompt caching reduces for every turn after the first.

**6. Review.** The proposal appears as a new scheme in the list, each mapping naming the run, its model and its tokens. Accept, correct, reject or defer each mapping, with a note, and save. The next proposal in the workspace is told the rules those reviews teach.

For LegalRuleML, make a workspace from **LegalRuleML mappings**, load `contracts/config-studio/legalruleml/trial/sample-supply-terms.ttl` as the sample, propose from `contracts/config-studio/legalruleml/trial/legalruleml-metamodel.ttl`, and type `http://docs.oasis-open.org/legalruleml/ns/v1.0/metamodel#` as the namespace. LegalRuleML has no hand-made pack, so compare the proposal with the trial runs' reviews in its history instead.

A job that fails says why in the job's message, for example "no language model is configured" when the worker has no model, or "the model declined the request" when a provider refuses it.

The same tools are offered to an MCP client by the studio's MCP server, so a client such as Claude Code can propose a scheme itself and save it with `mork_propose_mapping`, with no model configured in the worker (the operations guide's [MCP server](../../operator/configuration-studio-operations.md#the-mcp-server) section).

The review of what the proposing agents were given, and what to change, is in [mapping-proposer-review.md](mapping-proposer-review.md).
