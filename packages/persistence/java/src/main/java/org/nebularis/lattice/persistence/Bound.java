// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.persistence;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Deque;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * What a payload may name as a subject (ADR-A132 decision 2, ADR-A123 decision 6 and its addendum on the subjects of an event append).
 * The walk follows the owned edges of the family's boundary shape from the root, over the payload alone, so it needs no engine.
 */
public final class Bound {
    private Bound() {}

    static final String OWNED = "Owned";

    /** A node of the walk and the shape it was reached in, null for a member that owns nothing further. */
    public record State(String node, String shape) {}

    /** The IRI of a typed {@link Iri} or of a plain string, without angle brackets. */
    public static String plain(Object term) {
        if (term instanceof Iri i) return i.value();
        String text = String.valueOf(term);
        return text.startsWith("<") && text.endsWith(">") && text.length() >= 2 ? text.substring(1, text.length() - 1) : text;
    }

    /** The states the walk from {@code root} reaches in {@code payload}, following only owned edges. */
    public static Set<State> reach(PayloadContract contract, Object root, Payload payload) {
        return reach(contract, root, payload, true);
    }

    /** As {@link #reach(PayloadContract, Object, Payload)}, and with {@code ownedOnly} false every edge is followed. */
    public static Set<State> reach(PayloadContract contract, Object root, Payload payload, boolean ownedOnly) {
        Map<List<String>, List<String>> forward = new HashMap<>(), backward = new HashMap<>();
        for (Triple t : payload.triples()) {
            if (t.object() instanceof Iri o) {
                forward.computeIfAbsent(List.of(t.subject().value(), t.predicate().value()), k -> new ArrayList<>()).add(o.value());
                backward.computeIfAbsent(List.of(o.value(), t.predicate().value()), k -> new ArrayList<>()).add(t.subject().value());
            }
        }
        Map<String, List<EdgeContract>> bySource = new HashMap<>();
        for (EdgeContract e : contract.edges()) {
            if (!ownedOnly || OWNED.equals(e.ownership())) bySource.computeIfAbsent(e.sourceShape(), k -> new ArrayList<>()).add(e);
        }
        State start = new State(plain(root), contract.shape());
        Set<State> seen = new HashSet<>(Set.of(start));
        Deque<State> stack = new ArrayDeque<>(List.of(start));
        while (!stack.isEmpty()) {
            State s = stack.pop();
            for (EdgeContract e : bySource.getOrDefault(s.shape(), List.of())) {
                for (String target : (e.inverse() ? backward : forward).getOrDefault(List.of(s.node(), e.predicate()), List.of())) {
                    State next = new State(target, e.targetShape());
                    if (seen.add(next)) stack.push(next);
                }
            }
        }
        return seen;
    }

    /**
     * The subjects of {@code payload} that are neither {@code root} nor reached from it by the owned edges, sorted. A contract with no
     * boundary shape bounds nothing and returns none.
     */
    public static List<Iri> outsideBound(PayloadContract contract, Object root, Payload payload) {
        if (contract.shape() == null) return List.of();
        Set<String> inside = new HashSet<>();
        for (State s : reach(contract, root, payload)) inside.add(s.node());
        return payload.subjects().stream().filter(s -> !inside.contains(s.value())).sorted().toList();
    }

    /** The subjects of an append's event triples that are neither an event of the batch nor a node minted under one, {@code {event}/part/...}. */
    public static List<Iri> outsideEvents(Collection<?> events, Payload payload) {
        List<String> names = events.stream().map(Bound::plain).toList();
        return payload.subjects().stream()
            .filter(s -> names.stream().noneMatch(n -> s.value().equals(n) || s.value().startsWith(n + "/part/")))
            .sorted().toList();
    }
}
