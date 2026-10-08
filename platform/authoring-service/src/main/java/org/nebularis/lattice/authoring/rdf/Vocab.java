// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.rdf;

import org.apache.jena.rdf.model.Property;
import org.apache.jena.rdf.model.Resource;
import org.apache.jena.rdf.model.ResourceFactory;

/**
 * Every IRI constant the word authoring POC's Java code writes into RDF: the {@code wrd:} terms
 * provisionally taken from the computable contract substrate sketch, and the POC's own
 * {@code wap:} terms (plan \u00a72.3, \u00a72.6). The only place these strings are written in Java; see
 * {@code src/main/resources/vocab/wording-provisional.ttl} for their documentation.
 */
public final class Vocab {
    public static final String WRD_NS = "https://www.nebularis.org/neuro-semantic/lattice/wording#";
    public static final String INS_NS = "https://www.nebularis.org/neuro-semantic/lattice/instrument#";
    public static final String WAP_NS = "https://www.nebularis.org/neuro-semantic/lattice/poc/word-authoring#";
    public static final String PROV_NS = "http://www.w3.org/ns/prov#";
    public static final String DCTERMS_NS = "http://purl.org/dc/terms/";
    public static final String RDFS_NS = "http://www.w3.org/2000/01/rdf-schema#";

    // wrd: classes
    public static final Resource WRD_WORDING = resource(WRD_NS, "Wording");
    public static final Resource WRD_ELEMENT = resource(WRD_NS, "Element");
    public static final Resource WRD_TEXT = resource(WRD_NS, "Text");
    public static final Resource WRD_TEXT_PART = resource(WRD_NS, "TextPart");
    public static final Resource WRD_EMBEDDED_VARIABLE = resource(WRD_NS, "EmbeddedVariable");

    // wrd: properties
    public static final Property WRD_DIRECTLY_COMPRISES = property(WRD_NS, "directlyComprises");
    public static final Property WRD_RANK_KEY = property(WRD_NS, "rankKey");
    public static final Property WRD_OBJECT_ID = property(WRD_NS, "objectId");
    public static final Property WRD_ELEMENT_TYPE = property(WRD_NS, "elementType");
    public static final Property WRD_PART_INDEX = property(WRD_NS, "partIndex");
    public static final Property WRD_PART_TEXT = property(WRD_NS, "partText");
    public static final Property WRD_REFERS_TO_VARIABLE = property(WRD_NS, "refersToVariable");
    public static final Property WRD_REFERS_TO_OBJECT = property(WRD_NS, "refersToObject");
    public static final Property WRD_VARIABLE_KEY = property(WRD_NS, "variableKey");

    // wap: classes
    public static final Resource WAP_DEFINITION_TEXT = resource(WAP_NS, "DefinitionText");
    public static final Resource WAP_AUTHORING_DOCUMENT = resource(WAP_NS, "AuthoringDocument");
    public static final Resource WAP_REVISION = resource(WAP_NS, "Revision");

    // wap: concepts (values of wrd:elementType and wap:valueType, not rdf:type targets)
    public static final Resource WAP_SECTION = resource(WAP_NS, "Section");
    public static final Resource WAP_CLAUSE = resource(WAP_NS, "Clause");
    public static final Resource WAP_DEFINITION = resource(WAP_NS, "Definition");

    // wap: properties
    public static final Property WAP_DOCUMENT_ID = property(WAP_NS, "documentId");
    public static final Property WAP_TEMPLATE_ID = property(WAP_NS, "templateId");
    public static final Property WAP_REVISION_NUMBER = property(WAP_NS, "revisionNumber");
    public static final Property WAP_SECTION_KEY = property(WAP_NS, "sectionKey");
    public static final Property WAP_ELEMENT_ID = property(WAP_NS, "elementId");
    public static final Property WAP_PLAIN_TEXT = property(WAP_NS, "plainText");
    public static final Property WAP_DEFINED_TERM = property(WAP_NS, "definedTerm");
    public static final Property WAP_HAS_PART = property(WAP_NS, "hasPart");
    public static final Property WAP_DISPLAY_TEXT = property(WAP_NS, "displayText");
    public static final Property WAP_VALUE_TYPE = property(WAP_NS, "valueType");
    public static final Property WAP_LATEST_REVISION = property(WAP_NS, "latestRevision");
    public static final Property WAP_REVISION_OF = property(WAP_NS, "revisionOf");
    public static final Property WAP_WORDING_GRAPH = property(WAP_NS, "wordingGraph");
    public static final Property WAP_REVISION_HASH = property(WAP_NS, "revisionHash");
    public static final Property WAP_ANALYSIS_JSON = property(WAP_NS, "analysisJson");

    // external properties this layer writes
    public static final Property DCTERMS_TITLE = property(DCTERMS_NS, "title");
    public static final Property DCTERMS_CREATED = property(DCTERMS_NS, "created");
    public static final Property RDFS_LABEL = property(RDFS_NS, "label");

    private Vocab() {
    }

    /** The {@code wap:} concept for a value type, e.g. {@code capitalizedName = "Money"} -> {@code wap:Money}. */
    public static Resource valueTypeConcept(String capitalizedName) {
        return resource(WAP_NS, capitalizedName);
    }

    private static Resource resource(String namespace, String localName) {
        return ResourceFactory.createResource(namespace + localName);
    }

    private static Property property(String namespace, String localName) {
        return ResourceFactory.createProperty(namespace + localName);
    }
}
