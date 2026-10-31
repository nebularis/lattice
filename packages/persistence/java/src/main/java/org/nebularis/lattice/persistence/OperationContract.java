// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.persistence;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Optional;
import java.util.Set;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.Property;
import org.apache.jena.rdf.model.RDFNode;
import org.apache.jena.rdf.model.Resource;

/**
 * One generated operation of a compiled profile, as far as a caller needs it (ADR-A132 decisions 2 and 3). {@code node} is the operation's
 * node in the profile and may be null for a synthetic operation, {@code templateId} is its builder's name. {@code payload}, {@code digest}
 * and {@code examines} are null where the operation has none. {@link #read(Model)} reads every operation back from the RDF a compile
 * emits, and nothing is looked up in the compiler.
 */
public record OperationContract(
    Resource node, String templateId, OperationKind kind, int version, List<ParameterContract> parameters, PayloadContract payload,
    DigestSpec digest, List<Binding> bindings, String examines, List<String> outcomes) {

    public OperationContract {
        parameters = List.copyOf(parameters);
        bindings = List.copyOf(bindings);
        outcomes = List.copyOf(outcomes);
    }

    /** An operation with no bindings, no examined parameter and no outcome. */
    public OperationContract(Resource node, String templateId, OperationKind kind, int version, List<ParameterContract> parameters, PayloadContract payload, DigestSpec digest) {
        this(node, templateId, kind, version, parameters, payload, digest, List.of(), null, List.of());
    }

    /** The text of a compile-time binding, such as {@code graphPrefix}. */
    public Optional<String> binding(String name) {
        return bindings.stream().filter(b -> b.name().equals(name)).map(Binding::text).findFirst();
    }

    /** The declared parameter with this name. */
    public Optional<ParameterContract> parameter(String name) {
        return parameters.stream().filter(p -> p.name().equals(name)).findFirst();
    }

    public OperationContract withParameters(List<ParameterContract> parameters) {
        return new OperationContract(node, templateId, kind, version, parameters, payload, digest, bindings, examines, outcomes);
    }

    public OperationContract withBindings(List<Binding> bindings) {
        return new OperationContract(node, templateId, kind, version, parameters, payload, digest, bindings, examines, outcomes);
    }

    public OperationContract withPayload(PayloadContract payload) {
        return new OperationContract(node, templateId, kind, version, parameters, payload, digest, bindings, examines, outcomes);
    }

    // ---- reading a compiled profile

    private static Property p(Model m, String name) { return m.createProperty(Namespaces.DAL + name); }

    private static String local(RDFNode node) { return Text.local(node.isURIResource() ? node.asResource().getURI() : node.toString()); }

    private static String text(RDFNode node) { return node.isLiteral() ? node.asLiteral().getLexicalForm() : node.isURIResource() ? node.asResource().getURI() : node.toString(); }

    private static boolean bool(RDFNode node) {
        String t = text(node);
        return t.equals("true") || t.equals("1");
    }

    private static List<RDFNode> all(Model m, Resource s, String property) { return m.listObjectsOfProperty(s, p(m, property)).toList(); }

    private static RDFNode first(Model m, Resource s, String property) { return all(m, s, property).stream().findFirst().orElse(null); }

    private static RDFNode one(Model m, Resource s, String property) {
        List<RDFNode> values = all(m, s, property);
        if (values.size() != 1) throw new ProfileException(s + " should have exactly one " + property + ", found " + values.size());
        return values.get(0);
    }

    private static String paramName(Model m, RDFNode node) { return text(one(m, node.asResource(), "parameterName")); }

    private static DigestSpec digest(Model m, Resource node) {
        List<DigestPart> parts = new ArrayList<>();
        for (RDFNode part : all(m, node, "digestPart")) {
            Resource pr = part.asResource();
            List<String> sources = new ArrayList<>();
            for (RDFNode s : all(m, pr, "partSource")) {
                if (!(s.isURIResource() && s.asResource().getURI().equals(Namespaces.DAL + "NoSource"))) sources.add(paramName(m, s));
            }
            parts.add(new DigestPart(Integer.parseInt(text(one(m, pr, "partOrder")).trim()), local(one(m, pr, "partRole")), Text.sortedUnique(sources)));
        }
        parts.sort(null);
        return new DigestSpec(text(one(m, node, "digestAlgorithm")), parts);
    }

    private static PayloadContract payload(Model m, Resource node) {
        RDFNode root = first(m, node, "payloadRoot");
        List<EdgeContract> edges = new ArrayList<>();
        for (RDFNode en : all(m, node, "referenceEdge")) {
            Resource e = en.asResource();
            RDFNode targetClass = first(m, e, "edgeTargetClass");
            RDFNode targetShape = first(m, e, "edgeTargetShape");
            edges.add(new EdgeContract(
                text(one(m, e, "edgeSource")), text(one(m, e, "edgePredicate")), bool(one(m, e, "edgeInverse")), local(one(m, e, "edgeOwnership")),
                targetClass == null ? null : text(targetClass), local(one(m, e, "referenceMode")), targetShape == null ? null : text(targetShape)));
        }
        edges.sort(null);
        RDFNode shape = one(m, node, "boundaryShape");
        List<String> records = new ArrayList<>();
        for (Resource op : m.listSubjectsWithProperty(p(m, "payloadContract"), node).toList()) {
            for (Resource profile : m.listSubjectsWithProperty(p(m, "generatedOperation"), op).toList()) {
                for (RDFNode c : all(m, profile, "recordClass")) records.add(text(c));
            }
        }
        records.sort(Text.ORDER);
        return new PayloadContract(
            paramName(m, one(m, node, "payloadParameter")), root == null ? null : paramName(m, root), edges,
            shape.isURIResource() && shape.asResource().getURI().equals(Namespaces.DAL + "NoBoundaryShape") ? null : text(shape), records);
    }

    /**
     * The {@link OperationContract} of every generated operation in a compiled profile, in a stable order (template, then kind, then the
     * operation's parameters).
     */
    public static List<OperationContract> read(Model g) {
        Set<Resource> nodes = new LinkedHashSet<>(g.listSubjectsWithProperty(p(g, "operationKind")).toList());
        List<OperationContract> out = new ArrayList<>();
        for (Resource node : nodes) {
            Resource template = one(g, node, "usesTemplate").asResource();
            List<ParameterContract> parameters = new ArrayList<>();
            for (RDFNode pn : all(g, node, "parameter")) {
                Resource r = pn.asResource();
                parameters.add(new ParameterContract(
                    paramName(g, r), local(one(g, r, "parameterKind")).replaceFirst("Kind$", ""), bool(one(g, r, "required")),
                    r.hasProperty(p(g, "mustEqual")), r.hasProperty(p(g, "sourcedFrom"))));
            }
            parameters.sort(null);
            RDFNode pc = first(g, node, "payloadContract");
            RDFNode dc = first(g, node, "digestContract");
            List<Binding> bindings = new ArrayList<>();
            for (RDFNode b : all(g, node, "hasParameterBinding")) {
                bindings.add(new Binding(text(one(g, b.asResource(), "paramName")), text(one(g, b.asResource(), "paramValue"))));
            }
            bindings.sort(null);
            RDFNode ex = first(g, node, "examinedParameter");
            List<String> outcomes = new ArrayList<>();
            for (RDFNode o : all(g, node, "reportsOutcome")) outcomes.add(local(o));
            outcomes.sort(Text.ORDER);
            out.add(new OperationContract(
                node, text(one(g, template, "templateId")), OperationKind.of(local(one(g, node, "operationKind"))),
                Integer.parseInt(text(one(g, node, "templateVersion")).trim()), parameters,
                pc == null ? null : payload(g, pc.asResource()), dc == null ? null : digest(g, dc.asResource()), bindings,
                ex == null ? null : paramName(g, ex), outcomes));
        }
        out.sort(Comparator.comparing(OperationContract::templateId, Text.ORDER)
            .thenComparing((OperationContract o) -> o.kind().value(), Text.ORDER)
            .thenComparing((OperationContract o) -> String.join(",", o.parameters().stream().map(ParameterContract::name).toList()), Text.ORDER)
            .thenComparing((OperationContract o) -> String.valueOf(o.node()), Text.ORDER));
        return List.copyOf(out);
    }
}
