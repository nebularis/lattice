"""
mork_tools.py

LangChain tool definitions for the MORK agent pipeline.

Each tool wraps a capability from the MORK infrastructure
with typed Pydantic input/output schemas. Tool scoping
(allowed_graphs) enforces layer independence (R1).

Implements:
  - Retrieval tools (§C.5, §D.4.2)
  - Validation tools (§D.4.2)
  - §D.4.1 tool categories
"""

from __future__ import annotations

from typing import List, Optional

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from mork_validation import validate_fragment, ValidationResult


# ─── Tool input schemas ───

class ClassContextInput(BaseModel):
    class_iri: str = Field(
        description="Full IRI of the OWL class to retrieve context for"
    )


class PathFindingInput(BaseModel):
    source_class: str = Field(
        description="Full IRI of the source class"
    )
    target_type: str = Field(
        description="Full IRI of the target class or datatype"
    )
    max_path_length: int = Field(
        default=3, ge=1, le=5,
        description="Maximum property steps in the path"
    )


class ConceptLookupInput(BaseModel):
    search_term: str = Field(
        description="Natural language term to search for"
    )
    scheme_iri: Optional[str] = Field(
        default=None,
        description="Optional: restrict to a specific concept scheme"
    )


class TemplateLookupInput(BaseModel):
    keyword: str = Field(
        description="Keyword to match against template descriptions"
    )


class ExistingMappingInput(BaseModel):
    target_iri: str = Field(
        description="Target ontology element IRI to search for"
    )


class ValidationInput(BaseModel):
    turtle_fragment: str = Field(
        description="Turtle fragment to validate"
    )


class ConflictDetectionInput(BaseModel):
    target_class: str = Field(
        description="Target class IRI to check for conflicts"
    )


# ─── Tool factory ───

def create_tools(
    graph_rag_client,
    template_library: dict,
    allowed_graphs: List[str],
    sparql_endpoint: Optional[str] = None,
    ontology_graph_uri: Optional[str] = None,
) -> list:
    """
    Create a scoped set of tools for a specific agent role.

    The allowed_graphs parameter enforces layer independence:
    tools check this list before executing any SPARQL query.
    """

    def _check_access(graph_uri: str) -> Optional[str]:
        """Return error message if graph is not accessible."""
        if graph_uri not in allowed_graphs:
            return (
                f"ACCESS DENIED: This agent cannot query "
                f"<{graph_uri}>. Allowed graphs: "
                f"{allowed_graphs}"
            )
        return None

    @tool(args_schema=ClassContextInput)
    def retrieve_class_context(class_iri: str) -> str:
        """Retrieve the structural context of an OWL class: its
        superclasses, properties with domains and ranges, and
        subclasses. Returns Turtle.

        ALWAYS call this tool BEFORE proposing any exactTBoxMatch,
        exactRBoxMatch, or sh:path expression."""
        error = _check_access("urn:mork:ontology:target")
        if error:
            return error
        result = graph_rag_client.execute(
            template_library["M1_ClassContext"],
            {"classIRI": class_iri},
        )
        return result.serialised_context

    @tool(args_schema=PathFindingInput)
    def find_property_paths(
        source_class: str,
        target_type: str,
        max_path_length: int = 3,
    ) -> str:
        """Find property paths connecting a source class to a
        target class or datatype. Returns path summaries suitable
        for constructing sh:path expressions.

        Call this tool to determine valid property paths before
        creating ShapeMapping parameter bindings."""
        error = _check_access("urn:mork:ontology:target")
        if error:
            return error
        result = graph_rag_client.execute(
            template_library["M2_PathFinding"],
            {
                "sourceClass": source_class,
                "targetType": target_type,
                "maxResults": str(max_path_length * 5),
            },
        )
        return result.serialised_context

    @tool(args_schema=ConceptLookupInput)
    def lookup_skos_concepts(
        search_term: str,
        scheme_iri: Optional[str] = None,
    ) -> str:
        """Search for SKOS concepts by label across vocabulary
        schemes. Returns a table of matching concepts with IRIs,
        labels, schemes, and broader concepts.

        Use this to ground entity references against controlled
        vocabularies (perils, jurisdictions, metrics, etc.)."""
        error = _check_access("urn:mork:skos:vocabularies")
        if error:
            return error
        params = {
            "searchTerm": search_term,
            "maxResults": "20",
        }
        result = graph_rag_client.execute(
            template_library["I1_ConceptLookup"],
            params,
        )
        return result.serialised_context

    @tool(args_schema=TemplateLookupInput)
    def find_templates(keyword: str) -> str:
        """Search for reusable ShapeTemplates or RuleTemplates.
        Returns matching templates with parameter descriptions.

        PREFER instantiating existing templates over creating
        ad hoc ShapeMappings or RuleMappings."""
        error = _check_access("urn:mork:mappings:templates")
        if error:
            return error
        result = graph_rag_client.execute(
            template_library["M3_TemplateMatch"],
            {"keyword": keyword},
        )
        return result.serialised_context

    @tool(args_schema=ExistingMappingInput)
    def find_existing_mappings(target_iri: str) -> str:
        """Search for existing DataMappings targeting the specified
        ontology element. Returns mappings with weighting and notes.

        REUSE existing mappings with weighting >= 70 when possible."""
        error = _check_access("urn:mork:mappings:active")
        if error:
            return error
        result = graph_rag_client.execute(
            template_library["M4_ExistingMappings"],
            {"targetIRI": target_iri},
        )
        return result.serialised_context

    @tool(args_schema=ValidationInput)
    def validate_mork_fragment(turtle_fragment: str) -> str:
        """Validate a Turtle fragment against MORK GCI axioms,
        structural completeness constraints, and precedence
        acyclicity.

        ALWAYS call this tool before finalising generated mappings."""
        result = validate_fragment(
            turtle_fragment,
            sparql_endpoint=sparql_endpoint,
            ontology_graph_uri=ontology_graph_uri,
        )
        if result.valid:
            summary = "VALID: All GCI and structural checks passed."
        else:
            summary = "INVALID:\n" + "\n".join(
                f"  ✗ {v}" for v in result.violations
            )
        if result.warnings:
            summary += "\nWARNINGS:\n" + "\n".join(
                f"  ⚠ {w}" for w in result.warnings
            )
        return summary

    @tool(args_schema=ConflictDetectionInput)
    def detect_conflicts(target_class: str) -> str:
        """Check for existing constraints that may conflict with
        a proposed mapping on the specified target class."""
        error = _check_access("urn:mork:constraints:active")
        if error:
            return error
        result = graph_rag_client.execute(
            template_library["R1_ConflictDetection"],
            {"targetClass": target_class},
        )
        return result.serialised_context

    # Return only tools whose required graphs are accessible
    all_tools = []

    if "urn:mork:ontology:target" in allowed_graphs:
        all_tools.extend([retrieve_class_context, find_property_paths])

    if "urn:mork:skos:vocabularies" in allowed_graphs:
        all_tools.append(lookup_skos_concepts)

    if "urn:mork:mappings:templates" in allowed_graphs:
        all_tools.append(find_templates)

    if "urn:mork:mappings:active" in allowed_graphs:
        all_tools.append(find_existing_mappings)

    # Validation is always available
    all_tools.append(validate_mork_fragment)

    if "urn:mork:constraints:active" in allowed_graphs:
        all_tools.append(detect_conflicts)

    return all_tools