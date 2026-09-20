# src/spc/ingress/egress_config_gen.py
"""
Generate egress configuration: SPARQL query templates, JSON-LD frames,
and the query registry JSON.
"""

from __future__ import annotations
from pathlib import Path
from typing import Any, Optional

from spc.verify.jena_client import JenaClient
from spc.util.json_ser import write_json


class EgressConfigGenerator:
    """Generate egress query templates and configuration."""

    def __init__(self, jena_client: JenaClient):
        self.jena = jena_client

    def generate(self, output_dir: Path) -> dict[str, Any]:
        """
        Generate all egress artifacts:
        - SPARQL query templates (.rq files)
        - JSON-LD frames (.jsonld files)
        - Query registry (JSON config)

        Returns the query registry dict.
        """
        queries_dir = output_dir / "queries"
        frames_dir = output_dir / "frames"
        queries_dir.mkdir(parents=True, exist_ok=True)
        frames_dir.mkdir(parents=True, exist_ok=True)

        # Query all egress mappings from MORK
        query = """
        PREFIX mork: <http://mork.marsh.com/ontology#>
        PREFIX spc: <http://spc.marsh.com/ontology/core#>
        SELECT ?mapping ?name ?targetConcept ?targetConceptIRI
               ?outputFormat
        WHERE {
            ?mapping a mork:EgressMapping .
            ?mapping mork:hasTemplateName ?name .
            ?mapping mork:hasTargetConcept ?targetConcept .
            ?mapping mork:hasTargetConceptIRI ?targetConceptIRI .
            OPTIONAL { ?mapping mork:hasOutputFormat ?outputFormat . }
        }
        """
        results = self.jena.sparql_query(query)
        registry: dict[str, Any] = {}

        for b in results.get("results", {}).get("bindings", []):
            mapping_iri = b["mapping"]["value"]
            template_name = b["name"]["value"]
            concept_iri = b["targetConceptIRI"]["value"]
            output_format = _val(b, "outputFormat") or "json-ld"

            # Generate the SPARQL CONSTRUCT query template
            sparql = self._generate_construct_template(
                mapping_iri, concept_iri)
            template_path = queries_dir / f"{template_name}.rq"
            template_path.write_text(sparql)

            # Generate JSON-LD frame if applicable
            frame_path = None
            if output_format == "json-ld":
                frame = self._generate_jsonld_frame(mapping_iri, concept_iri)
                frame_path = frames_dir / f"{template_name}.jsonld"
                import json
                frame_path.write_text(json.dumps(frame, indent=2))

            # Fetch parameters
            params = self._fetch_parameters(mapping_iri)

            registry[template_name] = {
                "template_file": str(template_path),
                "template": sparql,
                "parameters": params,
                "output_format": output_format,
                "frame_file": str(frame_path) if frame_path else None,
                "pre_compiled": True,
            }

        return registry

    def generate_to_file(self, output_dir: Path) -> None:
        """Generate all artifacts and write query registry."""
        registry = self.generate(output_dir)
        write_json(registry, output_dir / "query_registry.json")

    def _generate_construct_template(
        self, mapping_iri: str, concept_iri: str
    ) -> str:
        """Generate a SPARQL CONSTRUCT template for an egress mapping."""
        # Fetch the field mappings (reverse direction)
        fm_query = f"""
        PREFIX mork: <http://mork.marsh.com/ontology#>
        SELECT ?targetProp ?datatype
        WHERE {{
            <{mapping_iri}> mork:hasFieldMapping ?fm .
            ?fm mork:hasTargetProperty ?targetProp .
            OPTIONAL {{ ?fm mork:hasDatatype ?datatype . }}
        }}
        """
        fm_results = self.jena.sparql_query(fm_query)
        properties = []
        for fb in fm_results.get("results", {}).get("bindings", []):
            properties.append(fb["targetProp"]["value"])

        # Build CONSTRUCT clause
        construct_triples = [f"  ?entity a <{concept_iri}> ."]
        where_triples = [f"  ?entity a <{concept_iri}> ."]
        for prop in properties:
            var_name = prop.split("#")[-1].split("/")[-1]
            construct_triples.append(
                f"  ?entity <{prop}> ?{var_name} .")
            where_triples.append(
                f"  OPTIONAL {{ ?entity <{prop}> ?{var_name} . }}")

        # Add session filter parameter
        where_triples.append(
            "  FILTER (?entity = ?entityIri)")

        construct = "\n".join(construct_triples)
        where = "\n".join(where_triples)

        return f"""CONSTRUCT {{
{construct}
}}
WHERE {{
{where}
}}"""

    def _generate_jsonld_frame(
        self, mapping_iri: str, concept_iri: str
    ) -> dict:
        """Generate a JSON-LD frame for an egress mapping."""
        fm_query = f"""
        PREFIX mork: <http://mork.marsh.com/ontology#>
        SELECT ?sourcePath ?targetProp
        WHERE {{
            <{mapping_iri}> mork:hasFieldMapping ?fm .
            ?fm mork:hasSourcePath ?sourcePath .
            ?fm mork:hasTargetProperty ?targetProp .
        }}
        """
        fm_results = self.jena.sparql_query(fm_query)

        context: dict[str, str] = {}
        for fb in fm_results.get("results", {}).get("bindings", []):
            source_name = fb["sourcePath"]["value"]
            target_prop = fb["targetProp"]["value"]
            context[source_name] = target_prop

        return {
            "@context": context,
            "@type": concept_iri,
        }

    def _fetch_parameters(self, mapping_iri: str) -> dict[str, dict]:
        """Fetch query parameter definitions."""
        # Standard parameters for all egress queries
        return {
            "entityIri": {"type": "iri", "required": True},
        }


def _val(binding: dict, key: str) -> Optional[str]:
    entry = binding.get(key)
    return entry.get("value") if entry else None