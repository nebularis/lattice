// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.store;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.HexFormat;
import java.util.List;
import java.util.Map;
import java.util.Set;
import org.apache.jena.graph.Node;
import org.apache.jena.graph.NodeFactory;
import org.apache.jena.graph.Triple;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.ModelFactory;
import org.apache.jena.sparql.util.FmtUtils;

/**
 * A payload holds no blank node (ADR-A132), so the writer names each one with a skolem IRI before it writes, and the store
 * reads one back as a blank node (ADR-A149 decision 13). A blank node's name is the digest of what it says and of where it
 * sits, so a save that leaves a node and its ancestors unchanged gives it the name it had, and the patch log's delta holds
 * only what changed. Nodes that say the same thing in the same place are indistinguishable, and are told apart by a count.
 */
public final class Skolem {
    public static final String PREFIX = "urn:lattice:studio:genid:";

    private Skolem() {
    }

    public static boolean isSkolem(Node n) {
        return n.isURI() && n.getURI().startsWith(PREFIX);
    }

    /** {@code model} with every blank node replaced by its skolem IRI. */
    public static Model skolemise(Model model) {
        List<Triple> triples = model.getGraph().find().toList();
        Map<Node, List<Triple>> out = new HashMap<>();
        Map<Node, List<Triple>> in = new HashMap<>();
        for (Triple t : triples) {
            if (t.getSubject().isBlank()) {
                out.computeIfAbsent(t.getSubject(), k -> new ArrayList<>()).add(t);
            }
            if (t.getObject().isBlank()) {
                in.computeIfAbsent(t.getObject(), k -> new ArrayList<>()).add(t);
            }
        }
        Map<Node, String> content = new HashMap<>();
        Map<Node, String> names = new HashMap<>();
        Set<Node> blanks = new HashSet<>(out.keySet());
        blanks.addAll(in.keySet());
        Map<String, Integer> seen = new HashMap<>();
        // Sorted by the base name, so the count that tells identical nodes apart is assigned in one order.
        List<Map.Entry<String, Node>> bases = new ArrayList<>();
        for (Node b : blanks) {
            bases.add(Map.entry(name(b, out, in, content, names, new HashSet<>()), b));
        }
        bases.sort(Map.Entry.comparingByKey());
        Map<Node, Node> iri = new HashMap<>();
        for (Map.Entry<String, Node> e : bases) {
            int n = seen.merge(e.getKey(), 1, Integer::sum) - 1;
            iri.put(e.getValue(), NodeFactory.createURI(PREFIX + e.getKey() + (n == 0 ? "" : "-" + n)));
        }
        Model result = ModelFactory.createDefaultModel();
        result.setNsPrefixes(model.getNsPrefixMap());
        for (Triple t : triples) {
            result.getGraph().add(Triple.create(iri.getOrDefault(t.getSubject(), t.getSubject()), t.getPredicate(),
                iri.getOrDefault(t.getObject(), t.getObject())));
        }
        return result;
    }

    /** {@code model} with every skolem IRI read back as a blank node, the same IRI as the same node. */
    public static Model unskolemise(Model model) {
        if (!model.getGraph().find().filterKeep(t -> isSkolem(t.getSubject()) || isSkolem(t.getObject())).hasNext()) {
            return model;
        }
        Map<Node, Node> blank = new HashMap<>();
        Model result = ModelFactory.createDefaultModel();
        result.setNsPrefixes(model.getNsPrefixMap());
        model.getGraph().find().forEachRemaining(t -> result.getGraph().add(Triple.create(
            isSkolem(t.getSubject()) ? blank.computeIfAbsent(t.getSubject(), k -> NodeFactory.createBlankNode()) : t.getSubject(),
            t.getPredicate(),
            isSkolem(t.getObject()) ? blank.computeIfAbsent(t.getObject(), k -> NodeFactory.createBlankNode()) : t.getObject())));
        return result;
    }

    /** The digest of what {@code b} says, its own triples with each blank object by what it says, in turn. */
    private static String content(Node b, Map<Node, List<Triple>> out, Map<Node, String> memo, Set<Node> path) {
        String known = memo.get(b);
        if (known != null) {
            return known;
        }
        if (!path.add(b)) {
            return "cycle"; // ponytail: a cycle of blank nodes is named by its shape only, and told apart by the count
        }
        List<String> lines = new ArrayList<>();
        for (Triple t : out.getOrDefault(b, List.of())) {
            Node o = t.getObject();
            lines.add(FmtUtils.stringForNode(t.getPredicate()) + " " + (o.isBlank() ? "_:" + content(o, out, memo, path) : FmtUtils.stringForNode(o)));
        }
        path.remove(b);
        String digest = sha256(sorted(lines));
        memo.put(b, digest);
        return digest;
    }

    /** The digest of what {@code b} says and of each place it is named from, a named subject by its IRI and a blank one by its name. */
    private static String name(Node b, Map<Node, List<Triple>> out, Map<Node, List<Triple>> in, Map<Node, String> content,
                               Map<Node, String> names, Set<Node> path) {
        String known = names.get(b);
        if (known != null) {
            return known;
        }
        if (!path.add(b)) {
            return "cycle";
        }
        List<String> places = new ArrayList<>();
        for (Triple t : in.getOrDefault(b, List.of())) {
            Node s = t.getSubject();
            places.add((s.isBlank() ? "_:" + name(s, out, in, content, names, path) : FmtUtils.stringForNode(s)) + " " + FmtUtils.stringForNode(t.getPredicate()));
        }
        path.remove(b);
        String name = sha256(content(b, out, content, new HashSet<>()) + "\n" + sorted(places)).substring(0, 32);
        names.put(b, name);
        return name;
    }

    private static String sorted(List<String> lines) {
        lines.sort(null);
        return String.join("\n", lines);
    }

    private static String sha256(String text) {
        try {
            return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(text.getBytes(StandardCharsets.UTF_8)));
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException(e);
        }
    }
}
