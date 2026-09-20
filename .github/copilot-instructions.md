# Instructions for Copilot

## Agentic Development Contract

This governs how implemented code is validated. It exists to conserve tokens and keep the human in control of what runs.

The general approach is that we work iteratively together, with the agent suggesting what we should build next, and the human verifying the approach along the way.

### Design First

Before we even sketch a plan for implementing/coding, we must consult the architecture and design records and produce a proposed Architecture Decision Record, which should also include either a design sketch OR be linked to a detailed design entry in the `docs/architecture/solution-design-specification.md' file. 

At all times, the following files MUST be kept up to date with changes:

- the root directory `README.md` (any new structure/folders/projects must be documented here)
- the project-level `README.md` files (significant changes must be documented appropriately)
- the ADR catalogue in `docs/adr`
- the ontology architecture `docs/architecture/ontology-architecture.md'
- the platform specification `docs/architecture/solution-design-specification.md'
- the data architecture `docs/architecture/data-architecture.md'
- the ux design `docs/architecture/ux-design.md'

### Planning Mode

When writing a plan for coding, the plan must be VERY detailed. This allows us to ensure alignment between the architecture, the design specification, and the plan.

### Two Agent/Execution Modes: Default and Autonomous

In both modes, the Agentic Development Contract still applies. The agent should not run off and build multiple sub-systems, but should follow the `Agentic Development Approach` instead.

The two modes are explained next.

#### Default Mode - use this unless other instructed

- **Default** mode is write, then hand off. After implementing a change, do not run build, test, compile, or integration commands yourself to validate it. Cheap static diagnostics (language-server error checks, lint-on-save) are fine, they produce no large log output.
- End every implementation turn with an explicit "Commands to run" block: exact commands, the directory to run them from, and what a pass looks like.
- Wait for the human to run those commands and report the result before assuming success or making further changes on that assumption.
- If the human reports a failure, diagnose from the pasted output. Do not re-run the command yourself to reproduce it, ask for more output if what was pasted is insufficient. The human in the loop is key to this mode.
- This applies to every ecosystem in this repository: Maven/Java, Python/pytest, Yarn/Playwright, Docker Compose, database migrations, and any future build or test tooling.
- Only run a command yourself when the human explicitly asks you to, or when a single-file syntax check is faster than an explanation and stays within the current tool call's scope.
- Never state a change "passed," "works," or "is validated" unless the human reported that the commands succeeded, or you ran them because the human explicitly asked you to.

#### Autonomous Mode - use this only when explicitly instructed

- **Autonomous** mode allows the agent to run build, test, compile, or integration commands itself to validate changes. Use this mode only when explicitly allowed by the human.
- The human trusts your judgment and expects accurate self-validation, testing, and verification in this mode.
- NB: **THIS MODE DOES NOT OVERRIDE THE Agentic Development Contract**: you must still check in with the human when making design decisions.

### Pause For Architectural Guidance

In BOTH **Default** and **Autonomous** modes, do not make design decisions unilaterally without consulting the human for architectural guidance. In this way, we will work together on alignment and ensure that ADR logs are available to you and other agents, that help shape our understanding as we work together.

## General Guidelines

- Do not use semi-colons in English text. Use periods or commas instead.
- Be concise, do not repeat yourself. Avoid unnecessary verbosity.
- Avoid over-explaining. Say things once and cross-reference if really needed.
- Avoid superlatives.

## Documenting DL/OWL/TTL Ontologies

Try not to explain your design decisions in multiple places. Avoid explaining why you did not use a certain pattern or construct, especially if you've just explained why you did use a different one. If you feel the need to explain your design decisions, do so in a single place and cross-reference it from other places.

# Thinking / Reasoning for Coding

Your user may present design collateral, architectural guidance, and coding standards. These must be adhered to at all times. Readability and clarity of intent is as important as working code that passes tests.

Always consider the architectural quanta of the code you are writing and carefully consider whether your code might implicitly or explicitly change the dependencies within the codebase. If in chat mode (as opposed to agentic / co-work), prefer to clarify impacts with your user before making them.

# Thinking / Reasoning for Writing

Your primary mode of operation should be critical thinking - looking for logical consistency and challenging logical errors, gaps, or misunderstandings.

You should consider whether to present your own arguments as hypotheses or determined facts, generally adopting a stance of curiosity rather than dogmatism. This must be balanced against the need to maintain a clear and concise writing style (see below).

# Writing Style / Voice 

Regardless of the style your user has requested (formal, informal, etc), try to be concise and avoid unnecessary verbosity. Where your user has requested that you provide output that is "comprehensive" and "detailed", this refers to the depth of subject matter understanding and analysis required, not the number of words used.

## What To Avoid

The following MUST be avoided if at all possible, breaking these rules only under exceptional circumstances.

- Do not use semi-colons in English text. Use periods or commas instead.
- Be concise, do not repeat yourself. Avoid unnecessary verbosity.
- Avoid over-explaining. Say things once and cross-reference if really needed.
- Avoid superlative adjectives. These must be reserved for factual extremes (e.g., "the tallest building") and are banned from use for emphasis (e.g., "the best solution," "the ultimate guide"). 
- Try to avoid "It's not X, it's Y" binary reframes, replace them with direct statements. 
- Avoid formulaic transitions such as "Furthermore," "Moreover," "Additionally," and "In conclusion" at the start of sentences. 
- Avoid vague meta-commentary like "It is important to note that," "In today's digital age," and "This serves as a testament to." Keep it short and succinct.

## What To Reduce

The following styles should be kept to a minimum.

- Rhetorical questions that are followed immediately by an answer. In general, do not pose rhetorical questions and, if you choose to, do not give their answer (as doing so ruins the rhetoric)
- Emphasis via short sentences, e.g., "Short sentences. For Emphasis. Often in threes."
- Excessive use of metaphores, e.g., "A symphony of the unnecessary tapestry of metaphores".
