"""Public exports for the mork_communities package."""

__version__ = "0.2.0"

from .communities import (
    SemanticCommunity,
    CommunityScheme,
    CommunityDiscovery,
)
from .projections import (
    OntologicalProjection,
    PropertyProjection,
    DAGTemplate,
    ProjectionExtractor,
)
from .shadow import ShadowOntologyBuilder
from .inference import TriStratumResolver
from .matching import CommunityMatcher
from .scoring import BayesianScorer
from .recognition import (
    RecognitionEngine,
    AbbreviationDictionary,
    RecognitionCandidate,
)
from .type_compatibility import TypeCompatibilityEngine
from .axiom_intent import (
    AxiomIntentProfiler,
    AxiomAlignmentScorer,
    AxiomIntentProfile,
)
from .precedence import (
    PrecedenceDeriver,
    DAGEvaluator,
    IdentityTemplateResolver,
)
from .aggregator import FullBayesianAggregator, FullEvidenceBundle
from .dag_instantiation import DAGTemplateInstantiator
from .confidence import ConfidencePropagator

__all__ = [
    "SemanticCommunity",
    "CommunityScheme",
    "CommunityDiscovery",
    "OntologicalProjection",
    "PropertyProjection",
    "DAGTemplate",
    "ProjectionExtractor",
    "ShadowOntologyBuilder",
    "TriStratumResolver",
    "CommunityMatcher",
    "BayesianScorer",
    "RecognitionEngine",
    "AbbreviationDictionary",
    "RecognitionCandidate",
    "TypeCompatibilityEngine",
    "AxiomIntentProfiler",
    "AxiomAlignmentScorer",
    "AxiomIntentProfile",
    "PrecedenceDeriver",
    "DAGEvaluator",
    "IdentityTemplateResolver",
    "FullBayesianAggregator",
    "FullEvidenceBundle",
    "DAGTemplateInstantiator",
    "ConfidencePropagator",
]
