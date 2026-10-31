// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.persistence;

import java.util.Locale;
import java.util.regex.Pattern;

/**
 * A ground literal (ADR-A132 decision 2). {@code datatype} and {@code lang} are mutually exclusive, xsd:string is the same as no
 * datatype, and a language tag is lower case. The canonical form escapes only backslash, quote, line feed and carriage return.
 */
public record Lit(String value, String datatype, String lang) implements Term {
    private static final Pattern LANG = Pattern.compile("[A-Za-z]{1,8}(-[A-Za-z0-9]{1,8})*");
    private static final String HEX = "0123456789abcdefABCDEF";

    public Lit {
        if (value == null) throw new PayloadException("not a literal: the value is null");
        if (Namespaces.XSD_STRING.equals(datatype) || "".equals(datatype)) datatype = null;
        lang = lang == null || lang.isEmpty() ? null : lang.toLowerCase(Locale.ROOT);
        for (int i = 0; i < value.length(); i++) {
            char c = value.charAt(i);
            if (Character.isHighSurrogate(c) && i + 1 < value.length() && Character.isLowSurrogate(value.charAt(i + 1))) {
                i++;
            } else if (Character.isSurrogate(c)) {
                throw new PayloadException("not a literal: the value cannot be encoded as UTF-8");
            }
        }
        try {
            encode(value, datatype, lang);
        } catch (SparqlTermException e) {
            throw new PayloadException("not a literal: " + e.getMessage(), e);
        }
    }

    /** A plain string literal. */
    public Lit(String value) {
        this(value, null, null);
    }

    @Override public String nt() {
        String text = "\"" + value.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n").replace("\r", "\\r") + "\"";
        if (datatype != null) return text + "^^<" + datatype + ">";
        return lang != null ? text + "@" + lang : text;
    }

    @Override public String sparql() {
        return encode(value, datatype, lang);
    }

    /**
     * The quoted and escaped SPARQL literal. SPARQL reads unicode escapes over the whole text before parsing, so a backslash before
     * a {@code u} or a {@code U} is followed by an escape of that letter, and hex digits after it are written as escapes too. Every engine then
     * decodes the same value.
     */
    public static String encode(String value, String datatype, String lang) {
        StringBuilder out = new StringBuilder("\"");
        char previous = 0;
        boolean afterEscape = false;
        for (int i = 0; i < value.length(); i++) {
            char ch = value.charAt(i);
            if ((ch == 'u' || ch == 'U') && previous == '\\') {
                out.append(ch == 'u' ? "\\u0075" : "\\u0055");
                afterEscape = true;
            } else if (afterEscape && HEX.indexOf(ch) >= 0) {
                out.append(String.format("\\u%04X", (int) ch));
            } else {
                switch (ch) {
                    case '\\' -> out.append("\\\\");
                    case '"' -> out.append("\\\"");
                    case '\n' -> out.append("\\n");
                    case '\r' -> out.append("\\r");
                    case '\t' -> out.append("\\t");
                    default -> out.append(ch);
                }
                afterEscape = false;
            }
            previous = ch;
        }
        out.append('"');
        if (datatype != null && !datatype.isEmpty() && lang != null && !lang.isEmpty()) {
            throw new SparqlTermException("a literal cannot carry both a datatype and a language tag");
        }
        if (datatype != null && !datatype.isEmpty()) {
            out.append("^^").append(Iri.of(datatype));
        } else if (lang != null && !lang.isEmpty()) {
            if (!LANG.matcher(lang).matches()) throw new SparqlTermException("invalid language tag '" + lang + "'");
            out.append('@').append(lang);
        }
        return out.toString();
    }
}
