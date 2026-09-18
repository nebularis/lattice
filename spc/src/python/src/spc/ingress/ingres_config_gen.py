# src/spc/ingress/ingress_config_gen.py
"""
Generate ingress configuration JSON from MORK mappings.

Reads MORK mapping individuals from the Jena store and produces
the ingress_registry.json consumed by the Elixir SpcBoundary.Ingress
module at runtime.
"""

from __future__ import annotations
from pathlib import Path
from typing import Any, Optional

from spc.verify.jena_client import JenaClient
from spc.util.json_ser import write_json


class IngressConfigGenerator:
    """Generate ingress configuration from MORK mappings."""

    def __init__(self, jena_client: JenaClient):
        self.jena = jena_client

    def generate(self) -> dict[str, Any]:
        """Generate the ingress registry mapping source schemas to configs."""
        query = """
        PREFIX mork: <http://mork.marsh.com/ontology#>
        PREFIX spc: <http://spc.marsh.com/ontology/core#>
        SELECT ?mapping ?sourceSchema ?targetConcept ?targetConceptIRI
               ?identityTemplate ?sessionField ?label ?participant
        WHERE {
            ?mapping a mork:IngressMapping .
            ?mapping mork:hasSourceSchema ?sourceSchema .
            ?mapping mork:hasTargetConcept ?targetConcept .
            ?mapping mork:hasTargetConceptIRI ?targetConceptIRI .
            OPTIONAL { ?mapping mork:hasIdentityTemplate ?identityTemplate . }
            OPTIONAL { ?mapping mork:hasSessionField ?sessionField . }
            OPTIONAL { ?mapping mork:bindsToLabel ?label . }
            OPTIONAL { ?mapping mork:bindsToParticipant ?pIri .
                       ?pIri spc:hasRoleName ?participant . }
        }
        """
        results = self.jena.sparql_query(query)
        registry: dict[str, Any] = {}

        for b in results.get("results", {}).get("bindings", []):
            mapping_iri = b["mapping"]["value"]
            schema = b["sourceSchema"]["value"]

            config: dict[str, Any] = {
                "source_schema": schema,
                "target_concept": _val(b, "targetConcept") or "",
                "target_concept_iri": _val(b, "targetConceptIRI") or "",
                "identity_template": _val(b, "identityTemplate") or "",
                "identity_fields": [],
                "field_mappings": [],
                "session_field": _val(b, "sessionField") or "session_id",
                "label": _val(b, "label") or "",
                "participant": _val(b, "participant") or "",
            }

            # Fetch identity fields
            id_query = f"""
            PREFIX mork: <http://mork.marsh.com/ontology#>
            SELECT ?field WHERE {{
                <{mapping_iri}> mork:hasIdentityField ?field .
            }}
            """
            id_results = self.jena.sparql_query(id_query)
            config["identity_fields"] = [
                fb["field"]["value"]
                for fb in id_results.get("results", {}).get("bindings", [])
            ]

            # Fetch field mappings
            fm_query = f"""
            PREFIX mork: <http://mork.marsh.com/ontology#>
            SELECT ?fm ?sourcePath ?targetProp ?datatype ?required
            WHERE {{
                <{mapping_iri}> mork:hasFieldMapping ?fm .
                ?fm mork:hasSourcePath ?sourcePath .
                ?fm mork:hasTargetProperty ?targetProp .
                OPTIONAL {{ ?fm mork:hasDatatype ?datatype . }}
                OPTIONAL {{ ?fm mork:isRequired ?required . }}
            }}
            """
            fm_results = self.jena.sparql_query(fm_query)
            for fmb in fm_results.get("results", {}).get("bindings", []):
                fm_config: dict[str, Any] = {
                    "source_path": fmb["sourcePath"]["value"],
                    "target_property": fmb["targetProp"]["value"],
                    "datatype": _val(fmb, "datatype") or "xsd:string",
                    "required": _val(fmb, "required") == "true",
                }

                # Fetch value map if present
                vm_query = f"""
                PREFIX mork: <http://mork.marsh.com/ontology#>
                SELECT ?sourceVal ?targetVal WHERE {{
                    <{fmb['fm']['value']}> mork:hasValueMap ?vm .
                    ?vm mork:mapsFromValue ?sourceVal .
                    ?vm mork:mapsToValue ?targetVal .
                }}
                """
                vm_results = self.jena.sparql_query(vm_query)
                vmap = {}
                for vmb in vm_results.get("results", {}).get("bindings", []):
                    vmap[vmb["sourceVal"]["value"]] = vmb["targetVal"]["value"]
                if vmap:
                    fm_config["value_map"] = vmap

                config["field_mappings"].append(fm_config)

            registry[schema] = config

        return registry

    def generate_to_file(self, path: Path) -> None:
        """Generate and write to file."""
        registry = self.generate()
        write_json(registry, path)


def _val(binding: dict, key: str) -> Optional[str]:
    entry = binding.get(key)
    return entry.get("value") if entry else None