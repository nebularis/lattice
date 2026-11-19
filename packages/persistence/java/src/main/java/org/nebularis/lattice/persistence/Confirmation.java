// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.persistence;

import static org.nebularis.lattice.persistence.Bound.plain;

import java.util.ArrayList;
import java.util.Collection;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;

/**
 * The confirmation read of a write and how it classifies the write (ADR-A132, STD-312, the confirmation section of
 * {@code contracts/persistence/README.md}). A 204 from the endpoint does not say whether a write's guard matched. After a write the caller
 * reads the transaction claim and the few facts each guard of the operation tests, on the writer, and {@link #classify} turns them into one of
 * three outcomes. The write applied (on this attempt or an earlier one), was refused because its transaction id already claims a different
 * request, or lost a race, and a lost race names the guard that failed, which is its cause.
 *
 * <p>{@link #query} is the read, one SELECT of {@code ?fact} and {@code ?value} built from typed IRIs only, so no value is read as SPARQL
 * (PRI-55). {@link #classify} decides from the rows alone, and {@link #run} runs the one and the other through the adopter's client. The library
 * makes no store call of its own.
 *
 * @param revision the revision the transaction claimed, or null where it claimed none
 * @param reason which guard the classification answers and what the read found, in words
 */
public record Confirmation(Classification classification, String revision, String reason) {
    /** A template id that ends with it guards on the dataset's epoch. Any other write guards on the version row's own epoch. */
    public static final String DATASET_GUARD_SUFFIX = "-dataset-guard";

    private static final Set<OperationKind> CLAIMING = Set.of(
        OperationKind.CREATE, OperationKind.REPLACE, OperationKind.DELTA_REPLACE, OperationKind.TOMBSTONE, OperationKind.APPEND, OperationKind.APPEND_VERSION);
    private static final Set<OperationKind> KEY_CLAIMING = Set.of(OperationKind.KEY_CLAIM_WRITE, OperationKind.KEY_CLAIM_WRITE_DUAL);

    /** The outcome of the classification. */
    public Outcome outcome() { return classification.outcome(); }

    private static boolean rowGuarded(OperationKind kind) { return CLAIMING.contains(kind) && kind != OperationKind.CREATE; }

    /** Whether the confirmation reads this operation. It does for an operation that records a transaction claim, and for a key-claim write. */
    public static boolean confirms(OperationContract operation) {
        return KEY_CLAIMING.contains(operation.kind()) || (CLAIMING.contains(operation.kind()) && operation.parameter("txnId").isPresent());
    }

    private static void require(OperationContract operation) {
        if (!confirms(operation)) {
            throw new ConfirmationException(operation.templateId() + " records no transaction claim and is not a key-claim write, so this read does not confirm it");
        }
    }

    private static Iri graph(OperationContract operation, String name) {
        String text = operation.binding(name).orElse(null);
        if (text == null) return null;
        if (!(text.startsWith("<") && text.endsWith(">"))) throw new ConfirmationException("the binding " + name + " of " + operation.templateId() + " is not an IRI");
        return Iri.of(text.substring(1, text.length() - 1));
    }

    private static Iri needGraph(OperationContract operation, String name) {
        Iri found = graph(operation, name);
        if (found == null) throw new ConfirmationException(operation.templateId() + " has no binding " + name + ", so the write cannot be confirmed");
        return found;
    }

    private static Iri needIri(Map<String, Object> values, String name) {
        Object value = values.get(name);
        if (value == null) throw new ConfirmationException("the request has no " + name + ", which the confirmation reads");
        try {
            return Iri.of(plain(value));
        } catch (SparqlTermException e) {
            throw new ConfirmationException(name + " is not an IRI: " + e.getMessage(), e);
        }
    }

    private static Long longOf(Map<String, Object> values, String name) {
        Object value = values.get(name);
        if (value == null) return null;
        if (value instanceof Boolean) throw new ConfirmationException(name + " is not an xsd:long");
        try {
            return value instanceof Number n ? n.longValue() : Long.parseLong(value instanceof Lit l ? l.value() : String.valueOf(value));
        } catch (NumberFormatException e) {
            throw new ConfirmationException(name + " is not an xsd:long", e);
        }
    }

    private static String branch(Iri graph, Iri subject, String predicate, String fact) {
        return "{ GRAPH " + graph + " { " + subject + " <" + Namespaces.PAT + predicate + "> ?value } BIND(\"" + fact + "\" AS ?fact) }";
    }

    /**
     * The confirmation read of the write {@code operation} took {@code values} for, as one SELECT of {@code ?fact} and {@code ?value}. Run it on
     * the writer. A row is one fact the store holds. The facts the read asks for follow the guards of the operation, and the contract in
     * {@code contracts/persistence/README.md} lists them. Every graph is a binding of the operation and every subject a typed IRI of the request.
     */
    public static String query(OperationContract operation, Map<String, Object> values) {
        require(operation);
        List<String> branches = new ArrayList<>();
        if (KEY_CLAIMING.contains(operation.kind())) {
            Iri keys = needGraph(operation, "keysGraph");
            List<String> names = operation.kind() == OperationKind.KEY_CLAIM_WRITE_DUAL ? List.of("claimCurrent", "claimNext") : List.of("claim");
            List<String> facts = List.of("claimOwner", "claimNextOwner");
            for (int i = 0; i < names.size(); i++) branches.add(branch(keys, needIri(values, names.get(i)), "claimedBy", facts.get(i)));
        } else {
            Iri txnGraph = needGraph(operation, "txnGraph"), txnId = needIri(values, "txnId");
            Iri target = needIri(values, operation.kind() == OperationKind.APPEND ? "stream" : "root"), meta = needGraph(operation, "metaGraphPrefix");
            branches.add(branch(txnGraph, txnId, "rev", "claimRev"));
            branches.add(branch(txnGraph, txnId, "requestDigest", "claimDigest"));
            if (operation.templateId().endsWith(DATASET_GUARD_SUFFIX)) {
                branches.add(branch(needGraph(operation, "datasetGraph"), needGraph(operation, "datasetNode"), "epoch", "datasetEpoch"));
            }
            branches.add(branch(meta, target, "seq", "rowSeq"));
            if (rowGuarded(operation.kind())) {
                branches.add(branch(meta, target, "epoch", "rowEpoch"));
                branches.add(branch(meta, target, "deleted", "rowDeleted"));
            }
            Iri data = graph(operation, "dataGraph");
            if (operation.kind() == OperationKind.CREATE && data != null) {
                branches.add("{ { SELECT ?p WHERE { GRAPH " + data + " { " + target + " ?p ?o } } LIMIT 1 } BIND(STR(?p) AS ?value) BIND(\"dataPresent\" AS ?fact) }");
            }
        }
        return "SELECT ?fact ?value WHERE {\n  " + String.join("\n  UNION ", branches) + "\n}";
    }

    private static Map<String, List<String>> facts(Collection<Map<String, Object>> rows) {
        Map<String, List<String>> out = new HashMap<>();
        for (Map<String, Object> row : rows) out.computeIfAbsent(String.valueOf(row.get("fact")), k -> new ArrayList<>()).add(plain(row.get("value")));
        return out;
    }

    private static Long asLong(String text) {
        try {
            return Long.parseLong(text.startsWith("+") ? text.substring(1) : text);
        } catch (NumberFormatException e) {
            return null;
        }
    }

    private static boolean has(List<String> texts, Long wanted) {
        return texts.stream().anyMatch(t -> wanted.equals(asLong(t)));
    }

    private static List<String> sorted(List<String> texts) {
        return texts.stream().sorted(Text.ORDER).toList();
    }

    private static Confirmation keyClaim(OperationContract operation, Map<String, Object> values, Map<String, List<String>> facts) {
        String owner = needIri(values, "owner").value();
        List<String> names = operation.kind() == OperationKind.KEY_CLAIM_WRITE_DUAL ? List.of("claimCurrent", "claimNext") : List.of("claim");
        List<String> keys = List.of("claimOwner", "claimNextOwner");
        for (int i = 0; i < names.size(); i++) {
            List<String> others = sorted(facts.getOrDefault(keys.get(i), List.of()).stream().filter(o -> !o.equals(owner)).toList());
            if (!others.isEmpty()) {
                return new Confirmation(Classification.KEY_CLAIM_HELD, null, "The key claim <" + needIri(values, names.get(i)).value() + "> is held by <" + others.get(0)
                    + ">, not by <" + owner + ">, so the guard on another owner failed and the write changed nothing.");
            }
        }
        boolean all = java.util.stream.IntStream.range(0, names.size()).allMatch(i -> facts.getOrDefault(keys.get(i), List.of()).contains(owner));
        return all ? new Confirmation(Classification.APPLIED, null, "The key claim is held by <" + owner + ">, so the write applied, on this attempt or an earlier attempt.")
            : new Confirmation(Classification.NOT_APPLIED, null, "The key claim has no owner and no guard of the operation can be read as the one that failed.");
    }

    /** Classify the write from the rows {@link #query} returned. The first rule that holds decides, in the order of the contract. */
    public static Confirmation classify(OperationContract operation, Map<String, Object> values, Collection<Map<String, Object>> rows) {
        require(operation);
        Map<String, List<String>> facts = facts(rows);
        if (KEY_CLAIMING.contains(operation.kind())) return keyClaim(operation, values, facts);

        Object digest = values.get("requestDigest");
        Long epoch = longOf(values, "epoch"), expected = longOf(values, "expectedSeq");
        List<String> revs = sorted(facts.getOrDefault("claimRev", List.of()));
        if (!revs.isEmpty()) {
            boolean same = facts.getOrDefault("claimDigest", List.of()).equals(digest == null ? List.of() : List.of(String.valueOf(digest)));
            return same ? new Confirmation(Classification.APPLIED, revs.get(0),
                "The claim of the transaction is on the transaction graph with this request's digest, so the write applied, on this attempt or an earlier attempt.")
                : new Confirmation(Classification.IDEMPOTENCY_KEY_REUSE, revs.get(0), "The transaction id already claims a revision with the digest of a different request.");
        }

        List<Long> seqs = facts.getOrDefault("rowSeq", List.of()).stream().map(Confirmation::asLong).filter(n -> n != null).sorted().toList();
        boolean rowGuarded = rowGuarded(operation.kind());
        if (operation.templateId().endsWith(DATASET_GUARD_SUFFIX)) {
            List<String> current = sorted(facts.getOrDefault("datasetEpoch", List.of()));
            if (epoch != null && !has(current, epoch)) {
                return new Confirmation(Classification.EPOCH_CHANGED, null,
                    "The dataset's epoch " + (current.isEmpty() ? "is not stated" : "is " + current.get(0)) + ", not " + epoch + ", so the guard on it failed.");
            }
        } else if (rowGuarded && epoch != null && !facts.getOrDefault("rowEpoch", List.of()).isEmpty() && !has(facts.get("rowEpoch"), epoch)) {
            return new Confirmation(Classification.EPOCH_CHANGED, null,
                "The version row's epoch is " + sorted(facts.get("rowEpoch")).get(0) + ", not " + epoch + ", so the guard on it failed.");
        }
        if (rowGuarded && facts.getOrDefault("rowDeleted", List.of()).stream().anyMatch(v -> v.equals("true") || v.equals("1"))) {
            return new Confirmation(Classification.GONE, null, "The aggregate's version row is tombstoned, so the write found nothing to change.");
        }
        if (rowGuarded && (expected != null ? !seqs.contains(expected) : seqs.isEmpty())) {
            String what = seqs.isEmpty()
                ? (expected != null ? "The aggregate has no version row, so the guard on position " + expected + " failed."
                    : "The stream has no version row, so the guard on it failed. Was it bootstrapped?")
                : "The version row is at position " + seqs.get(0) + ", not " + expected + ", so another writer moved it and the guard failed.";
            return new Confirmation(Classification.PRECONDITION_FAILED, null, what);
        }
        if (operation.kind() == OperationKind.CREATE && (!seqs.isEmpty() || !facts.getOrDefault("dataPresent", List.of()).isEmpty())) {
            return new Confirmation(Classification.ALREADY_EXISTS, null, !seqs.isEmpty()
                ? "The aggregate already has a version row at position " + seqs.get(0) + ", so the create wrote nothing."
                : "The root already has triples in the data graph, so the create wrote nothing.");
        }
        return new Confirmation(Classification.NOT_APPLIED, null, "The transaction has no claim and no guard of the operation can be read as the one that failed.");
    }

    /**
     * Read the write's confirmation through {@code client} and classify it. {@code values} are the values the request was built from, including its
     * {@code requestDigest} ({@link RequestDigest}).
     */
    public static Confirmation run(SelectClient client, OperationContract operation, Map<String, Object> values) {
        return classify(operation, values, client.select(query(operation, values)));
    }
}
