# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""These tests prove the knowledge base consistent against the store `vyd build` writes (ADR-A152 decision 6)."""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple

import pyoxigraph as ox
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import lattice_repo_catalogue  # noqa: E402

ROOT = lattice_repo_catalogue.find_root()
KI = "https://www.nebularis.org/vyvid/knowledge#"
INDEX = KI + "index/lattice"
TERMS = KI + "terms/lattice"
TBOX = KI + "tbox"
FACETS = KI + "facets"


class Built(NamedTuple):
    store: ox.Store
    notes: list[str]


@pytest.fixture(scope="module")
def built() -> Built:
    """Вивід's store for this checkout, rebuilt by `vyd build` so the tests read the corpus as it is now, with every
    note and finding the build printed."""
    if shutil.which("vyd") is None:
        pytest.skip("vyd is not installed, run `mise run bootstrap`")
    done = subprocess.run(["vyd", "build"], cwd=ROOT, capture_output=True, text=True)
    assert done.returncode == 0, done.stderr[-500:]
    output = done.stdout + done.stderr
    path = done.stdout.strip().splitlines()[-1].split(" at ", 1)[1]
    return Built(ox.Store.read_only(path), [line.split(": ", 1)[1] for line in output.splitlines() if line.startswith(("NOTE: ", "FINDING: "))])




def one(store: ox.Store, query: str) -> list:
    return list(store.query(query))


def test_a_known_decision_carries_its_claim_status_and_pointer(built):
    store = built.store
    rows = one(
        store,
        f"""PREFIX ki: <{KI}>
        SELECT ?claim ?status ?pointer WHERE {{ GRAPH <https://www.nebularis.org/vyvid/knowledge#index/lattice> {{
          ?n ki:identifier "ADR-A131" ; ki:claim ?claim ; ki:status ?status ; ki:pointer ?pointer .
        }} }}""",
    )
    assert len(rows) == 1
    assert "Ledger" in str(rows[0]["claim"].value)
    assert str(rows[0]["status"].value).endswith("#Accepted")
    assert str(rows[0]["pointer"].value).startswith("docs/architecture/decisions/ADR-A131")


def test_no_decision_has_two_statuses(built):
    """A decision with a dated addendum carries a second Status line. Taking both would give one
    node two statuses and make the check that no Accepted decision depends on a Proposed one
    meaningless, so only the header's line counts."""
    store = built.store
    rows = one(
        store,
        f"""PREFIX ki: <{KI}>
        SELECT ?n (COUNT(?s) AS ?c) WHERE {{ GRAPH <https://www.nebularis.org/vyvid/knowledge#index/lattice> {{ ?n a ki:Decision ; ki:status ?s }} }}
        GROUP BY ?n HAVING (COUNT(?s) > 1)""",
    )
    assert not [str(r["n"].value) for r in rows]


def test_every_status_used_is_in_the_tbox_closed_set(built):
    """The status vocabulary exists to replace roughly fifteen freeform line shapes. If the
    extractor emitted one the T-Box does not declare, the set would not be closed."""
    store = built.store
    used = {
        str(r["s"].value)
        for r in one(
            store,
            f"PREFIX ki: <{KI}> SELECT DISTINCT ?s WHERE {{ GRAPH <https://www.nebularis.org/vyvid/knowledge#index/lattice> {{ ?n ki:status ?s }} }}",
        )
    }
    declared = {
        str(r["s"].value)
        for r in one(
            store,
            f"PREFIX ki: <{KI}> SELECT ?s WHERE {{ GRAPH <https://www.nebularis.org/vyvid/knowledge#tbox> {{ ?s a ki:Status }} }}",
        )
    }
    assert used <= declared, used - declared


def test_the_term_summary_answers_the_question_the_index_exists_for(built):
    """An agent once proposed a versioning system although Foundation already modelled one. This is
    that query, and it has to return Foundation's class with a pointer to read."""
    store = built.store
    rows = one(
        store,
        f"""PREFIX ki: <{KI}>
        SELECT ?term ?pointer WHERE {{ GRAPH <https://www.nebularis.org/vyvid/knowledge#terms/lattice> {{
          ?t ki:identifier ?term ; ki:declaredAs "Class" ; ki:pointer ?pointer ;
             ki:ownedBy ?module .
          FILTER (CONTAINS(?term, "#Version") && CONTAINS(STR(?module), "foundation"))
        }} }}""",
    )
    assert rows, "Foundation's Version class must be findable in the term summary"
    assert "foundation" in str(rows[0]["pointer"].value)


def test_every_node_has_a_claim_and_a_pointer(built):
    """The index is a handle on prose. A node without a claim cannot be triaged and one without a
    pointer cannot be read, so either makes the node useless."""
    store = built.store
    rows = one(
        store,
        f"""PREFIX ki: <{KI}>
        SELECT ?id WHERE {{ GRAPH <https://www.nebularis.org/vyvid/knowledge#index/lattice> {{
          ?n ki:identifier ?id .
          FILTER (NOT EXISTS {{ ?n ki:claim ?c }} || NOT EXISTS {{ ?n ki:pointer ?p }})
        }} }}""",
    )
    assert not [str(r["id"].value) for r in rows]


def test_a_group_reaches_every_value_under_it(built):
    """A facet value may sit under several groups, so Java is both a language and a platform, and a
    filter on either group must reach what is tagged java. CAP-72, the Java minting library, is the
    entry a held-out question failed to find."""
    store = built.store
    for group in ("language", "platform"):
        rows = store.query(
            f"""PREFIX ki: <{KI}>
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            PREFIX fct: <https://www.nebularis.org/vyvid/facets#>
            SELECT DISTINCT ?id WHERE {{
              GRAPH <https://www.nebularis.org/vyvid/knowledge#facets> {{ ?value skos:broader* fct:{group} }}
              GRAPH <https://www.nebularis.org/vyvid/knowledge#index/lattice> {{ ?n ki:technology ?value ; ki:identifier ?id }}
            }}"""
        )
        assert "CAP-72" in {str(r["id"].value) for r in rows}, group


def test_the_term_summary_holds_only_declared_ontology_terms(built):
    """The T-Box and the facet schemes are loaded into graphs of their own. Without a filter they
    would also appear in the term summary, so a question about a facet value would come back as
    though a module had declared it."""
    store = built.store
    rows = list(
        store.query(
            f"""PREFIX ki: <{KI}>
            SELECT ?term WHERE {{ GRAPH <https://www.nebularis.org/vyvid/knowledge#terms/lattice> {{ ?t ki:identifier ?term }} }}"""
        )
    )
    leaked = [str(r["term"].value) for r in rows if "/dev/" in str(r["term"].value)]
    assert not leaked


def test_a_capability_is_invoked_and_a_mechanism_is_adopted(built):
    """The class definitions in knowledge.ttl, as checks. A capability has an entry point or a
    pointer into code, and a mechanism never has an entry point."""
    store = built.store
    rows = one(
        store,
        f"""PREFIX ki: <{KI}>
        SELECT ?id ?pointer WHERE {{ GRAPH <https://www.nebularis.org/vyvid/knowledge#index/lattice> {{
          ?n a ki:Capability ; ki:identifier ?id ; ki:pointer ?pointer .
          FILTER NOT EXISTS {{ ?n ki:entryPoint ?e }}
        }} }}""",
    )
    assert rows, "the capability register must contribute capabilities"
    prose = [str(r["id"].value) for r in rows if str(r["pointer"].value).split(":")[0].endswith(".md")]
    assert not prose, f"capabilities with neither an entry point nor a pointer into code: {prose}"
    mechanisms = one(
        store,
        f"""PREFIX ki: <{KI}>
        SELECT ?id WHERE {{ GRAPH <https://www.nebularis.org/vyvid/knowledge#index/lattice> {{ ?n a ki:Mechanism ; ki:identifier ?id ; ki:entryPoint ?e }} }}""",
    )
    assert not [str(r["id"].value) for r in mechanisms]


def test_every_pattern_states_a_cost(built):
    """A technique with no trade-off is a rule, not a pattern. An empty Cost cell is reported here
    rather than filled with a guess."""
    store = built.store
    rows = one(
        store,
        f"""PREFIX ki: <{KI}>
        SELECT ?id WHERE {{ GRAPH <https://www.nebularis.org/vyvid/knowledge#index/lattice> {{
          ?n a ki:Pattern ; ki:identifier ?id .
          FILTER NOT EXISTS {{ ?n ki:cost ?c }}
        }} }}""",
    )
    assert not [str(r["id"].value) for r in rows], "patterns with no stated cost"


def test_every_evidenced_by_target_exists(built):
    """A declared edge to an identifier that no register defines would point at nothing."""
    store = built.store
    rows = one(
        store,
        f"""PREFIX ki: <{KI}>
        SELECT ?n ?o WHERE {{ GRAPH <https://www.nebularis.org/vyvid/knowledge#index/lattice> {{
          ?n ki:evidencedBy ?o .
          FILTER NOT EXISTS {{ GRAPH ?any {{ ?o ki:identifier ?id }} }}
        }} }}""",
    )
    assert not [(str(r["n"].value), str(r["o"].value)) for r in rows]


def test_every_index_entry_states_its_scope(built):
    """Each entry says who may depend on it and when it applies, so a rule of LATTICE's own test
    harness is never read as a rule for designing a runtime component."""
    store = built.store
    rows = _rows(store, """SELECT ?id WHERE { GRAPH <https://www.nebularis.org/vyvid/knowledge#index/lattice> {
        VALUES ?k { ki:Mechanism ki:Capability ki:Pattern ki:Principle ki:Standard }
        ?s a ?k ; ki:identifier ?id .
        FILTER (NOT EXISTS { ?s ki:audience ?a } || NOT EXISTS { ?s ki:phase ?p }) } }""")
    assert not [str(r["id"].value) for r in rows]


def _rows(store, query):
    return list(store.query(f"PREFIX ki: <{KI}>\n" + query))


def test_every_standard_has_a_stratum(built):
    store = built.store
    rows = _rows(store, "SELECT ?id WHERE { GRAPH <https://www.nebularis.org/vyvid/knowledge#index/lattice> { ?s a ki:Standard ; ki:identifier ?id "
                        "FILTER NOT EXISTS { ?s ki:stratum ?x } } }")
    assert not [str(r["id"].value) for r in rows]


def test_a_standard_refines_only_one_at_its_own_level_or_above(built):
    """A narrow rule must not be made to govern a broad one. Refinement runs from convention and
    practice up towards design and architecture, never down, and so can never form a cycle."""
    store = built.store
    rows = _rows(store, """SELECT ?a ?b WHERE {
        GRAPH <https://www.nebularis.org/vyvid/knowledge#index/lattice> { ?s ki:refines ?t ; ki:stratum ?ls ; ki:identifier ?a .
                         ?t ki:stratum ?lt ; ki:identifier ?b . }
        GRAPH <https://www.nebularis.org/vyvid/knowledge#tbox> { ?ls ki:level ?x . ?lt ki:level ?y . }
        FILTER (?y > ?x) }""")
    assert not [(str(r["a"].value), str(r["b"].value)) for r in rows]


def test_enforcement_names_a_capability(built):
    """A standard is enforced by a check the index holds, never by a review, which is not a check."""
    store = built.store
    rows = _rows(store, "SELECT ?id WHERE { GRAPH <https://www.nebularis.org/vyvid/knowledge#index/lattice> { ?s ki:enforcedBy ?c ; ki:identifier ?id "
                        "FILTER NOT EXISTS { ?c a ki:Capability } } }")
    assert not [str(r["id"].value) for r in rows]


def test_an_extrapolated_standard_rests_on_something(built):
    """A standard an agent extrapolated was found written nowhere, so it must name what it was
    extrapolated from: a principle it serves, a decision, or a discovery. Otherwise it is an opinion
    with an identifier."""
    store = built.store
    rows = _rows(store, """SELECT ?id WHERE { GRAPH <https://www.nebularis.org/vyvid/knowledge#index/lattice> {
        ?s ki:origin ki:Extrapolated ; ki:identifier ?id .
        FILTER NOT EXISTS { ?s ki:supports|ki:decidedBy|ki:evidencedBy ?g } } }""")
    assert not [str(r["id"].value) for r in rows]


def test_the_enforcement_gap_is_one_query(built):
    """The governance question no skill can answer: which standards does nothing check."""
    store = built.store
    def count(where: str) -> int:
        return int(_rows(store, f"SELECT (COUNT(DISTINCT ?s) AS ?n) WHERE {{ GRAPH <https://www.nebularis.org/vyvid/knowledge#index/lattice> {{ "
                                f"?s a ki:Standard {where} }} }}")[0]["n"].value)

    enforced = count(". ?s ki:enforcedBy ?c")
    unenforced = count("FILTER NOT EXISTS { ?s ki:enforcedBy ?c }")
    # Both halves, because each alone passes vacuously: a register whose enforcement edges were all
    # lost still has standards nothing enforces, and one with every edge still has a capability.
    assert enforced > 0, "no standard is enforced, so the enforcement column was not read"
    assert unenforced > 0
    assert enforced + unenforced == count("")


def test_the_release_is_one_data_quantum(built):
    """The release holds exactly the substrate's data quantum. MORK, Persistence, SPC and Surface shared
    it until ADR-A129's addendum of 2026-10-26, coupled to the substrate by nothing but the number. A
    module that newly joins the release without being coupled to the substrate fails here."""
    store = built.store
    if not store.query(f"ASK {{ GRAPH <{INDEX}> {{ ?q a <{KI}Quantum> }} }}"):
        pytest.skip("the quanta extractor did not run here. Run `vyd trust` in the checkout, then `vyd build`")
    substrate = {
        str(r["p"].value) for r in _rows(store, """PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?p WHERE { GRAPH <https://www.nebularis.org/vyvid/knowledge#index/lattice> { ?q ki:identifier "data/substrate" ; ki:includes ?m . ?m rdfs:label ?p } }""")
    }
    catalogue = lattice_repo_catalogue.load(ROOT)
    assert substrate == {m.name for m in catalogue.modules.values() if m.kind == "substrate"}
    assert {m.name for m in catalogue.release_members()} == substrate


def test_a_governed_quantum_exists(built):
    store = built.store
    if not store.query(f"ASK {{ GRAPH <{INDEX}> {{ ?q a <{KI}Quantum> }} }}"):
        pytest.skip("the quanta extractor did not run here. Run `vyd trust` in the checkout, then `vyd build`")
    rows = _rows(store, "SELECT ?id ?q WHERE { GRAPH <https://www.nebularis.org/vyvid/knowledge#index/lattice> { ?s ki:governs ?q ; ki:identifier ?id "
                        "FILTER NOT EXISTS { ?q a ki:Quantum } } }")
    assert not [(str(r["id"].value), str(r["q"].value)) for r in rows]


def test_a_terms_owner_meets_the_owner_edge_of_its_module(built):
    """A term declared under a module's folder is owned by the node an Owner cell naming that module reaches, since the
    extractor declares each unit's folder and Вивід gives a term the unit whose folder holds it (plan vyvid-migration, VM-3)."""
    store = built.store
    if not store.query(f"ASK {{ GRAPH <{INDEX}> {{ ?q a <{KI}Quantum> }} }}"):
        pytest.skip("the quanta extractor did not run here. Run `vyd trust` in the checkout, then `vyd build`")
    row = {str(r["o"].value) for r in _rows(store, f'SELECT ?o WHERE {{ GRAPH <{INDEX}> {{ ?e ki:identifier "MEC-01" ; ki:ownedBy ?o }} }}')}
    terms = {str(r["o"].value) for r in _rows(store, f'SELECT DISTINCT ?o WHERE {{ GRAPH <{TERMS}> {{ ?t ki:ownedBy ?o FILTER STRSTARTS(STR(?t), "{KI}term/lattice/foundation.") }} }}')}
    assert row == terms == {KI + "module/lattice/foundation"}


def test_every_architectural_and_design_standard_names_its_check_or_why_it_has_none(built):
    """STD-002: a standard nobody can tell is broken holds only while every reader remembers it. A
    standard with a check does not also say why it has none."""
    store = built.store
    rows = _rows(store, """SELECT ?id WHERE { GRAPH <https://www.nebularis.org/vyvid/knowledge#index/lattice> {
        ?s a ki:Standard ; ki:identifier ?id ; ki:stratum ?l .
        FILTER (?l IN (ki:ArchitecturalStratum, ki:DesignStratum))
        FILTER (NOT EXISTS { ?s ki:enforcedBy ?c } && NOT EXISTS { ?s ki:uncheckedBecause ?r }) } }""")
    assert not [str(r["id"].value) for r in rows]
    both = _rows(store, "SELECT ?id WHERE { GRAPH <https://www.nebularis.org/vyvid/knowledge#index/lattice> { ?s ki:enforcedBy ?c ; ki:uncheckedBecause ?r ; ki:identifier ?id } }")
    assert not [str(r["id"].value) for r in both]


def test_every_enforcing_check_is_classified_as_a_fitness_function(built):
    """So the absence of a holistic or a continual check is a query, not an impression."""
    store = built.store
    rows = _rows(store, """SELECT DISTINCT ?id WHERE { GRAPH <https://www.nebularis.org/vyvid/knowledge#index/lattice> { ?s ki:enforcedBy ?c . ?c ki:identifier ?id
        FILTER (NOT EXISTS { ?c ki:fitnessScope ?f } || NOT EXISTS { ?c ki:cadence ?k }) } }""")
    assert not [str(r["id"].value) for r in rows]


def test_a_store_finding_takes_its_technology_from_its_evidence(built):
    """TSD-23's Evidence line names pySHACL, so it carries pySHACL without anyone authoring it.
    TSD-07's says "both stores", which the record's Stores covered line names as rdflib and
    Oxigraph."""
    store = built.store
    # The store findings moved to the triple-stores domain, which answers for them (ADR-A152 decision 7).
    rows = _rows(store, """SELECT ?id ?t WHERE { GRAPH <https://www.nebularis.org/vyvid/knowledge#index/triple-stores> {
        ?n ki:identifier ?id ; ki:technology ?t . FILTER (?id IN ("TSD-23", "TSD-07")) } }""")
    found = {(str(r["id"].value), str(r["t"].value).rsplit("#", 1)[1]) for r in rows}
    assert ("TSD-23", "pyshacl") in found
    assert {("TSD-07", "rdflib"), ("TSD-07", "oxigraph")} <= found


# Signposts beside an answer (ADR-A134 decisions 28 to 31).


# Measured 2026-10-28 when the check was written, and recorded as TD-119. Remove an entry when its
# pointer names the section that states it, and never add one.


def test_a_declared_term_carries_a_claim_from_its_own_document(built):
    """The fact L1 lost was in the term's definition. Its claim states it, with the restrictions, so
    find ranks it by meaning and the row says what it is."""
    store = built.store
    rows = one(store, f"""PREFIX ki: <{KI}> SELECT ?claim WHERE {{ GRAPH <https://www.nebularis.org/vyvid/knowledge#terms/lattice> {{
        ?t ki:identifier "https://www.nebularis.org/neuro-semantic/lattice/ledger#keyDimension" ; ki:claim ?claim }} }}""")
    claim = str(rows[0]["claim"].value)
    assert claim.startswith("key Dimension. The dimension that derives one account per key value.")
    assert "functional" in claim and "at most 1" in claim


# Measured 2026-10-28 when the check was written, and recorded as TD-100. Remove an entry when its
# claim is cut to the limit, and never add one.


# ---- the corpus as a whole -------------------------------------------------------------------------

# The row families LATTICE's registers define, each a table whose first column is the identifier.
ROW_FAMILIES = ("STD", "PRI", "PAT", "MEC", "CAP", "TD", "PDD", "BL")
SEPARATOR_RE = re.compile(r"^\|?\s*:?-{3,}")
# Claims over the limit measured when the check was written, each a known debt. Remove an entry when its claim is
# cut to the limit, and never add one.
KNOWN_LONG_CLAIMS = frozenset({"TD-11", "TD-15", "TD-17", "TD-19", "CAP-58", "CAP-85", "PRI-51", "STD-295", "STD-296"})


def tracked(*patterns: str) -> list[Path]:
    listing = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-z", *patterns], capture_output=True, text=True, check=True)
    return [ROOT / p for p in listing.stdout.split("\0") if p and (ROOT / p).exists()]


def registers() -> list[Path]:
    import tomllib
    families = tomllib.loads((ROOT / "vyvid.toml").read_text(encoding="utf-8"))["project"]["families"]
    return [ROOT / "docs" / families[f]["defined"].removeprefix("docs:") for f in ROW_FAMILIES]


def test_every_decision_file_becomes_a_node(built):
    files = [p for p in tracked("docs/architecture/decisions/*.md") if p.stem.startswith("ADR-")]
    rows = _rows(built.store, "SELECT (COUNT(DISTINCT ?s) AS ?n) WHERE { GRAPH <" + INDEX + "> { ?s a ki:Decision } }")
    assert int(rows[0]["n"].value) == len(files)


def test_every_capability_row_is_a_capability_node(built):
    rows = _rows(built.store, "SELECT (COUNT(DISTINCT ?s) AS ?n) WHERE { GRAPH <" + INDEX + "> { ?s a ki:Capability } }")
    lines = (ROOT / "docs/developer/capabilities.md").read_text(encoding="utf-8").splitlines()
    assert int(rows[0]["n"].value) == len([l for l in lines if l.startswith("| CAP-")])


def test_every_table_in_a_register_is_a_data_table():
    """A register shows its structure with metadata, not with words: a column's meaning is the rdfs:comment of the
    property it maps to, written once. A register that explains its own columns does so in a second table, whose
    first column is not an identifier, so that is what fails."""
    offenders = []
    for path in registers():
        lines = path.read_text(encoding="utf-8").splitlines()
        for number, (line, below) in enumerate(zip(lines, lines[1:]), 1):
            if line.startswith("|") and SEPARATOR_RE.match(below.strip()):
                first = line.strip().strip("|").split("|")[0].strip()
                if first not in {"ID", "#"}:
                    offenders.append(f"{path.relative_to(ROOT)}:{number} starts with {first!r}")
    assert not offenders, offenders


def test_the_build_reports_nothing_but_the_known_notes(built):
    """Every problem Вивід finds in the corpus is a note of the build: a status it cannot read, a header it does not
    map, a value outside its set, a pointer or a signpost that resolves to nothing, a question unpromoted past its
    thirty days, which is a finding, a superseded decision naming no successor. The knowledge base is consistent when
    the build prints nothing but the notes and findings this test knows, so a new one fails here (ADR-A152 decision 6)."""
    unexpected = []
    for note in built.notes:
        cut = re.match(r"(\S+):\d+: (\S+) has a claim of \d+ characters, which is cut at 200$", note)
        if cut and (cut.group(2) in KNOWN_LONG_CLAIMS or not cut.group(1).startswith("docs/")):
            continue
        if "moved to 'triple-stores'" in note or "is a command, and the vyvid.toml" in note or note.startswith("extractor '"):
            continue
        unexpected.append(note)
    assert not unexpected, unexpected
