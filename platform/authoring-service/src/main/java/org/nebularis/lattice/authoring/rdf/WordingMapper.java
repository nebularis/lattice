// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.rdf;

import org.apache.jena.datatypes.xsd.XSDDatatype;
import org.apache.jena.rdf.model.Literal;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.ModelFactory;
import org.apache.jena.rdf.model.Resource;
import org.apache.jena.vocabulary.RDF;
import java.util.List;
import org.nebularis.lattice.authoring.model.DocumentSnapshot;
import org.nebularis.lattice.authoring.model.Element;
import org.nebularis.lattice.authoring.model.ElementKind;
import org.nebularis.lattice.authoring.model.LiteralPart;
import org.nebularis.lattice.authoring.model.Part;
import org.nebularis.lattice.authoring.model.ReferencePart;
import org.nebularis.lattice.authoring.model.Section;
import org.nebularis.lattice.authoring.model.VariableDeclaration;
import org.nebularis.lattice.authoring.model.VariablePart;

/** Maps a {@link DocumentSnapshot} to the Wording-layer graph (plan \u00a72.3's "Mapping rules" table). */
public final class WordingMapper {
    private final IriMinter minter;

    public WordingMapper(String base) {
        this.minter = new IriMinter(base);
    }

    public Model map(DocumentSnapshot snapshot, int revision) {
        Model model = ModelFactory.createDefaultModel();
        String documentId = snapshot.documentId();

        Resource wording = model.createResource(minter.wording(documentId));
        wording.addProperty(RDF.type, Vocab.WRD_WORDING);
        wording.addProperty(Vocab.DCTERMS_TITLE, snapshot.title());
        wording.addProperty(Vocab.WAP_DOCUMENT_ID, documentId);
        wording.addProperty(Vocab.WAP_TEMPLATE_ID, snapshot.templateId());
        wording.addProperty(Vocab.WAP_REVISION_NUMBER, integerLiteral(model, revision));

        List<Section> sections = snapshot.sections();
        for (int s = 0; s < sections.size(); s++) {
            Resource sectionResource = mapSection(model, documentId, sections.get(s), s);
            wording.addProperty(Vocab.WRD_DIRECTLY_COMPRISES, sectionResource);
        }

        List<VariableDeclaration> variables = snapshot.variables();
        for (int v = 0; v < variables.size(); v++) {
            Resource variableResource = mapVariable(model, documentId, variables.get(v), v);
            wording.addProperty(Vocab.WRD_DIRECTLY_COMPRISES, variableResource);
        }

        return model;
    }

    private Resource mapSection(Model model, String documentId, Section section, int s) {
        Resource resource = model.createResource(minter.section(documentId, section.sectionKey()));
        resource.addProperty(RDF.type, Vocab.WRD_ELEMENT);
        resource.addProperty(Vocab.WRD_ELEMENT_TYPE, Vocab.WAP_SECTION);
        resource.addProperty(Vocab.WAP_SECTION_KEY, section.sectionKey());
        resource.addProperty(Vocab.WRD_RANK_KEY, rankKey("s", s));
        resource.addProperty(Vocab.WRD_OBJECT_ID, String.valueOf(s + 1));

        List<Element> elements = section.elements();
        for (int e = 0; e < elements.size(); e++) {
            Resource elementResource = mapElement(model, documentId, elements.get(e), s, e);
            resource.addProperty(Vocab.WRD_DIRECTLY_COMPRISES, elementResource);
        }
        return resource;
    }

    private Resource mapElement(Model model, String documentId, Element element, int s, int e) {
        Resource resource = model.createResource(minter.element(documentId, element.elementId()));
        resource.addProperty(RDF.type, Vocab.WRD_TEXT);
        boolean isDefinition = element.kind() == ElementKind.DEFINITION;
        if (isDefinition) {
            resource.addProperty(RDF.type, Vocab.WAP_DEFINITION_TEXT);
        }
        resource.addProperty(Vocab.WRD_ELEMENT_TYPE, isDefinition ? Vocab.WAP_DEFINITION : Vocab.WAP_CLAUSE);
        resource.addProperty(Vocab.WAP_ELEMENT_ID, element.elementId());
        resource.addProperty(Vocab.WRD_RANK_KEY, rankKey("e", e));
        resource.addProperty(Vocab.WRD_OBJECT_ID, (s + 1) + "." + (e + 1));
        resource.addProperty(Vocab.WAP_PLAIN_TEXT, element.text());
        if (isDefinition) {
            resource.addProperty(Vocab.WAP_DEFINED_TERM, element.definedTerm());
        }

        List<Part> parts = element.parts();
        for (int i = 0; i < parts.size(); i++) {
            Resource partResource = mapPart(model, documentId, element.elementId(), parts.get(i), i);
            resource.addProperty(Vocab.WAP_HAS_PART, partResource);
        }
        return resource;
    }

    private Resource mapPart(Model model, String documentId, String elementId, Part part, int index) {
        Resource resource = model.createResource(minter.textPart(documentId, elementId, index));
        resource.addProperty(RDF.type, Vocab.WRD_TEXT_PART);
        resource.addProperty(Vocab.WRD_PART_INDEX, integerLiteral(model, index));
        switch (part) {
            case LiteralPart literal -> resource.addProperty(Vocab.WRD_PART_TEXT, literal.text());
            case VariablePart variable -> {
                Resource variableResource = model.createResource(minter.variable(documentId, variable.variableKey()));
                resource.addProperty(Vocab.WRD_REFERS_TO_VARIABLE, variableResource);
                resource.addProperty(Vocab.WAP_DISPLAY_TEXT, variable.text());
            }
            case ReferencePart reference -> {
                Resource targetResource = model.createResource(minter.element(documentId, reference.targetElementId()));
                resource.addProperty(Vocab.WRD_REFERS_TO_OBJECT, targetResource);
                resource.addProperty(Vocab.WAP_DISPLAY_TEXT, reference.text());
            }
        }
        return resource;
    }

    private Resource mapVariable(Model model, String documentId, VariableDeclaration variable, int v) {
        Resource resource = model.createResource(minter.variable(documentId, variable.variableKey()));
        resource.addProperty(RDF.type, Vocab.WRD_EMBEDDED_VARIABLE);
        resource.addProperty(Vocab.WRD_VARIABLE_KEY, variable.variableKey());
        resource.addProperty(Vocab.RDFS_LABEL, variable.label());
        resource.addProperty(Vocab.WAP_VALUE_TYPE, Vocab.valueTypeConcept(variable.valueType().capitalizedName()));
        resource.addProperty(Vocab.WRD_RANK_KEY, rankKey("v", v));
        return resource;
    }

    private static Literal integerLiteral(Model model, int value) {
        return model.createTypedLiteral(Integer.toString(value), XSDDatatype.XSDinteger);
    }

    private static String rankKey(String prefix, int index) {
        return String.format("%s%04d", prefix, index);
    }
}
