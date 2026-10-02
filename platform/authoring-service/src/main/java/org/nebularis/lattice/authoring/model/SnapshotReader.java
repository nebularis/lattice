// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.model;

import com.fasterxml.jackson.databind.JsonNode;
import java.util.ArrayList;
import java.util.List;
import java.util.function.Function;

/** Reads a {@link DocumentSnapshot} from an already schema-validated JSON node, by hand. */
public final class SnapshotReader {
    private SnapshotReader() {
    }

    public static DocumentSnapshot read(JsonNode node) {
        return new DocumentSnapshot(
            node.get("schemaVersion").asText(),
            node.get("documentId").asText(),
            node.get("templateId").asText(),
            node.get("title").asText(),
            each(node.get("sections"), SnapshotReader::readSection),
            each(node.get("variables"), v -> new VariableDeclaration(
                v.get("variableKey").asText(),
                v.get("label").asText(),
                ValueType.fromJson(v.get("valueType").asText())
            )),
            each(node.get("unmarked"), u -> new Unmarked(textOrNull(u.get("sectionKey")), u.get("text").asText()))
        );
    }

    private static Section readSection(JsonNode node) {
        return new Section(node.get("sectionKey").asText(), each(node.get("elements"), SnapshotReader::readElement));
    }

    private static Element readElement(JsonNode node) {
        return new Element(
            node.get("elementId").asText(),
            ElementKind.fromJson(node.get("kind").asText()),
            textOrNull(node.get("definedTerm")),
            each(node.get("parts"), SnapshotReader::readPart)
        );
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

    private static <T> List<T> each(JsonNode array, Function<JsonNode, T> read) {
        List<T> values = new ArrayList<>();
        for (JsonNode node : array) {
            values.add(read.apply(node));
        }
        return values;
    }
}
