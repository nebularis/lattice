# src/spc/extract/shape_extractor.py
"""
Extract SHACL payload validation shapes from refinement predicates.

For each message label with a refinement predicate {x ∈ C}, generate
a SHACL NodeShape that validates an individual for membership in C.
"""

from __future__ import annotations
from pathlib import Path
from rdflib import Graph, URIRef, Literal, BNode, RDF, RDFS
from spc.util.namespaces import SH, SPC, bind_namespaces
from spc.verify.jena_client import JenaClient


class ShapeExtractor:
    """Extract SHACL shapes from refinement predicates in the A-Box."""

    def __init__(self, jena_client: JenaClient):
        self.jena = jena_client

    def extract_all(self, output_dir: Path) -> dict[str, str]:
        """
        Extract shapes for all refinement predicates.
        Returns a mapping from label to shape file path.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        shape_map: dict[str, str] = {}

        # Query all message options with refinement predicates
        query = """
        PREFIX spc: <http://spc.marsh.com/ontology/core#>
        SELECT ?option ?label ?concept
        WHERE {
            ?option a spc:MessageOption .
            ?option spc:hasOptionLabel ?label .
            ?option spc:hasRefinementPredicate ?pred .
            ?pred a spc:ConceptMembershipPredicate .
            ?pred spc:hasTargetConcept ?concept .
        }
        """
        results = self.jena.sparql_query(query)

        for binding in results.get("results", {}).get("bindings", []):
            label = binding["label"]["value"]
            concept_iri = binding["concept"]["value"]

            shape_graph = self._generate_shape_for_concept(
                label, concept_iri)

            filename = f"{label}.ttl"
            filepath = output_dir / filename
            shape_graph.serialize(destination=str(filepath), format="turtle")
            shape_map[label] = str(filepath)

        return shape_map

    def _generate_shape_for_concept(
        self, label: str, concept_iri: str
    ) -> Graph:
        """Generate a SHACL shape for a concept membership predicate."""
        g = Graph()
        bind_namespaces(g)

        shape_iri = URIRef(f"http://spc.marsh.com/shapes/{label}Shape")
        concept = URIRef(concept_iri)

        g.add((shape_iri, RDF.type, SH.NodeShape))
        g.add((shape_iri, SH.targetClass, concept))

        # Query the ontology for necessary properties of the concept
        props_query = f"""
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        SELECT DISTINCT ?property ?range ?minCard
        WHERE {{
            <{concept_iri}> rdfs:subClassOf ?restriction .
            ?restriction a owl:Restriction .
            ?restriction owl:onProperty ?property .
            OPTIONAL {{ ?restriction owl:someValuesFrom ?range . }}
            OPTIONAL {{ ?restriction owl:minCardinality ?minCard . }}
        }}
        """
        try:
            props_result = self.jena.sparql_query(props_query)
            for pb in props_result.get("results", {}).get("bindings", []):
                prop_iri = URIRef(pb["property"]["value"])
                prop_shape = BNode()
                g.add((shape_iri, SH.property, prop_shape))
                g.add((prop_shape, SH.path, prop_iri))
                g.add((prop_shape, SH.minCount, Literal(1)))

                if "range" in pb:
                    range_iri = URIRef(pb["range"]["value"])
                    # Determine if range is a datatype or class
                    if "XMLSchema" in str(range_iri):
                        g.add((prop_shape, SH.datatype, range_iri))
                    else:
                        g.add((prop_shape, SH.node,
                               URIRef(f"http://spc.marsh.com/shapes/"
                                      f"{range_iri.split('#')[-1]}Shape")))
        except Exception:
            # If the ontology query fails, generate a minimal shape
            pass

        return g