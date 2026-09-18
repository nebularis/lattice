# src/spc/verify/owl_verifier.py
"""
OWL classification and consistency checking via Jena.

Loads the SPC T-Box + domain ontology + protocol A-Box into Jena,
runs classification, and checks for inconsistencies.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import subprocess
import json
from typing import Optional

from spc.verify.jena_client import JenaClient


@dataclass
class OWLVerificationResult:
    consistent: bool = True
    unsatisfiable_classes: list[str] = field(default_factory=list)
    classification_errors: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return self.consistent and not self.unsatisfiable_classes


def verify_owl(
    jena_client: JenaClient,
    tbox_path: Path,
    domain_ontology_path: Optional[Path],
    abox_path: Path,
    extension_paths: Optional[list[Path]] = None,
) -> OWLVerificationResult:
    """
    Load ontologies and A-Box into Jena and check consistency.
    """
    result = OWLVerificationResult()

    # Upload T-Box
    jena_client.upload_graph(tbox_path, graph_name="urn:spc:tbox")

    # Upload domain ontology
    if domain_ontology_path and domain_ontology_path.exists():
        jena_client.upload_graph(
            domain_ontology_path, graph_name="urn:spc:domain")

    # Upload extension ontologies
    for ext_path in (extension_paths or []):
        if ext_path.exists():
            jena_client.upload_graph(
                ext_path,
                graph_name=f"urn:spc:ext:{ext_path.stem}")

    # Upload protocol A-Box
    jena_client.upload_graph(abox_path, graph_name="urn:spc:protocol")

    # Check for unsatisfiable classes
    unsat_query = """
    PREFIX owl: <http://www.w3.org/2002/07/owl#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT ?class WHERE {
        ?class rdfs:subClassOf owl:Nothing .
        FILTER (?class != owl:Nothing)
    }
    """
    try:
        unsat_result = jena_client.sparql_query(unsat_query)
        for binding in unsat_result.get("results", {}).get("bindings", []):
            cls = binding.get("class", {}).get("value", "")
            result.unsatisfiable_classes.append(cls)
            result.consistent = False
    except Exception as e:
        result.classification_errors.append(f"Consistency check failed: {e}")

    # Check that all asserted types are consistent with partition axioms
    partition_query = """
    PREFIX spc: <http://spc.marsh.com/ontology/core#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    SELECT ?individual ?type1 ?type2 WHERE {
        ?individual rdf:type ?type1 .
        ?individual rdf:type ?type2 .
        ?type1 owl:disjointWith ?type2 .
        FILTER (?type1 != ?type2)
    }
    """
    try:
        partition_result = jena_client.sparql_query(partition_query)
        for binding in partition_result.get("results", {}).get("bindings", []):
            ind = binding.get("individual", {}).get("value", "")
            t1 = binding.get("type1", {}).get("value", "")
            t2 = binding.get("type2", {}).get("value", "")
            result.classification_errors.append(
                f"Individual {ind} has disjoint types {t1} and {t2}")
            result.consistent = False
    except Exception as e:
        result.classification_errors.append(
            f"Partition check failed: {e}")

    return result