<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# How LATTICE's components read their settings — sketch

**Status:** Sketch, 2026-10-30. Questions CFG-Q1 to CFG-Q6 open. Not planned. On the backlog as BL-01.
**Question prefix:** CFG
**Raised by:** the maintainer, 2026-10-30, while the studio's worker gained a choice of language model provider: each component reads its own environment variables its own way, and no design says how a setting is named, typed, documented, supplied or checked.
**Would need:** an ADR on deployment configuration. It meets ADR-A71's seam inventory (`SecretProvider`, `LLMProvider`), ADR-A29's rule that `mise.toml` holds shared environment variables, and ADR-A80's split between what a component checks, read from the ontology, and how it runs, a deployment-local setting that does not belong in RDF.

## 1. The scene

Measured 2026-10-30 on `claude/config-authoring-studio`:

- **About 35 `LATTICE_*` variables** are read across `platform/`, `workers/`, `tools/`, `apps/` and `mise.toml`, counting a secret's `_FILE` form. The studio reads more than 20 of them.
- **Each component reads its own.** The studio's service and writer read theirs in `StudioConfig.fromEnv` and `WriterConfig.fromEnv`, the worker in `config_studio_main.read_config` and, for a proposer, at each job. The reasoning test kit, the hooks and the deny-list read theirs where they are used. Each does its own parsing, defaults and errors.
- **Documentation is by hand,** in the operations guide's tables and each component's README, and the two drift. The worker's table missed the mapping proposer until 2026-10-30.
- **Secrets** are read from `NAME` or the file `NAME_FILE` names, by `config_studio_secrets.secret` in Python and `Secrets.secret` in Java, the env and file implementations of `SecretProvider`. A Vault adapter is BL-02.
- **A provider is chosen by a variable,** `LATTICE_PROPOSER_PROVIDER` naming `chat-completions` or `anthropic`, and each provider reads the variables it needs. This is the first setting that selects an implementation of a seam, and the pattern this sketch should settle before a second one copies it.
- **`mise.toml`** sets the local stack's values (`studio:worker`'s `env`, `tools/config_studio_stack.py`), so the same values are written in two places.

## 2. What a configuration layer would do

1. **Declare** each setting once, with its name, type, default, whether it is a secret, which components read it, and its meaning, so the operations guide's tables are generated from the declaration, never written by hand.
2. **Supply** values from layered sources in a stated order, for example a default, a deployment file, the environment, and a secret provider for secrets.
3. **Choose** a seam's implementation by name (`LLMProvider`, `SecretProvider`, a store adapter), with the chosen implementation's own settings scoped beneath it.
4. **Check** every value at start, refusing an unknown name, a wrong type or a missing required value in one report, never one at a time.
5. **Hide** a secret's value from every log, error and report of the effective configuration.
6. **Work alike in Java, Python and TypeScript,** since the platform is all three.

## 3. Options

| Option | What it is | For | Against |
|---|---|---|---|
| (a) A convention, written down | Keep environment variables. Name them `LATTICE_<COMPONENT>_<SETTING>`, `_FILE` for secrets, `_PROVIDER` to choose a seam, and declare each in a register the guide's tables are generated from | Least change. Every platform supplies environment variables | No layering, no structured values, the check stays in each component |
| (b) A declared schema with a reader per language | A machine-readable declaration (JSON Schema or a small YAML file per component) and a reader library in each language that layers defaults, a deployment file and the environment, checks the result and resolves secrets through `SecretProvider` | Generated documentation, one check, structured values such as a provider's own settings | Three small libraries to keep alike |
| (c) Settings as RDF | Settings described by a vocabulary and checked by SHACL, as the ontologies are | One modelling language across LATTICE | ADR-A80 places operational settings outside RDF. A component would need an RDF stack to start |
| (d) An existing library per language | For example Helidon Config or MicroProfile Config in Java and pydantic-settings in Python | Mature layering and typing | Two models of a setting, which (b)'s declaration would still have to reconcile |

The hypothesis to test is (b), with (a)'s naming convention as its first slice, since the convention is needed by every other option and costs nothing to adopt. (d)'s libraries could implement (b)'s reader in each language rather than replace the declaration.

## 4. Questions

- **CFG-Q1.** Which option, and is the declaration one register for the whole platform or one file per component?
- **CFG-Q2.** What is the order of sources, and may a deployment file hold a secret's reference (for example a Vault path) but never its value?
- **CFG-Q3.** How is a seam's implementation named and versioned, so a configuration can say `LLMProvider: anthropic` and carry that provider's own settings?
- **CFG-Q4.** Does a component report its effective configuration, with secrets masked, at start or on request, and where?
- **CFG-Q5.** Does `mise.toml` keep the local stack's values, or does the stack read a deployment file like any other deployment?
- **CFG-Q6.** How are today's variable names migrated, given that deployments outside this repository may set them?

## 5. What this does not cover

Configuration of the ontologies and of an applied layer, such as Behaviour's configuration documents (ADR-A106) or a compiled persistence profile, which is semantic content and stays in RDF. This sketch is about how a running component is told where things are and how to behave.
