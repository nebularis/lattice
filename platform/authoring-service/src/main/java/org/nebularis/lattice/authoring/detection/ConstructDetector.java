// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.detection;

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
import org.nebularis.lattice.authoring.model.DocumentSnapshot;
import org.nebularis.lattice.authoring.model.Element;
import org.nebularis.lattice.authoring.model.ElementKind;
import org.nebularis.lattice.authoring.model.LiteralPart;
import org.nebularis.lattice.authoring.model.Part;
import org.nebularis.lattice.authoring.model.Section;
import org.nebularis.lattice.authoring.model.ValueType;

/**
 * Finds the constructs an author has not yet marked up, in literal parts only (plan WA3). Where two
 * matches overlap the longer wins, then the earlier kind in {@link #RULES} order, then the earlier
 * start.
 */
public final class ConstructDetector {
    private static final String DEFINED_TERM = "defined-term";
    private static final String CROSS_REFERENCE = "cross-reference";

    /** A kind of construct found by one pattern, with the value type its variable would carry. */
    private record Rule(String kind, Pattern pattern, ValueType valueType) {
    }

    private static final List<Rule> RULES = List.of(
        new Rule("placeholder", Pattern.compile(
            "\\[[^\\[\\]\\n]{1,60}\\]|\\{[^{}\\n]{1,60}\\}|\u00ab[^\u00ab\u00bb\\n]{1,60}\u00bb|_{3,}"),
            ValueType.TEXT),
        new Rule("money", Pattern.compile(
            "(?:GBP|USD|EUR|\u00a3|\\$|\u20ac)\\s?\\d{1,3}(?:,\\d{3})*(?:\\.\\d{1,2})?(?:\\s?(?:million|bn|m)\\b)?"),
            ValueType.MONEY),
        new Rule("percentage", Pattern.compile(
            "\\d+(?:\\.\\d+)?\\s?(?:%|per cent\\b|percent\\b)", Pattern.CASE_INSENSITIVE),
            ValueType.PERCENTAGE),
        new Rule("date", Pattern.compile(
            "\\b\\d{1,2}(?:st|nd|rd|th)?\\s(?:January|February|March|April|May|June|July|August|September"
                + "|October|November|December)\\s\\d{4}\\b|\\b\\d{4}-\\d{2}-\\d{2}\\b"),
            ValueType.DATE),
        new Rule("duration", Pattern.compile(
            "\\b(?:\\d{1,4}|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|fourteen|fifteen"
                + "|twenty|thirty|sixty|ninety)(?:\\s\\(\\d{1,4}\\))?\\s(?:business\\s|calendar\\s|banking\\s)?"
                + "(?:days?|weeks?|months?|years?)\\b", Pattern.CASE_INSENSITIVE),
            ValueType.DURATION)
    );

    private static final Pattern CROSS_REFERENCE_PATTERN = Pattern.compile(
        "\\b(?:clause|section|schedule|paragraph|article)\\s\\d+(?:\\.\\d+)*(?:\\([a-z0-9]+\\))?",
        Pattern.CASE_INSENSITIVE);

    /** A match before overlaps are resolved. {@code order} is the position in the rule table. */
    private record Candidate(int order, int start, int end, String text, String kind, Suggestion suggestion,
                             int partIndex) {
    }

    public List<Detection> detect(DocumentSnapshot snapshot) {
        Map<String, String> definitionIdByTerm = definitionIdByTerm(snapshot);
        Pattern definedTerms = definedTermPattern(definitionIdByTerm.keySet());
        List<Detection> detections = new ArrayList<>();
        for (Section section : snapshot.sections()) {
            for (Element element : section.elements()) {
                detections.addAll(detectIn(element, definedTerms, definitionIdByTerm));
            }
        }
        return detections;
    }

    private static Map<String, String> definitionIdByTerm(DocumentSnapshot snapshot) {
        Map<String, String> byTerm = new LinkedHashMap<>();
        for (Section section : snapshot.sections()) {
            for (Element element : section.elements()) {
                if (element.kind() == ElementKind.DEFINITION && element.definedTerm() != null) {
                    byTerm.putIfAbsent(element.definedTerm(), element.elementId());
                }
            }
        }
        return byTerm;
    }

    /** Longest term first, so {@code Repayment Date} wins over a term that is a prefix of it. */
    private static Pattern definedTermPattern(Set<String> terms) {
        if (terms.isEmpty()) {
            return null;
        }
        String alternation = terms.stream()
            .sorted(Comparator.comparingInt(String::length).reversed().thenComparing(Comparator.naturalOrder()))
            .map(Pattern::quote)
            .collect(Collectors.joining("|"));
        return Pattern.compile("(?<![\\p{L}\\p{N}])(" + alternation + ")(?:s|'s|\u2019s)?(?![\\p{L}\\p{N}])");
    }

    private static List<Detection> detectIn(Element element, Pattern definedTerms,
                                            Map<String, String> definitionIdByTerm) {
        List<Candidate> candidates = new ArrayList<>();
        List<Part> parts = element.parts();
        int base = 0;
        for (int i = 0; i < parts.size(); i++) {
            Part part = parts.get(i);
            if (part instanceof LiteralPart literal) {
                collect(candidates, literal.text(), base, i, element, definedTerms, definitionIdByTerm);
            }
            base += part.displayText().length();
        }

        candidates.sort(Comparator.<Candidate>comparingInt(c -> c.end() - c.start()).reversed()
            .thenComparingInt(Candidate::order)
            .thenComparingInt(Candidate::start));
        List<Candidate> accepted = new ArrayList<>();
        for (Candidate candidate : candidates) {
            if (accepted.stream().noneMatch(other -> candidate.start() < other.end() && other.start() < candidate.end())) {
                accepted.add(candidate);
            }
        }
        accepted.sort(Comparator.comparingInt(Candidate::start));
        return accepted.stream()
            .map(c -> new Detection(element.elementId(), c.partIndex(), c.start(), c.end(), c.text(), c.kind(),
                c.suggestion()))
            .toList();
    }

    private static void collect(List<Candidate> candidates, String text, int base, int partIndex, Element element,
                                Pattern definedTerms, Map<String, String> definitionIdByTerm) {
        for (int order = 0; order < RULES.size(); order++) {
            Rule rule = RULES.get(order);
            Matcher matcher = rule.pattern().matcher(text);
            while (matcher.find()) {
                String found = matcher.group();
                candidates.add(new Candidate(order, base + matcher.start(), base + matcher.end(), found, rule.kind(),
                    new Suggestion(Suggestion.MARK_VARIABLE, rule.valueType(), suggestedKey(found, rule.valueType()),
                        null),
                    partIndex));
            }
        }
        if (definedTerms != null) {
            Matcher matcher = definedTerms.matcher(text);
            while (matcher.find()) {
                String term = matcher.group(1);
                if (element.kind() == ElementKind.DEFINITION && term.equals(element.definedTerm())) {
                    continue;
                }
                candidates.add(new Candidate(RULES.size(), base + matcher.start(), base + matcher.end(),
                    matcher.group(), DEFINED_TERM,
                    new Suggestion(Suggestion.MARK_REFERENCE, null, null, definitionIdByTerm.get(term)),
                    partIndex));
            }
        }
        Matcher matcher = CROSS_REFERENCE_PATTERN.matcher(text);
        while (matcher.find()) {
            candidates.add(new Candidate(RULES.size() + 1, base + matcher.start(), base + matcher.end(),
                matcher.group(), CROSS_REFERENCE, Suggestion.none(), partIndex));
        }
    }

    /** {@code [Agent] -> agent}, {@code GBP 250 -> gbp-250}, {@code 120 days -> duration-120-days}. */
    public static String suggestedKey(String text, ValueType valueType) {
        String key = toKey(text.toLowerCase(Locale.ROOT).replaceAll("[^a-z0-9]+", "-"));
        if (key.isEmpty() || Character.isDigit(key.charAt(0))) {
            key = toKey(valueType.toJson() + "-" + key);
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
