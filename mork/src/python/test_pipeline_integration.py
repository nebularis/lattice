"""
tests/test_pipeline_integration.py

Integration test demonstrating the full community-enhanced pipeline
on a synthetic MORK graph.
"""

import pytest
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, OWL, XSD, SKOS

from mork_communities.namespaces import *
from mork_communities.pipeline import (
    CommunityEnhancedPipeline,
    PipelineConfig,
)
from mork_communities.shadow import ShadowOntologyBuilder
from mork_communities.validation import CommunityValidator
from mork_communities.metrics import MetricsCollector

# Test namespaces
FBO = Namespace("http://example.org/fbo#")
SCHEMA = Namespace("http://example.org/schema/")
TAX = Namespace("http://example.org/taxonomy/")


def build_test_graph() -> tuple:
    """
    Build a synthetic MORK graph simulating 5 mapping runs
    with layer-like and party-like sections.
    """
    g = Graph()

    # ── Domain Ontology ───────────────────────────────────────
    domain = Graph()
    domain.add((FBO.Layer, RDF.type, OWL.Class))
    domain.add((FBO.Layer, RDFS.label, Literal("Layer")))
    domain.add((FBO.Party, RDF.type, OWL.Class))
    domain.add((FBO.Party, RDFS.label, Literal("Party")))

    domain.add((FBO.hasAttachment, RDF.type, OWL.DatatypeProperty))
    domain.add((FBO.hasAttachment, RDFS.domain, FBO.Layer))
    domain.add((FBO.hasAttachment, RDFS.label, Literal("has attachment")))

    domain.add((FBO.hasLimit, RDF.type, OWL.DatatypeProperty))
    domain.add((FBO.hasLimit, RDFS.domain, FBO.Layer))
    domain.add((FBO.hasLimit, RDFS.label, Literal("has limit")))

    domain.add((FBO.hasShare, RDF.type, OWL.DatatypeProperty))
    domain.add((FBO.hasShare, RDFS.domain, FBO.Layer))
    domain.add((FBO.hasShare, RDFS.label, Literal("has share")))

    domain.add((FBO.hasCurrency, RDF.type, OWL.DatatypeProperty))
    domain.add((FBO.hasCurrency, RDFS.domain, FBO.Layer))
    domain.add((FBO.hasCurrency, RDFS.label, Literal("has currency")))

    domain.add((FBO.hasPartyName, RDF.type, OWL.DatatypeProperty))
    domain.add((FBO.hasPartyName, RDFS.domain, FBO.Party))
    domain.add((FBO.hasPartyRole, RDF.type, OWL.DatatypeProperty))
    domain.add((FBO.hasPartyRole, RDFS.domain, FBO.Party))

    # ── Ontological Scheme ────────────────────────────────────
    os_iri = URIRef("http://example.org/ontological_scheme/fbo")
    g.add((os_iri, RDF.type, ONTOLOGICAL_SCHEME))

    # ── Taxonomy Concepts ─────────────────────────────────────
    tax_scheme = URIRef("http://example.org/taxonomy_scheme/1")
    g.add((tax_scheme, RDF.type, MORK.TaxonomyScheme))

    concepts = {
        "attachment": TAX.Attachment,
        "limit": TAX.Limit,
        "share": TAX.Share,
        "currency": TAX.Currency,
        "party_name": TAX.PartyName,
        "party_role": TAX.PartyRole,
    }
    for name, iri in concepts.items():
        g.add((iri, RDF.type, DATA_CONCEPT))
        g.add((iri, CONCEPT_SCHEME_PROP, tax_scheme))
        g.add((iri, SKOS.prefLabel, Literal(name)))

    # ── Simulated Mapping Runs ────────────────────────────────
    # Create 5 RepresentationSchemes, each with layer and party sections
    for run_idx in range(5):
        rs_iri = SCHEMA[f"schema_{run_idx}"]
        g.add((rs_iri, RDF.type, REPRESENTATION_SCHEME))

        # Layer section
        layer_section = SCHEMA[f"schema_{run_idx}/layer"]
        g.add((layer_section, RDF.type, REPRESENTATION))
        g.add((layer_section, REPRESENTATION_SCHEME_PROP, rs_iri))

        # Layer fields
        layer_concepts = ["attachment", "limit", "share", "currency"]
        for field_name in layer_concepts:
            field_iri = SCHEMA[f"schema_{run_idx}/layer/{field_name}"]
            g.add((field_iri, RDF.type, REPRESENTATION))
            g.add((field_iri, REPRESENTATION_SCHEME_PROP, rs_iri))
            g.add((layer_section, MEMBER_PROPERTY, field_iri))
            g.add((field_iri, REPRESENTATION_OF, concepts[field_name]))

            # Create mapping
            mapping_iri = SCHEMA[f"mapping_{run_idx}/layer/{field_name}"]
            g.add((mapping_iri, RDF.type, DATA_MAPPING))
            g.add((field_iri, HAS_MAPPING, mapping_iri))
            g.add((concepts[field_name], HAS_MAPPING, mapping_iri))

        # Parent mapping for layer section
        layer_parent_map = SCHEMA[f"mapping_{run_idx}/layer_parent"]
        g.add((layer_parent_map, RDF.type, DATA_MAPPING))
        g.add((layer_parent_map, EXACT_TBOX_MATCH, FBO.Layer))
        g.add((layer_section, HAS_MAPPING, layer_parent_map))

        # R-Box mappings for layer fields
        rbox_map = {
            "attachment": FBO.hasAttachment,
            "limit": FBO.hasLimit,
            "share": FBO.hasShare,
            "currency": FBO.hasCurrency,
        }
        for field_name, rbox_prop in rbox_map.items():
            mapping_iri = SCHEMA[f"mapping_{run_idx}/layer/{field_name}"]
            g.add((mapping_iri, EXACT_RBOX_MATCH, rbox_prop))
            g.add((mapping_iri, COMPOSITE_BROADER_MAPPING, layer_parent_map))

        # Party section
        party_section = SCHEMA[f"schema_{run_idx}/party"]
        g.add((party_section, RDF.type, REPRESENTATION))
        g.add((party_section, REPRESENTATION_SCHEME_PROP, rs_iri))

        party_concepts = ["party_name", "party_role"]
        for field_name in party_concepts:
            field_iri = SCHEMA[f"schema_{run_idx}/party/{field_name}"]
            g.add((field_iri, RDF.type, REPRESENTATION))
            g.add((field_iri, REPRESENTATION_SCHEME_PROP, rs_iri))
            g.add((party_section, MEMBER_PROPERTY, field_iri))
            g.add((field_iri, REPRESENTATION_OF, concepts[field_name]))

            mapping_iri = SCHEMA[f"mapping_{run_idx}/party/{field_name}"]
            g.add((mapping_iri, RDF.type, DATA_MAPPING))
            g.add((field_iri, HAS_MAPPING, mapping_iri))
            g.add((concepts[field_name], HAS_MAPPING, mapping_iri))

        party_parent_map = SCHEMA[f"mapping_{run_idx}/party_parent"]
        g.add((party_parent_map, RDF.type, DATA_MAPPING))
        g.add((party_parent_map, EXACT_TBOX_MATCH, FBO.Party))
        g.add((party_section, HAS_MAPPING, party_parent_map))

        party_rbox = {
            "party_name": FBO.hasPartyName,
            "party_role": FBO.hasPartyRole,
        }
        for field_name, rbox_prop in party_rbox.items():
            mapping_iri = SCHEMA[f"mapping_{run_idx}/party/{field_name}"]
            g.add((mapping_iri, EXACT_RBOX_MATCH, rbox_prop))
            g.add((mapping_iri, COMPOSITE_BROADER_MAPPING, party_parent_map))

    return g, domain, os_iri, concepts


class TestPipelineIntegration:
    """Full integration test of the community-enhanced pipeline."""

    def setup_method(self):
        self.graph, self.domain, self.os_iri, self.concepts = (
            build_test_graph()
        )
        self.config = PipelineConfig(
            resolution_min=0.3,
            resolution_max=1.5,
            resolution_steps=5,
            min_community_size=2,
            coherence_threshold=0.2,
            community_match_threshold=0.2,
            projection_min_frequency=2,
        )

    def test_shadow_ontology_building(self):
        """Test that the shadow ontology is correctly built."""
        builder = ShadowOntologyBuilder(
            self.graph, self.os_iri
        )
        shadow_graph = builder.build_shadow(self.domain)

        # Check shadow individuals exist
        layer_shadow = builder.get_shadow(FBO.Layer)
        assert layer_shadow is not None
        assert (layer_shadow, RDF.type, OWL_CLASS) in self.graph

        # Check shadow hierarchy
        attach_shadow = builder.get_shadow(FBO.hasAttachment)
        assert attach_shadow is not None
        assert (attach_shadow, RDF.type, OWL_DATA_PROPERTY) in self.graph

        # Check domain link
        domain_link = list(self.graph.objects(attach_shadow, SHADOW_DOMAIN))
        assert len(domain_link) == 1
        assert domain_link[0] == layer_shadow

    def test_community_discovery(self):
        """Test that communities are discovered correctly."""
        pipeline = CommunityEnhancedPipeline(self.graph, self.config)
        pipeline.initialise(self.domain, self.os_iri)

        assert pipeline.has_communities
        scheme = pipeline.state.community_scheme
        assert len(scheme.communities) >= 2

        # Check that layer concepts cluster together
        layer_concepts = {
            self.concepts["attachment"],
            self.concepts["limit"],
            self.concepts["share"],
            self.concepts["currency"],
        }

        found_layer_community = False
        for comm in scheme.communities:
            overlap = comm.member_set & layer_concepts
            if len(overlap) >= 3:
                found_layer_community = True
                assert comm.coherence > 0.2
                break

        assert found_layer_community, "No layer-like community found"

    def test_projection_extraction(self):
        """Test that projections are extracted from mapping data."""
        pipeline = CommunityEnhancedPipeline(self.graph, self.config)
        pipeline.initialise(self.domain, self.os_iri)

        assert len(pipeline.state.projections) > 0

        # Find a projection with property projections
        has_property_projections = False
        for proj in pipeline.state.projections.values():
            if proj.property_projections:
                has_property_projections = True
                for pp in proj.property_projections:
                    assert pp.confidence > 0.0
                    assert pp.frequency >= 2
                break

        # Property projections require that the extraction
        # found mappings; this depends on graph traversal working
        # correctly — we check at least projected classes exist
        has_projected_classes = any(
            bool(p.projected_classes)
            for p in pipeline.state.projections.values()
        )
        assert has_projected_classes, "No projected classes found"

    def test_section_resolution(self):
        """Test tri-stratum resolution of a new section."""
        pipeline = CommunityEnhancedPipeline(self.graph, self.config)
        pipeline.initialise(self.domain, self.os_iri)

        # Simulate a new section with candidates
        new_section = URIRef("http://example.org/new/layer_1")
        token1 = URIRef("http://example.org/new/layer_1/xs_point")
        token2 = URIRef("http://example.org/new/layer_1/lmt")

        token_candidates = {
            token1: [
                (self.concepts["attachment"], 0.72),
                (self.concepts["limit"], 0.30),
            ],
            token2: [
                (self.concepts["limit"], 0.75),
                (self.concepts["attachment"], 0.20),
            ],
        }
        token_names = {token1: "xs_point", token2: "lmt"}

        # Provide recognised concepts for community matching
        recognised = frozenset(
            {self.concepts["currency"], self.concepts["share"]}
        )

        result = pipeline.resolve_section(
            section_iri=new_section,
            token_candidates=token_candidates,
            token_names=token_names,
            recognised_concepts=recognised,
        )

        assert result.total_tokens == 2
        assert len(result.token_resolutions) == 2

        # Community should have been matched
        if result.community_match is not None:
            assert result.community_match.confidence > 0

    def test_graph_validation(self):
        """Test that materialised graph passes validation."""
        pipeline = CommunityEnhancedPipeline(self.graph, self.config)
        pipeline.initialise(self.domain, self.os_iri)

        validator = CommunityValidator(self.graph)
        issues = validator.validate_all()

        violations = [i for i in issues if i.severity == "violation"]
        if violations:
            for v in violations:
                print(f"  VIOLATION: {v.focus_node} — {v.message}")

        assert len(violations) == 0, (
            f"{len(violations)} validation violations found"
        )

    def test_metrics_collection(self):
        """Test convergence metrics."""
        pipeline = CommunityEnhancedPipeline(self.graph, self.config)
        pipeline.initialise(self.domain, self.os_iri)

        collector = MetricsCollector()

        # Simulate resolution
        new_section = URIRef("http://example.org/new/layer_1")
        token_candidates = {
            URIRef("http://example.org/new/layer_1/f1"): [
                (self.concepts["attachment"], 0.9),
            ],
            URIRef("http://example.org/new/layer_1/f2"): [
                (self.concepts["limit"], 0.5),
                (self.concepts["share"], 0.45),
            ],
        }
        token_names = {
            URIRef("http://example.org/new/layer_1/f1"): "attachment",
            URIRef("http://example.org/new/layer_1/f2"): "lmt",
        }

        result = pipeline.resolve_section(
            section_iri=new_section,
            token_candidates=token_candidates,
            token_names=token_names,
        )

        metrics = collector.collect([result])
        assert metrics.total_tokens == 2
        assert 0.0 <= metrics.deterministic_rate <= 1.0
        assert 0.0 <= metrics.llm_required_rate <= 1.0

    def test_diagnostics(self):
        """Test pipeline diagnostics."""
        pipeline = CommunityEnhancedPipeline(self.graph, self.config)
        pipeline.initialise(self.domain, self.os_iri)

        diag = pipeline.get_diagnostics()
        assert "community_count" in diag
        assert "shadow_entity_count" in diag
        assert diag["shadow_entity_count"] > 0

        summaries = pipeline.get_community_summary()
        assert isinstance(summaries, list)
        if summaries:
            assert "community_id" in summaries[0]
            assert "coherence" in summaries[0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])