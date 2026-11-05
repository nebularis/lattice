## Modelling from reality

**Facts, meaning and findings live apart.** Instrument holds stated meaning, bound meaning, and the
legal acts the parties did, such as assents and amendments. Behaviour holds what the evaluator
concluded and executed. Behaviour is an abstract state machine that applied ontologies use, and
deployments may implement differently, so outside a domain ontology do not name Behaviour constructs
where a legal concept belongs in Instrument.

Judgements include the law I10 case: whether an exercise took effect. An ontology layer, Behaviour's runtime document included, is data. A binding-time deferral is forced by the instantiator (law I13), and an evaluation-time deferral reads as Undetermined until forced. Statute and case law imply terms no clause states, such as a duty not to withhold consent unreasonably (`ins:impliedBy`).

## Modelling rules

**"Versioned".** A class that is a member of `fnd:Versioned` is *versioned*: it supports versions,
provenance and the rest. Call a node "a version" only when it is one specific version. The class is
to be renamed `fnd:Versioned` (technical debt TD-20).

**Domain-neutral substrate.** Explain a substrate term from law, contract drafting or computing,
never by appeal to "the market". Never cite a downstream project in a layer README. Draw examples
from several domains, such as lending, licences, trials, warranties and insurance, and order them by
what explains the mechanism best. Headings, captions and table columns name the domain or instrument
an example comes from ("Lending", "A guarantee"), and never rank one domain's examples before or
after another's.

**No market words as technical terms.** A word with a market meaning reads as that meaning to an insurance reader. "Binder" names a binding authority or a cover note, so producing bound meaning is **instantiation**, done by an **instantiator**. Check a new term against `docs/glossary.md`, `ontology/applied/insurance/` and `find <its meaning> --kind term` first. "Bound" stays where it is technical ("bound meaning", `ins:boundIn`, `ins:boundFrom`), never alone where it could read as cover. SPC's "binder" is the process-calculus term and stays.

**A "Formalisation" section names no tool.** Title it "Formalisation". Say what the type means, not
the ADR, the generation mechanism or past evaluations, which are recorded where they were decided.

A domain of `ins:LegalRelation` on `ins:activity` would make every trigger naming an act a legal relation.

## Designing for the runtime

An optimisation with no such meaning is projected through Surface.

The worked example is Ledger, in [ledger-history-and-runtime.md](../../../docs/developer/sketches/ledger-history-and-runtime.md), where the four drivers decide where a draw is recorded.
