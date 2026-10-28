// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.authoring;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Collectors;

/**
 * Finds the constructs an author has not yet marked, in literal parts only: placeholders, amounts, percentages, dates,
 * durations, uses of a defined term and references to a clause by number. Where two matches overlap the longer wins,
 * then the earlier kind in {@link #RULES} order, then the earlier start. Offsets are UTF-16 code units into the
 * element's text, the end exclusive, as the add-in counts them. Carried over from the Word add-in's first service.
 */
final class Detector {
    static final String DEFINED_TERM = "defined-term";
    static final String CROSS_REFERENCE = "cross-reference";
    static final String MARK_VARIABLE = "mark-variable";
    static final String MARK_REFERENCE = "mark-reference";
    static final String NONE = "none";

    /** One construct found. {@code valueType}, {@code key} and {@code target} are null where the action does not use them. */
    record Detection(String elementId, int partIndex, int start, int end, String text, String kind, String action,
                     String valueType, String key, String target) {
    }

    private record Rule(String kind, Pattern pattern, String valueType) {
    }

    private static final List<Rule> RULES = List.of(
        new Rule("placeholder", Pattern.compile(
            "\\[[^\\[\\]\\n]{1,60}\\]|\\{[^{}\\n]{1,60}\\}|«[^«»\\n]{1,60}»|_{3,}"), "text"),
        new Rule("money", Pattern.compile(
            "(?:GBP|USD|EUR|£|\\$|€)\\s?\\d{1,3}(?:,\\d{3})*(?:\\.\\d{1,2})?(?:\\s?(?:million|bn|m)\\b)?"), "money"),
        new Rule("percentage", Pattern.compile(
            "\\d+(?:\\.\\d+)?\\s?(?:%|per cent\\b|percent\\b)", Pattern.CASE_INSENSITIVE), "percentage"),
        new Rule("date", Pattern.compile(
            "\\b\\d{1,2}(?:st|nd|rd|th)?\\s(?:January|February|March|April|May|June|July|August|September"
                + "|October|November|December)\\s\\d{4}\\b|\\b\\d{4}-\\d{2}-\\d{2}\\b"), "date"),
        new Rule("duration", Pattern.compile(
            "\\b(?:\\d{1,4}|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|fourteen|fifteen"
                + "|twenty|thirty|sixty|ninety)(?:\\s\\(\\d{1,4}\\))?\\s(?:business\\s|calendar\\s|banking\\s)?"
                + "(?:days?|weeks?|months?|years?)\\b", Pattern.CASE_INSENSITIVE), "duration"));

    private static final Pattern CROSS_REFERENCE_PATTERN = Pattern.compile(
        "\\b(?:clause|section|schedule|paragraph|article)\\s\\d+(?:\\.\\d+)*(?:\\([a-z0-9]+\\))?", Pattern.CASE_INSENSITIVE);

    private record Candidate(int order, Detection detection) {
        int length() {
            return detection.end() - detection.start();
        }
    }

    private Detector() {
    }

    static List<Detection> detect(Markup markup) {
        Map<String, String> definitions = new LinkedHashMap<>();
        markup.sections().forEach(s -> s.items().forEach(i -> {
            if (i.definition()) {
                definitions.putIfAbsent(i.term(), i.id());
            }
        }));
        Pattern terms = termPattern(definitions.keySet());
        List<Detection> out = new ArrayList<>();
        markup.sections().forEach(s -> s.items().forEach(i -> out.addAll(detectIn(i, terms, definitions))));
        return out;
    }

    /** Longest term first, so a term wins over another that is a prefix of it. */
    private static Pattern termPattern(Set<String> terms) {
        if (terms.isEmpty()) {
            return null;
        }
        String alternation = terms.stream()
            .sorted(Comparator.comparingInt(String::length).reversed().thenComparing(Comparator.naturalOrder()))
            .map(Pattern::quote).collect(Collectors.joining("|"));
        return Pattern.compile("(?<![\\p{L}\\p{N}])(" + alternation + ")(?:s|'s|’s)?(?![\\p{L}\\p{N}])");
    }

    private static List<Detection> detectIn(Markup.Item item, Pattern terms, Map<String, String> definitions) {
        List<Candidate> candidates = new ArrayList<>();
        int base = 0;
        for (int p = 0; p < item.parts().size(); p++) {
            Markup.Part part = item.parts().get(p);
            if (part.kind() == Markup.Kind.LITERAL) {
                collect(candidates, item, part.text(), base, p, terms, definitions);
            }
            base += part.text().length();
        }
        candidates.sort(Comparator.comparingInt(Candidate::length).reversed().thenComparingInt(Candidate::order)
            .thenComparingInt(c -> c.detection().start()));
        List<Detection> accepted = new ArrayList<>();
        for (Candidate c : candidates) {
            Detection d = c.detection();
            if (accepted.stream().noneMatch(o -> d.start() < o.end() && o.start() < d.end())) {
                accepted.add(d);
            }
        }
        accepted.sort(Comparator.comparingInt(Detection::start));
        return accepted;
    }

    private static void collect(List<Candidate> out, Markup.Item item, String text, int base, int part, Pattern terms,
                                Map<String, String> definitions) {
        for (int order = 0; order < RULES.size(); order++) {
            Rule rule = RULES.get(order);
            Matcher m = rule.pattern().matcher(text);
            while (m.find()) {
                out.add(new Candidate(order, new Detection(item.id(), part, base + m.start(), base + m.end(), m.group(), rule.kind(),
                    MARK_VARIABLE, rule.valueType(), suggestedKey(m.group(), rule.valueType()), null)));
            }
        }
        if (terms != null) {
            Matcher m = terms.matcher(text);
            while (m.find()) {
                String term = m.group(1);
                if (item.definition() && term.equals(item.term())) {
                    continue;
                }
                out.add(new Candidate(RULES.size(), new Detection(item.id(), part, base + m.start(), base + m.end(), m.group(),
                    DEFINED_TERM, MARK_REFERENCE, null, null, definitions.get(term))));
            }
        }
        Matcher m = CROSS_REFERENCE_PATTERN.matcher(text);
        while (m.find()) {
            out.add(new Candidate(RULES.size() + 1, new Detection(item.id(), part, base + m.start(), base + m.end(), m.group(),
                CROSS_REFERENCE, NONE, null, null, null)));
        }
    }

    /** {@code [Agent]} gives {@code agent}, {@code GBP 250} {@code gbp-250}, and {@code 120 days} {@code duration-120-days}. */
    static String suggestedKey(String text, String valueType) {
        String key = toKey(text.toLowerCase(Locale.ROOT).replaceAll("[^a-z0-9]+", "-"));
        if (key.isEmpty() || Character.isDigit(key.charAt(0))) {
            key = toKey(valueType + "-" + key);
        }
        return key;
    }

    private static String toKey(String value) {
        String trimmed = strip(value);
        return strip(trimmed.length() > 40 ? trimmed.substring(0, 40) : trimmed);
    }

    private static String strip(String value) {
        return value.replaceAll("^-+|-+$", "");
    }
}
