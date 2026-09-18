"""
mork_communities/sparql_templates.py

SPARQL query templates for community and projection operations
against a remote triple store.

These implement the queries from §14 of the ontologic mapping addendum
and §B of the communities paper.
"""

from mork_communities.namespaces import MORK

# Prefix declarations shared by all templates
PREFIXES = """
PREFIX mork: <http://www.nebularis.org/ontologies/Mork#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX xsd:  <http://www.w3.org/2001/XMLSchema#>
PREFIX owl:  <http://www.w3.org/2002/07/owl#>
"""


MATCH_SECTION_AGAINST_COMMUNITIES = PREFIXES + """
SELECT ?community ?communityLabel ?matchWeight ?matchCount
WHERE {
    {
        SELECT ?community
               (SUM(?weight) AS ?matchWeight)
               (COUNT(?concept) AS ?matchCount)
        WHERE {
            ?community a mork:SemanticCommunity ;
                       mork:hasCommunityMembership ?membership .
            ?membership mork:memberConcept ?concept ;
                        mork:communityMemberWeight ?weight .
            FILTER(?concept IN (%(concept_iris)s))
        }
        GROUP BY ?community
    }
    OPTIONAL { ?community skos:prefLabel ?communityLabel }
    BIND(?matchWeight / ?matchCount AS ?matchScore)
}
ORDER BY DESC(?matchWeight)
LIMIT 5
"""


RETRIEVE_COMMUNITY_PROJECTION = PREFIXES + """
SELECT ?concept ?conceptLabel ?property ?propertyLabel
       ?parentClass ?parentClassLabel ?confidence ?frequency
WHERE {
    <%(community_iri)s> mork:hasOntologicalProjection ?proj .
    ?proj mork:hasPropertyProjection ?pp .
    ?pp mork:projectedConcept ?concept ;
        mork:projectedProperty ?property ;
        mork:projectedParentClass ?parentClass ;
        mork:propertyProjectionConfidence ?confidence ;
        mork:propertyProjectionFrequency ?frequency .
    OPTIONAL { ?concept skos:prefLabel ?conceptLabel }
    OPTIONAL { ?property mork:conceptName ?propertyLabel }
    OPTIONAL { ?parentClass mork:conceptName ?parentClassLabel }
}
ORDER BY ?concept DESC(?confidence)
"""


FIND_PROJECTION_FOR_CONCEPT = PREFIXES + """
SELECT ?property ?parentClass ?confidence ?frequency
WHERE {
    <%(community_iri)s> mork:hasOntologicalProjection ?proj .
    ?proj mork:hasPropertyProjection ?pp .
    ?pp mork:projectedConcept <%(concept_iri)s> ;
        mork:projectedProperty ?property ;
        mork:projectedParentClass ?parentClass ;
        mork:propertyProjectionConfidence ?confidence ;
        mork:propertyProjectionFrequency ?frequency .
}
ORDER BY DESC(?confidence) DESC(?frequency)
LIMIT 3
"""


RETRIEVE_DAG_TEMPLATE = PREFIXES + """
SELECT ?template ?rootClass ?rootLabel ?childConcept
       ?childConceptLabel ?childProperty ?childPropertyLabel
       ?frequency
WHERE {
    <%(community_iri)s> mork:hasOntologicalProjection ?proj .
    ?proj mork:hasDAGTemplate ?template .
    ?template mork:dagTemplateRoot ?rootClass ;
              mork:dagTemplateFrequency ?frequency ;
              mork:dagTemplateChild ?pp .
    OPTIONAL { ?rootClass mork:conceptName ?rootLabel }
    ?pp mork:projectedConcept ?childConcept ;
        mork:projectedProperty ?childProperty .
    OPTIONAL { ?childConcept skos:prefLabel ?childConceptLabel }
    OPTIONAL { ?childProperty mork:conceptName ?childPropertyLabel }
}
ORDER BY ?template DESC(?frequency) ?childConceptLabel
"""


RETRIEVE_ALL_COMMUNITIES = PREFIXES + """
SELECT ?community ?communityLabel ?concept ?conceptLabel
       ?weight ?coherence
WHERE {
    ?community a mork:SemanticCommunity ;
               mork:communityCoherence ?coherence ;
               mork:hasCommunityMembership ?membership .
    OPTIONAL { ?community skos:prefLabel ?communityLabel }
    ?membership mork:memberConcept ?concept ;
                mork:communityMemberWeight ?weight .
    OPTIONAL { ?concept skos:prefLabel ?conceptLabel }
}
ORDER BY ?community DESC(?weight)
"""


FIND_UNRESOLVED_COMMUNITY_CONCEPTS = PREFIXES + """
SELECT ?concept ?conceptLabel ?weight
WHERE {
    <%(community_iri)s> mork:hasCommunityMembership ?membership .
    ?membership mork:memberConcept ?concept ;
                mork:communityMemberWeight ?weight .
    OPTIONAL { ?concept skos:prefLabel ?conceptLabel }
    FILTER(?concept NOT IN (%(resolved_iris)s))
}
ORDER BY DESC(?weight)
"""


RETRIEVE_SECTION_OBSERVATIONS = PREFIXES + """
SELECT ?observation ?section ?scheme ?concept
WHERE {
    ?observation a mork:SectionObservation ;
                 mork:observedInSection ?section ;
                 mork:observedInScheme ?scheme ;
                 mork:observedConcept ?concept .
}
ORDER BY ?scheme ?section
"""


SHADOW_HIERARCHY_FOR_CLASS = PREFIXES + """
SELECT ?shadow ?iri ?label ?superShadow ?superIri
WHERE {
    ?shadow a mork:OwlClass ;
            mork:iri ?iri .
    OPTIONAL { ?shadow skos:prefLabel ?label }
    OPTIONAL {
        ?shadow mork:shadowSubClassOf ?superShadow .
        ?superShadow mork:iri ?superIri .
    }
    FILTER(?iri = "%(class_iri)s"
           || EXISTS { ?shadow mork:shadowSubClassOf*/mork:iri "%(class_iri)s" })
}
ORDER BY ?iri
"""


SHADOW_PROPERTIES_FOR_CLASS = PREFIXES + """
SELECT ?propShadow ?propIri ?propLabel ?propType
       ?rangeShadow ?rangeIri ?rangeLabel
WHERE {
    ?classShadow a mork:OwlClass ;
                 mork:iri "%(class_iri)s" .
    ?propShadow mork:shadowDomain ?classShadow ;
                mork:iri ?propIri .
    OPTIONAL { ?propShadow skos:prefLabel ?propLabel }
    ?propShadow a ?propType .
    FILTER(?propType IN (mork:OwlObjectProperty, mork:OwlDataProperty))
    OPTIONAL {
        ?propShadow mork:shadowRange ?rangeShadow .
        ?rangeShadow mork:iri ?rangeIri .
        OPTIONAL { ?rangeShadow skos:prefLabel ?rangeLabel }
    }
}
ORDER BY ?propIri
"""