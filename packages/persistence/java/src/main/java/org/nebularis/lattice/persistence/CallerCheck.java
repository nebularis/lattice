// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.persistence;

import static org.nebularis.lattice.persistence.Bound.plain;

import java.io.StringReader;
import java.math.BigInteger;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.TreeSet;
import java.util.function.Predicate;
import java.util.regex.Pattern;
import org.apache.jena.graph.Node;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.ModelFactory;
import org.apache.jena.riot.Lang;
import org.apache.jena.riot.RDFParser;

/**
 * The caller check (ADR-A132 decision 2, ADR-A123 decision 5 and its addenda). {@link #refusals} tests a request against the contract of its
 * operation before anything is sent, and says why for each failure, since a guard that fails in the store reads as a lost race.
 * It checks what the store cannot, or can only when the compile left the guards on.
 * <ul>
 * <li>Every required parameter is present, none is unknown, and each is of its kind. A {@code Long} or {@code Position} is an xsd:long exactly,
 * on any store, and a literal is never an IRI.
 * <li>A caller-named graph equals the naming rule of the family.
 * <li>{@code logGraphs} holds IRIs and is not empty, unless the caller allows an audit over no graph.
 * <li>A payload names no subject outside the aggregate, and an append's event triples name none outside its events.
 * <li>Where the caller can say what is a version, an object on a pinned edge is one and an object on an identity edge is not.
 * <li>On a version of a family under delta membership, a checkpoint lists the full set of members.
 * </ul>
 * A value is an {@link Iri}, a {@link Lit}, a {@link Payload}, a {@link Rows}, a {@code String}, an integral number, or for a
 * {@code RegistryList} an {@link Iterable} of {@link Iri} or IRI strings. A Jena literal node is read as a literal.
 */
public final class CallerCheck {
    private CallerCheck() {}

    private static final Pattern LONG_LEXICAL = Pattern.compile("[+-]?[0-9]+");
    private static final Pattern DIGEST = Pattern.compile("[0-9a-f]{64}");
    private static final BigInteger MIN = BigInteger.valueOf(Long.MIN_VALUE), MAX = BigInteger.valueOf(Long.MAX_VALUE);

    /** The options of {@link #refusals}. {@code versionOf} says what is a version, and a null one skips the reference modes. */
    public record Options(boolean allowEmptyLogGraphs, Predicate<Iri> versionOf, Membership membership) {
        /** No option. */
        public static Options none() { return new Options(false, null, null); }

        /** An audit over no graph is then allowed, and reports nothing examined. */
        public Options allowEmptyLogGraphs(boolean allow) { return new Options(allow, versionOf, membership); }

        public Options versionOf(Predicate<Iri> versionOf) { return new Options(allowEmptyLogGraphs, versionOf, membership); }

        public Options membership(Membership membership) { return new Options(allowEmptyLogGraphs, versionOf, membership); }
    }

    private static String iri(Object value) {
        if (value instanceof Iri i) return i.value();
        if (value instanceof String s) {
            try {
                Iri.of(s);
            } catch (SparqlTermException e) {
                return null;
            }
            return s;
        }
        return null;
    }

    private static boolean integral(Object v) {
        return v instanceof Long || v instanceof Integer || v instanceof Short || v instanceof Byte || v instanceof BigInteger;
    }

    private static Refusal longProblem(Object value) {
        if (value instanceof Boolean) return new Refusal("WrongKind", "", "a boolean is not an xsd:long");
        if (integral(value)) {
            BigInteger n = value instanceof BigInteger b ? b : BigInteger.valueOf(((Number) value).longValue());
            return n.compareTo(MIN) >= 0 && n.compareTo(MAX) <= 0 ? null : new Refusal("IllTypedLiteral", "", n + " is outside the range of xsd:long");
        }
        String datatype, lexical;
        if (value instanceof Lit l) {
            datatype = l.datatype();
            lexical = l.value();
        } else if (value instanceof Node n && n.isLiteral()) {
            datatype = n.getLiteralDatatypeURI();
            lexical = n.getLiteralLexicalForm();
            if (Namespaces.XSD_STRING.equals(datatype)) datatype = null;
        } else {
            return new Refusal("WrongKind", "", Text.repr(value) + " is not an xsd:long literal or an int");
        }
        if (!Namespaces.XSD_LONG.equals(datatype)) {
            return new Refusal("NotXsdLong", "", "the datatype is " + (datatype == null ? "xsd:string" : datatype) + ", and a position or epoch is exactly xsd:long on every store");
        }
        if (!LONG_LEXICAL.matcher(lexical).matches()) return new Refusal("IllTypedLiteral", "", Text.repr(lexical) + " is not a valid xsd:long");
        BigInteger n = new BigInteger(lexical);
        return n.compareTo(MIN) >= 0 && n.compareTo(MAX) <= 0 ? null : new Refusal("IllTypedLiteral", "", Text.repr(lexical) + " is not a valid xsd:long");
    }

    private static Refusal kindProblem(String kind, Object value) {
        switch (kind) {
            case "Iri":
                return iri(value) != null ? null : new Refusal("WrongKind", "", Text.repr(value) + " is not an IRI");
            case "Long", "Position":
                return longProblem(value);
            case "Digest":
                return value instanceof String s && DIGEST.matcher(s).matches() ? null : new Refusal("WrongKind", "", "a digest is 64 lower-case hexadecimal characters");
            case "String":
                return value instanceof String ? null : new Refusal("WrongKind", "", Text.repr(value) + " is not a string");
            case "LangString":
                return value instanceof Lit l && l.lang() != null ? null : new Refusal("WrongKind", "", "a language string is a Lit with a language tag");
            case "Literal":
                return value instanceof Lit ? null : new Refusal("WrongKind", "", "this parameter is a literal, and an IRI is not one");
            case "IriOrLiteral":
                return value instanceof Term ? null : new Refusal("WrongKind", "", "this parameter is an Iri or a Lit, and a bare string is neither");
            case "Payload":
                return value instanceof Payload ? null : new Refusal("WrongKind", "", "a payload is a Payload, and a bare string is not one");
            case "Rows":
                return value instanceof Rows ? null : new Refusal("WrongKind", "", "event rows are a Rows");
            case "RegistryList":
                return value instanceof Iterable ? null : new Refusal("WrongKind", "", "a list of graph IRIs is a sequence of Iri");
            default:
                return new Refusal("WrongKind", "", "unknown parameter kind " + Text.repr(kind));
        }
    }

    /** The value of an N-Triples string literal as the compile encoded it, for a binding such as {@code graphPrefix}. */
    public static String decodeLiteral(String text) {
        Model m = ModelFactory.createDefaultModel();
        RDFParser.create().source(new StringReader("<urn:x:s> <urn:x:p> " + text + " .")).lang(Lang.NTRIPLES).parse(m);
        return m.listObjects().next().asLiteral().getLexicalForm();
    }

    private static String quote(String s) {
        StringBuilder out = new StringBuilder();
        for (byte b : Text.utf8(s)) {
            char c = (char) (b & 0xFF);
            if (c < 128 && (Character.isLetterOrDigit(c) || "-_.~".indexOf(c) >= 0)) out.append(c);
            else out.append('%').append(String.format("%02X", b & 0xFF));
        }
        return out.toString();
    }

    /**
     * The graph of {@code root} by the family's naming rule (ADR-A122 decision 8): the prefix, the root encoded as {@code ENCODE_FOR_URI} does,
     * and the suffix. Null where the operation records no rule.
     */
    public static String graphName(OperationContract operation, Object root) {
        var prefix = operation.binding("graphPrefix");
        var suffix = operation.binding("graphSuffix");
        if (prefix.isEmpty() || suffix.isEmpty()) return null;
        return decodeLiteral(prefix.get()) + quote(plain(root)) + decodeLiteral(suffix.get());
    }

    /** Every reason the request {@code values} for {@code operation} is refused, sorted. Empty when it passes. */
    public static List<Refusal> refusals(OperationContract operation, Map<String, ?> values) {
        return refusals(operation, values, Options.none());
    }

    /** As {@link #refusals(OperationContract, Map)}, with options. */
    public static List<Refusal> refusals(OperationContract operation, Map<String, ?> values, Options options) {
        Set<Refusal> out = new TreeSet<>();
        Map<String, ParameterContract> declared = new TreeMap<>(Text.ORDER);
        for (ParameterContract p : operation.parameters()) declared.put(p.name(), p);
        for (String name : Text.sortedUnique(values.keySet())) {
            if (!declared.containsKey(name)) out.add(new Refusal("UnknownParameter", name, operation.templateId() + " declares no parameter " + Text.repr(name)));
        }
        Map<String, Object> typed = new HashMap<>();
        for (var entry : declared.entrySet()) {
            String name = entry.getKey();
            ParameterContract param = entry.getValue();
            Object value = values.get(name);
            if (value == null) {
                if (param.required()) out.add(new Refusal("MissingParameter", name, "a required parameter is not given"));
                continue;
            }
            Refusal problem = kindProblem(param.kind(), value);
            if (problem != null) out.add(new Refusal(problem.code(), name, problem.reason()));
            else typed.put(name, value);
            if (param.kind().equals("RegistryList") && typed.containsKey(name)) {
                List<Object> members = new ArrayList<>();
                ((Iterable<?>) value).forEach(members::add);
                if (members.isEmpty() && !options.allowEmptyLogGraphs()) {
                    out.add(new Refusal("EmptyLogGraphs", name, "an audit over no graph examines nothing and would report clean. Pass allowEmptyLogGraphs to have it report NothingExamined"));
                }
                members.stream().filter(m -> !(m instanceof Iri) && iri(m) == null).findFirst()
                    .ifPresent(bad -> out.add(new Refusal("LogGraphNotIri", name, Text.repr(bad) + " is not an IRI")));
            }
        }

        // a caller-named graph is the one the naming rule gives for the root (ADR-A123, addendum of 2026-10-12)
        for (ParameterContract param : declared.values()) {
            if (param.equalsGraphName() && typed.containsKey(param.name()) && typed.containsKey("root")) {
                String expected = graphName(operation, typed.get("root"));
                if (expected == null) {
                    out.add(new Refusal("GraphNameMismatch", param.name(), "the profile records no naming rule (dal:graphIriTemplate) to check it against"));
                } else if (!expected.equals(iri(typed.get(param.name())))) {
                    out.add(new Refusal("GraphNameMismatch", param.name(), "the graph of " + plain(typed.get("root")) + " is " + expected + ", not " + iri(typed.get(param.name()))));
                }
            }
        }

        // a payload names no subject outside the aggregate
        PayloadContract contract = operation.payload();
        if (contract != null && typed.containsKey(contract.parameter()) && contract.root() != null && typed.containsKey(contract.root())) {
            Payload payload = (Payload) typed.get(contract.parameter());
            Object root = typed.get(contract.root());
            List<Iri> stray = Bound.outsideBound(contract, root, payload);
            if (!stray.isEmpty()) {
                out.add(new Refusal("PayloadOutsideBound", contract.parameter(), stray.size() + " subject(s) are neither " + plain(root) + " nor reached from it by an owned edge, for example " + stray.get(0)));
            }
            if (options.versionOf() != null) out.addAll(referenceModes(contract, root, payload, options.versionOf()));
            if (options.membership() != null) out.addAll(membership(contract.parameter(), root, payload, options.membership()));
        }

        // an append: rows of events, and triples about the events alone
        if (operation.kind() == OperationKind.APPEND) {
            String rowsName = operation.parameters().stream().filter(p -> p.kind().equals("Rows")).map(ParameterContract::name).findFirst().orElse(null);
            String triplesName = operation.parameters().stream().filter(p -> p.kind().equals("Payload")).map(ParameterContract::name).findFirst().orElse(null);
            if (rowsName != null && typed.containsKey(rowsName)) {
                List<EventRow> rows = ((Rows) typed.get(rowsName)).rows();
                if (rows.isEmpty()) out.add(new Refusal("NoEvents", rowsName, "an append holds at least one event"));
                if (rows.stream().map(EventRow::event).distinct().count() != rows.size()) out.add(new Refusal("DuplicateEvent", rowsName, "each event of a batch has its own IRI"));
                if (rows.stream().map(EventRow::opSeq).distinct().count() != rows.size()) out.add(new Refusal("DuplicateOpSeq", rowsName, "opSeq is distinct within a batch"));
                if (triplesName != null && typed.containsKey(triplesName)) {
                    List<Iri> stray = Bound.outsideEvents(rows.stream().map(EventRow::event).toList(), (Payload) typed.get(triplesName));
                    if (!stray.isEmpty()) {
                        out.add(new Refusal("EventOutsideBound", triplesName, stray.get(0) + " is neither an event of the batch nor minted under one ({event}/part/...), so the append would describe it"));
                    }
                }
            }
        }
        return List.copyOf(out);
    }

    /** An object on a pinned edge is a version, and on an identity edge it is not. Every edge of every node the owned walk reaches (TD-67). */
    private static List<Refusal> referenceModes(PayloadContract contract, Object root, Payload payload, Predicate<Iri> versionOf) {
        List<Refusal> out = new ArrayList<>();
        Map<String, List<EdgeContract>> bySource = new HashMap<>();
        for (EdgeContract e : contract.edges()) bySource.computeIfAbsent(e.sourceShape(), k -> new ArrayList<>()).add(e);
        for (Bound.State state : Bound.reach(contract, root, payload)) {
            for (EdgeContract e : bySource.getOrDefault(state.shape(), List.of())) {
                for (Triple t : payload.triples()) {
                    if (!t.predicate().value().equals(e.predicate()) || !(t.object() instanceof Iri object)) continue;
                    if (e.inverse() ? object.value().equals(state.node()) : t.subject().value().equals(state.node())) {
                        Iri target = e.inverse() ? t.subject() : object;
                        boolean known = versionOf.test(target);
                        if (e.referenceMode().equals("Pinned") && !known) {
                            out.add(new Refusal("ReferenceModeViolation", e.predicate(), target.value() + " is on a pinned edge and is not known to be a version"));
                        } else if (e.referenceMode().equals("ByIdentity") && known) {
                            out.add(new Refusal("ReferenceModeViolation", e.predicate(), target.value() + " is a version, and this edge is by identity"));
                        }
                    }
                }
            }
        }
        return out;
    }

    /** Under delta membership a checkpoint version lists every member and states {@code pat:checkpoint true}, and any other version lists none. */
    private static List<Refusal> membership(String parameter, Object version, Payload payload, Membership m) {
        String v = plain(version), prop = m.property().value();
        Set<String> listed = new HashSet<>();
        boolean marked = false;
        for (Triple t : payload.triples()) {
            if (!t.subject().value().equals(v)) continue;
            if (t.predicate().value().equals(prop) && t.object() instanceof Iri o) listed.add(o.value());
            if (t.predicate().value().equals(Namespaces.PAT + "checkpoint") && t.object() instanceof Lit l && l.value().equals("true")) marked = true;
        }
        Set<String> members = new HashSet<>();
        for (Iri x : m.members()) members.add(x.value());
        if (m.checkpoint() && !(marked && listed.equals(members))) {
            return List.of(new Refusal("CheckpointNotFull", parameter, "a checkpoint states pat:checkpoint true and lists all " + members.size() + " member(s), and this lists " + listed.size() + (marked ? "" : " with no pat:checkpoint")));
        }
        if (!m.checkpoint() && (marked || !listed.isEmpty())) {
            return List.of(new Refusal("UnexpectedFullList", parameter, "a version that is not a checkpoint states its changes only, and lists no member and no pat:checkpoint"));
        }
        return List.of();
    }

    /** Throw {@link CallerCheckException} naming every reason, or return when the request passes. */
    public static void check(OperationContract operation, Map<String, ?> values) {
        check(operation, values, Options.none());
    }

    /** As {@link #check(OperationContract, Map)}, with options. */
    public static void check(OperationContract operation, Map<String, ?> values, Options options) {
        List<Refusal> found = refusals(operation, values, options);
        if (!found.isEmpty()) throw new CallerCheckException(operation, found);
    }
}
