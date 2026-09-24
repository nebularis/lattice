// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.minting;

import java.math.BigInteger;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

/**
 * The JSON this library needs, since the JDK has none: a reader for recipes,
 * vectors and anchors, and the canonical writer for recipe digests
 * (identity-minting-specification.md §2.1).
 *
 * <p>The reader accepts RFC 8259 JSON restricted as recipes and vectors are:
 * numbers must be integers, member names must be unique, and strings must be
 * well-formed Unicode (no unpaired surrogates). Objects become
 * {@link LinkedHashMap}, arrays {@link ArrayList}, integers {@link Long}, or
 * {@link BigInteger} beyond the range of a long.
 */
public final class Json {

    /** Input outside the restricted JSON above. */
    public static final class SyntaxException extends IllegalArgumentException {
        private static final long serialVersionUID = 1L;

        SyntaxException(String message) {
            super(message);
        }
    }

    private Json() {
    }

    public static Object parse(String text) {
        return new Parser(text).document();
    }

    /**
     * RFC 8785 for values of the recipe format: members sorted by UTF-16 code
     * units, no insignificant whitespace, integers only, and only the
     * required string escapes. Returns UTF-8 bytes.
     */
    public static byte[] canonical(Object value) {
        StringBuilder sb = new StringBuilder();
        write(sb, value);
        return sb.toString().getBytes(StandardCharsets.UTF_8);
    }

    private static void write(StringBuilder sb, Object value) {
        switch (value) {
            case null -> sb.append("null");
            case Boolean b -> sb.append(b);
            case Long n -> sb.append(n);
            case Integer n -> sb.append(n);
            case BigInteger n -> sb.append(n);
            case String s -> string(sb, s);
            case Map<?, ?> m -> {
                TreeMap<String, Object> sorted = new TreeMap<>();
                for (Map.Entry<?, ?> e : m.entrySet()) {
                    if (!(e.getKey() instanceof String k)) {
                        throw new IllegalArgumentException("member names must be strings");
                    }
                    sorted.put(k, e.getValue());
                }
                sb.append('{');
                boolean first = true;
                for (Map.Entry<String, Object> e : sorted.entrySet()) {
                    if (!first) {
                        sb.append(',');
                    }
                    first = false;
                    string(sb, e.getKey());
                    sb.append(':');
                    write(sb, e.getValue());
                }
                sb.append('}');
            }
            case List<?> l -> {
                sb.append('[');
                for (int i = 0; i < l.size(); i++) {
                    if (i > 0) {
                        sb.append(',');
                    }
                    write(sb, l.get(i));
                }
                sb.append(']');
            }
            default -> throw new IllegalArgumentException("not a value of the recipe format: " + value.getClass().getName());
        }
    }

    private static void string(StringBuilder sb, String s) {
        sb.append('"');
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            switch (c) {
                case '"' -> sb.append("\\\"");
                case '\\' -> sb.append("\\\\");
                case '\b' -> sb.append("\\b");
                case '\t' -> sb.append("\\t");
                case '\n' -> sb.append("\\n");
                case '\f' -> sb.append("\\f");
                case '\r' -> sb.append("\\r");
                default -> {
                    if (c < 0x20) {
                        sb.append(String.format("\\u%04x", (int) c));
                    } else {
                        sb.append(c);
                    }
                }
            }
        }
        sb.append('"');
    }

    private static final class Parser {
        private final String s;
        private int i;

        Parser(String s) {
            this.s = s;
        }

        Object document() {
            ws();
            Object v = value();
            ws();
            if (i != s.length()) {
                throw error("unexpected content after the value");
            }
            return v;
        }

        private SyntaxException error(String message) {
            return new SyntaxException(message + " at offset " + i);
        }

        private boolean peek(char c) {
            return i < s.length() && s.charAt(i) == c;
        }

        private void expect(char c) {
            if (!peek(c)) {
                throw error("expected '" + c + "'");
            }
            i++;
        }

        private boolean digit() {
            return i < s.length() && s.charAt(i) >= '0' && s.charAt(i) <= '9';
        }

        private void ws() {
            while (i < s.length()) {
                char c = s.charAt(i);
                if (c != ' ' && c != '\t' && c != '\n' && c != '\r') {
                    return;
                }
                i++;
            }
        }

        private Object value() {
            if (i >= s.length()) {
                throw error("unexpected end of input");
            }
            char c = s.charAt(i);
            return switch (c) {
                case '{' -> object();
                case '[' -> array();
                case '"' -> string();
                case 't' -> literal("true", Boolean.TRUE);
                case 'f' -> literal("false", Boolean.FALSE);
                case 'n' -> literal("null", null);
                default -> {
                    if (c == '-' || (c >= '0' && c <= '9')) {
                        yield number();
                    }
                    throw error("unexpected character");
                }
            };
        }

        private Object literal(String word, Object v) {
            if (!s.startsWith(word, i)) {
                throw error("unexpected character");
            }
            i += word.length();
            return v;
        }

        private Map<String, Object> object() {
            i++;
            Map<String, Object> m = new LinkedHashMap<>();
            ws();
            if (peek('}')) {
                i++;
                return m;
            }
            while (true) {
                ws();
                if (!peek('"')) {
                    throw error("expected a member name");
                }
                String key = string();
                ws();
                expect(':');
                ws();
                Object v = value();
                if (m.containsKey(key)) {
                    throw error("duplicate member \"" + key + "\"");
                }
                m.put(key, v);
                ws();
                if (peek(',')) {
                    i++;
                    continue;
                }
                expect('}');
                return m;
            }
        }

        private List<Object> array() {
            i++;
            List<Object> l = new ArrayList<>();
            ws();
            if (peek(']')) {
                i++;
                return l;
            }
            while (true) {
                ws();
                l.add(value());
                ws();
                if (peek(',')) {
                    i++;
                    continue;
                }
                expect(']');
                return l;
            }
        }

        private Object number() {
            int start = i;
            if (peek('-')) {
                i++;
            }
            if (peek('0')) {
                i++;
            } else {
                if (!digit()) {
                    throw error("expected a digit");
                }
                while (digit()) {
                    i++;
                }
            }
            if (peek('.') || peek('e') || peek('E')) {
                throw error("only integers are allowed");
            }
            BigInteger n = new BigInteger(s.substring(start, i));
            return n.bitLength() < 64 ? (Object) n.longValue() : n;
        }

        private String string() {
            i++;
            StringBuilder sb = new StringBuilder();
            while (true) {
                if (i >= s.length()) {
                    throw error("unterminated string");
                }
                char c = s.charAt(i++);
                if (c == '"') {
                    break;
                }
                if (c < 0x20) {
                    throw error("unescaped control character in a string");
                }
                if (c != '\\') {
                    sb.append(c);
                    continue;
                }
                if (i >= s.length()) {
                    throw error("unterminated escape");
                }
                char e = s.charAt(i++);
                switch (e) {
                    case '"' -> sb.append('"');
                    case '\\' -> sb.append('\\');
                    case '/' -> sb.append('/');
                    case 'b' -> sb.append('\b');
                    case 'f' -> sb.append('\f');
                    case 'n' -> sb.append('\n');
                    case 'r' -> sb.append('\r');
                    case 't' -> sb.append('\t');
                    case 'u' -> sb.append(hex4());
                    default -> throw error("unknown escape");
                }
            }
            String out = sb.toString();
            for (int k = 0; k < out.length(); k++) {
                char c = out.charAt(k);
                if (Character.isHighSurrogate(c) && k + 1 < out.length() && Character.isLowSurrogate(out.charAt(k + 1))) {
                    k++;
                } else if (Character.isSurrogate(c)) {
                    throw error("unpaired surrogate in a string");
                }
            }
            return out;
        }

        private char hex4() {
            if (i + 4 > s.length()) {
                throw error("short escape");
            }
            int v = 0;
            for (int k = 0; k < 4; k++) {
                int d = Character.digit(s.charAt(i++), 16);
                if (d < 0) {
                    throw error("bad hex digit in escape");
                }
                v = v * 16 + d;
            }
            return (char) v;
        }
    }
}
