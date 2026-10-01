// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.model;

import com.fasterxml.jackson.databind.JsonNode;
import java.util.ArrayList;
import java.util.List;

/** Reads a {@link DocumentSnapshot} from an already schema-validated JSON node, by hand. */
public final class SnapshotReader {
    private SnapshotReader() {
    }

    public static DocumentSnapshot read(JsonNode node) {
        List<Section> sections = new ArrayList<>();
        for (JsonNode sectionNode : node.get("sections")) {
            sections.add(readSection(sectionNode));
        }
        List<VariableDeclaration> variables = new ArrayList<>();
        for (JsonNode variableNode : node.get("variables")) {
            variables.add(new VariableDeclaration(
                variableNode.get("variableKey").asText(),
                variableNode.get("label").asText(),
                ValueType.fromJson(variableNode.get("valueType").asText())
            ));
        }
        List<Unmarked> unmarked = new ArrayList<>();
        for (JsonNode unmarkedNode : node.get("unmarked")) {
            unmarked.add(new Unmarked(textOrNull(unmarkedNode.get("sectionKey")), unmarkedNode.get("text").asText()));
        }
        return new DocumentSnapshot(
            node.get("schemaVersion").asText(),
            node.get("documentId").asText(),
            node.get("templateId").asText(),
            node.get("title").asText(),
            sections,
            variables,
            unmarked
        );
    }

    private static Section readSection(JsonNode node) {
        List<Element> elements = new ArrayList<>();
        for (JsonNode elementNode : node.get("elements")) {
            elements.add(readElement(elementNode));
        }
        return new Section(node.get("sectionKey").asText(), elements);
    }

    private static Element readElement(JsonNode node) {
        ElementKind kind = ElementKind.fromJson(node.get("kind").asText());
        List<Part> parts = new ArrayList<>();
        for (JsonNode partNode : node.get("parts")) {
            parts.add(readPart(partNode));
        }
        return new Element(node.get("elementId").asText(), kind, textOrNull(node.get("definedTerm")), parts);
    }

    private static Part readPart(JsonNode node) {
        String kind = node.get("kind").asText();
        return switch (kind) {
            case "literal" -> new LiteralPart(node.get("text").asText());
            case "variable" -> new VariablePart(node.get("variableKey").asText(), node.get("text").asText());
            case "reference" -> new ReferencePart(node.get("targetElementId").asText(), node.get("text").asText());
            default -> throw new IllegalArgumentException("unknown part kind: " + kind);
        };
    }

    private static String textOrNull(JsonNode node) {
        return (node == null || node.isNull()) ? null : node.asText();
    }
}
