// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.transforms;

import java.io.IOException;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.regex.Pattern;
import org.apache.jena.atlas.json.JSON;
import org.apache.jena.atlas.json.JsonObject;
import org.apache.jena.atlas.json.JsonValue;

/**
 * Checks a JSON value against `contracts/config-studio/run-frame.schema.json`. No JSON Schema library is on this module's test
 * classpath, so this interprets the keywords the schema file uses and no others (type, required, additionalProperties, properties,
 * pattern, minimum, maximum, minLength, maxLength, enum, const, if, then, else, not, anyOf, allOf), reading the schema from the file, and
 * it refuses a keyword it does not know so that a schema change cannot pass unchecked. It adds the one rule a schema cannot state, that
 * the text of a frame is at most 49,152 bytes as UTF-8, and the rules across a run's frames that the contract states.
 */
final class SchemaCheck {
    private static final Path SCHEMA = Path.of("..", "..", "contracts", "config-studio", "run-frame.schema.json");
    private static final List<String> KNOWN = List.of("$schema", "$id", "title", "description", "type", "required", "additionalProperties",
        "properties", "pattern", "minimum", "maximum", "minLength", "maxLength", "enum", "const", "if", "then", "else", "not", "anyOf", "allOf");

    private final JsonObject schema;

    SchemaCheck() throws IOException {
        schema = JSON.parse(Files.readString(SCHEMA)).getAsObject();
    }

    /** The reasons a frame does not hold, none when it does. */
    List<String> problems(String frameJson) {
        List<String> out = new ArrayList<>();
        JsonValue v;
        try {
            v = JSON.parseAny(frameJson);
        } catch (RuntimeException e) {
            return List.of("not JSON");
        }
        check(v, schema, "$", out);
        if (v.isObject() && v.getAsObject().hasKey("text") && v.getAsObject().get("text").isString()
            && v.getAsObject().get("text").getAsString().value().getBytes(StandardCharsets.UTF_8).length > RunFrames.MAX_TEXT_BYTES) {
            out.add("$.text is over 49152 bytes");
        }
        return out;
    }

    /** The reasons the frames of one run do not hold together, none when they do. */
    List<String> problems(List<String> frames) {
        List<String> out = new ArrayList<>();
        if (frames.isEmpty() || frames.size() > RunFrames.MAX_FRAMES) {
            out.add("a run has 1 to 128 frames, not " + frames.size());
        }
        int parts = 0;
        for (int i = 0; i < frames.size(); i++) {
            List<String> own = problems(frames.get(i));
            own.forEach(p -> out.add(p));
            if (!own.isEmpty()) {
                continue;
            }
            JsonObject f = JSON.parse(frames.get(i));
            if (f.get("seq").getAsNumber().value().intValue() != i) {
                out.add("frame " + i + " has seq " + f.get("seq"));
            }
            if (f.get("last").getAsBoolean().value() != (i == frames.size() - 1)) {
                out.add("last is true on frame " + i + " of " + frames.size() + " or not on the final frame");
            }
            if (i == 0 && f.get("last").getAsBoolean().value() == false && !f.hasKey("part")) {
                out.add("the first frame has no part");
            }
            if (f.hasKey("part")) {
                if (f.get("part").getAsObject().get("index").getAsNumber().value().intValue() != parts++) {
                    out.add("part indexes are not contiguous from 0 at frame " + i);
                }
            }
        }
        return out;
    }

    private void check(JsonValue v, JsonObject s, String at, List<String> out) {
        for (String key : s.keys()) {
            if (!KNOWN.contains(key)) {
                out.add("the schema uses a keyword this check does not know: " + key);
            }
        }
        if (s.hasKey("type") && !isType(v, s.get("type").getAsString().value())) {
            out.add(at + " is not a " + s.get("type").getAsString().value());
            return;
        }
        if (s.hasKey("const") && !s.get("const").equals(v)) {
            out.add(at + " is not " + s.get("const"));
        }
        if (s.hasKey("enum") && s.get("enum").getAsArray().stream().noneMatch(e -> e.equals(v))) {
            out.add(at + " is not one of " + s.get("enum"));
        }
        if (v.isString()) {
            String t = v.getAsString().value();
            if (s.hasKey("pattern") && !Pattern.compile(s.get("pattern").getAsString().value()).matcher(t).find()) {
                out.add(at + " does not match its pattern");
            }
            if (s.hasKey("minLength") && t.codePointCount(0, t.length()) < number(s.get("minLength")).intValue()) {
                out.add(at + " is shorter than its minLength");
            }
            if (s.hasKey("maxLength") && t.codePointCount(0, t.length()) > number(s.get("maxLength")).intValue()) {
                out.add(at + " is longer than its maxLength");
            }
        }
        if (v.isNumber()) {
            BigDecimal n = new BigDecimal(v.getAsNumber().value().toString());
            if (s.hasKey("minimum") && n.compareTo(number(s.get("minimum"))) < 0) {
                out.add(at + " is under its minimum");
            }
            if (s.hasKey("maximum") && n.compareTo(number(s.get("maximum"))) > 0) {
                out.add(at + " is over its maximum");
            }
        }
        if (v.isObject()) {
            JsonObject o = v.getAsObject();
            if (s.hasKey("required")) {
                s.get("required").getAsArray().forEach(r -> {
                    if (!o.hasKey(r.getAsString().value())) {
                        out.add(at + " lacks " + r.getAsString().value());
                    }
                });
            }
            JsonObject props = s.hasKey("properties") ? s.get("properties").getAsObject() : new JsonObject();
            for (String key : o.keys()) {
                if (props.hasKey(key)) {
                    check(o.get(key), props.get(key).getAsObject(), at + "." + key, out);
                } else if (s.hasKey("additionalProperties") && s.get("additionalProperties").isBoolean()
                    && !s.get("additionalProperties").getAsBoolean().value()) {
                    out.add(at + "." + key + " is not a property the schema names");
                }
            }
        }
        if (s.hasKey("if")) {
            boolean holds = matches(v, s.get("if").getAsObject(), at);
            if (holds && s.hasKey("then")) {
                check(v, s.get("then").getAsObject(), at, out);
            } else if (!holds && s.hasKey("else")) {
                check(v, s.get("else").getAsObject(), at, out);
            }
        }
        if (s.hasKey("not") && matches(v, s.get("not").getAsObject(), at)) {
            out.add(at + " matches a schema it must not");
        }
        if (s.hasKey("anyOf") && s.get("anyOf").getAsArray().stream().noneMatch(a -> matches(v, a.getAsObject(), at))) {
            out.add(at + " matches none of its anyOf");
        }
        if (s.hasKey("allOf")) {
            s.get("allOf").getAsArray().forEach(a -> check(v, a.getAsObject(), at, out));
        }
    }

    private boolean matches(JsonValue v, JsonObject s, String at) {
        List<String> none = new ArrayList<>();
        check(v, s, at, none);
        return none.isEmpty();
    }

    private static BigDecimal number(JsonValue v) {
        return new BigDecimal(v.getAsNumber().value().toString());
    }

    private static boolean isType(JsonValue v, String type) {
        return switch (type) {
            case "object" -> v.isObject();
            case "string" -> v.isString();
            case "boolean" -> v.isBoolean();
            case "integer" -> v.isNumber() && new BigDecimal(v.getAsNumber().value().toString()).stripTrailingZeros().scale() <= 0;
            default -> throw new IllegalArgumentException("a type this check does not know: " + type);
        };
    }
}
