# SPDX-License-Identifier: MPL-2.0

"""
Closures in the compilers (ADR-A105, elg:L15 as restated, elg:L17), CCS HQ-6a.2.

A set reading decides on completeness, Denied under some value and Permitted under every value,
the empty case included, only for a binding that names a closure (``elg:closedUnder``). The SPARQL
backend is the reference, and its rows name the closure a decision relied on. The SHACL backend
must agree with it. A binding naming something that is not a closure, or a closure with no source,
is refused with ``exe:NoClosureLicence``. Each example's tables are the ones its comments state,
and the ones ``tools/test_closures.py`` reads with the reference semantics.
"""

from __future__ import annotations

import unittest
from pathlib import Path
from typing import Dict, FrozenSet, Optional, Tuple

from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import RDF

from .eligibility_ir import IRCompileError, compile_any_condition, compile_profile
from .namespaces import ELG, MORK
from .sparql_backend import compile_query_template
from .test_set_readings import shacl

ONTOLOGY = Path(__file__).resolve().parents[4] / "ontology"
ADM = Namespace("https://example.org/lattice/eligibility/admissions/")
TRIAL = Namespace("https://example.org/lattice/eligibility/trial/")
USE = Namespace("https://example.org/lattice/eligibility/usage-reports/")
FAC = Namespace("https://example.org/lattice/instrument/facility-requests/")
REI = Namespace("https://example.org/lattice/instrument/reinsurance-claims-cooperation/")
INS = Namespace("https://www.nebularis.org/neuro-semantic/lattice/instrument#")

EXAMPLES = {
    "admissions": ONTOLOGY / "eligibility" / "examples" / "set-reading-admissions.ttl",
    "trial": ONTOLOGY / "eligibility" / "examples" / "set-reading-trial.ttl",
    "usage": ONTOLOGY / "eligibility" / "examples" / "closure-usage-reports.ttl",
    "facility": ONTOLOGY / "instrument" / "examples" / "facility-requests.ttl",
    "reinsurance": ONTOLOGY / "instrument" / "examples" / "reinsurance-claims-cooperation.ttl",
}

P, D, U = "Permitted", "Denied", "Undetermined"

# (example, condition, subject class, {subject: (with the closure, without it)})
CASES = [
    ("admissions", ADM["stem-qualification"], ADM.Applicant,
     {"ada": (P, P), "ben": (D, U), "cai": (D, U), "dee": (P, P)}),
    ("admissions", ADM["no-medicine"], ADM.Applicant,
     {"ada": (P, U), "ben": (P, U), "cai": (P, U), "dee": (D, D)}),
    ("trial", TRIAL["all-permitted"], TRIAL.Patient,
     {"pat-1": (P, U), "pat-2": (D, D), "pat-3": (P, U)}),
    ("trial", TRIAL["none-excluded"], TRIAL.Patient,
     {"pat-1": (P, U), "pat-2": (D, D), "pat-3": (P, U)}),
    ("usage", USE["no-use-in-france"], USE.Licence,
     {"lic-1": (P, U), "lic-2": (D, D), "lic-3": (P, U)}),
    ("facility", FAC["no-objection"], INS.Proposal,
     {"request-1": (P, U), "request-2": (D, D), "request-3": (P, U)}),
    ("reinsurance", REI["settled-with-approval"], REI.Claim,
     {"claim-1": (P, P), "claim-2": (D, U)}),
]


def example(name: str, closed: bool = True) -> Graph:
    graph = Graph().parse(EXAMPLES[name])
    if not closed:
        graph.remove((None, ELG.closedUnder, None))
    return graph


def sparql(plan, data: Graph) -> Dict[str, Tuple[str, Optional[URIRef]]]:
    """Each subject's decision and the closure it relied on, if any."""
    artefact = compile_query_template(plan)
    template = next(artefact.subjects(RDF.type, MORK.QueryTemplate))
    rows = list(data.query(str(artefact.value(template, MORK.queryText))))
    keyed = {str(row[0]).rsplit("/", 1)[1]: (str(row.decision), row.closure) for row in rows}
    assert len(keyed) == len(rows), "one decision per subject"
    return keyed


def sparql_profile(plan, data: Graph) -> Dict[str, Tuple[str, FrozenSet[URIRef]]]:
    """Each record's decision and the closures it relied on, split from ``?closures``."""
    artefact = compile_query_template(plan)
    template = next(artefact.subjects(RDF.type, MORK.QueryTemplate))
    rows = list(data.query(str(artefact.value(template, MORK.queryText))))
    keyed = {
        str(row[0]).rsplit("/", 1)[1]: (
            str(row.decision),
            frozenset(URIRef(c) for c in str(row.closures).split()) if row.closures is not None else frozenset(),
        )
        for row in rows
    }
    assert len(keyed) == len(rows), "one decision per record"
    return keyed


class ExampleTests(unittest.TestCase):
    def test_sparql_decides_each_example_with_and_without_its_closure(self) -> None:
        # HQ6a2-04
        for name, condition, _, table in CASES:
            for closed, column in ((True, 0), (False, 1)):
                data = example(name, closed)
                rows = sparql(compile_any_condition(data, condition), data)
                got = {subject: rows[subject][0] for subject in table}
                self.assertEqual(got, {s: outcomes[column] for s, outcomes in table.items()}, (name, closed))

    def test_shacl_agrees_with_sparql(self) -> None:
        # HQ6a2-05
        for name, condition, subject_class, table in CASES:
            for closed in (True, False):
                data = example(name, closed)
                plan = compile_any_condition(data, condition)
                subjects = list(data.subjects(RDF.type, subject_class))
                expected = {k: v[0] for k, v in sparql(plan, data).items()}
                self.assertEqual(shacl(plan, data, subjects), expected, (name, closed))


class RelianceTests(unittest.TestCase):
    def test_a_row_names_the_closure_only_when_completeness_decided(self) -> None:
        # HQ6a2-06: Denied under some value with no Permitted value, so before negation
        data = example("admissions")
        closure = ADM["registry-closure"]
        stem = sparql(compile_any_condition(data, ADM["stem-qualification"]), data)
        self.assertEqual({s: c for s, (_, c) in stem.items()},
                         {"ada": None, "ben": closure, "cai": closure, "dee": None})
        no_medicine = sparql(compile_any_condition(data, ADM["no-medicine"]), data)
        self.assertEqual({s: c for s, (_, c) in no_medicine.items()},
                         {"ada": closure, "ben": closure, "cai": closure, "dee": None})

    def test_a_profile_row_names_the_union_of_its_conditions_closures(self) -> None:
        # HQ6a2-08 (HQ6a2-Q2 (i)): ada relies through no-medicine, ben and cai through both, dee on neither
        data = example("admissions")
        closure = ADM["registry-closure"]
        rows = sparql_profile(compile_profile(data, ADM["engineering-admission"]), data)
        self.assertEqual({s: c for s, (_, c) in rows.items()},
                         {"ada": {closure}, "ben": {closure}, "cai": {closure}, "dee": set()})

    def test_no_row_names_a_closure_without_one(self) -> None:
        data = example("admissions", closed=False)
        rows = sparql(compile_any_condition(data, ADM["no-medicine"]), data)
        self.assertTrue(all(closure is None for _, closure in rows.values()))


class RefusalTests(unittest.TestCase):
    def test_a_binding_naming_no_closure_is_refused(self) -> None:
        # HQ6a2-07
        data = example("usage")
        data.remove((USE["reports-closure"], RDF.type, ELG.Closure))
        with self.assertRaisesRegex(IRCompileError, "NoClosureLicence"):
            compile_any_condition(data, USE["no-use-in-france"])

    def test_a_closure_with_no_source_is_refused(self) -> None:
        # HQ6a2-07
        data = example("usage")
        data.remove((USE["reports-closure"], ELG.licensedBy, None))
        with self.assertRaisesRegex(IRCompileError, "NoClosureLicence"):
            compile_any_condition(data, USE["no-use-in-france"])


if __name__ == "__main__":
    unittest.main()
