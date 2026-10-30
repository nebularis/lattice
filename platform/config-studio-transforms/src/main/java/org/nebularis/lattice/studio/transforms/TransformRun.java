// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.transforms;

import java.io.StringWriter;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.TreeSet;
import org.apache.jena.atlas.json.JSON;
import org.apache.jena.atlas.json.JsonArray;
import org.apache.jena.atlas.json.JsonObject;
import org.apache.jena.atlas.json.JsonValue;
import org.apache.jena.datatypes.xsd.XSDDatatype;
import org.apache.jena.graph.Graph;
import org.apache.jena.graph.Node;
import org.apache.jena.graph.NodeFactory;
import org.apache.jena.graph.Triple;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.ModelFactory;
import org.apache.jena.rdf.model.Property;
import org.apache.jena.rdf.model.RDFNode;
import org.apache.jena.rdf.model.Resource;
import org.apache.jena.rdf.model.ResourceFactory;
import org.apache.jena.rdf.model.Statement;
import org.apache.jena.riot.Lang;
import org.apache.jena.riot.RDFDataMgr;
import org.apache.jena.riot.RDFParser;
import org.apache.jena.sparql.graph.GraphFactory;
import org.apache.jena.vocabulary.RDF;
import org.nebularis.lattice.morktransforms.TransformException;
import org.nebularis.lattice.morktransforms.Transforms;
import org.nebularis.lattice.studio.store.Cst;

/**
 * One run of a compile job's transforms over a sample source (ADR-A148): each scheme with a transform of the sample's
 * format is run, and what it wrote is attributed to its mappings by the scheme's attribution table, as one N-Triples
 * artefact for each mapping, grouped by the mapping, in the shape of a mapping dry run's. A scheme with no transform of
 * that format is reported as not run.
 */
public final class TransformRun {
    /** Each format's transform, by media type or path, and the sample media types it reads. */
    private enum Format {
        XML("XML", Lang.NTRIPLES), JSON("JSON", Lang.JSONLD);

        final String label;
        final Lang output;

        Format(String label, Lang output) {
            this.label = label;
            this.output = output;
        }

        static Format of(String mediaType) {
            String type = mediaType == null ? "" : mediaType.split(";", 2)[0].trim().toLowerCase(java.util.Locale.ROOT);
            return switch (type) {
                case "application/xml", "text/xml" -> XML;
                case "application/json" -> JSON;
                default -> null;
            };
        }

        boolean isTransform(String path, String mediaType) {
            return this == XML ? "application/xslt+xml".equals(mediaType) : path.endsWith(".jolt.json");
        }
    }

    private record Artefact(String path, String mediaType, String content) {
    }

    /** The SHACL terms of a report, named here so the worker needs no SHACL engine. */
    private static final class SHACLM {
        static final String NS = "http://www.w3.org/ns/shacl#";
        static final Resource ValidationReport = ResourceFactory.createResource(NS + "ValidationReport");
        static final Resource ValidationResult = ResourceFactory.createResource(NS + "ValidationResult");
        static final Resource Violation = ResourceFactory.createResource(NS + "Violation");
        static final Resource Info = ResourceFactory.createResource(NS + "Info");
        static final Property conforms = ResourceFactory.createProperty(NS + "conforms");
        static final Property result = ResourceFactory.createProperty(NS + "result");
        static final Property resultSeverity = ResourceFactory.createProperty(NS + "resultSeverity");
        static final Property resultMessage = ResourceFactory.createProperty(NS + "resultMessage");
        static final Property focusNode = ResourceFactory.createProperty(NS + "focusNode");
    }

    private TransformRun() {
    }

    /** The reply to a run of {@code jobIri}'s transforms over {@code sample}, described under {@code runIri}. */
    public static Model run(Model job, String jobIri, String runIri, String mediaType, String sample) {
        Reply reply = new Reply(runIri, jobIri);
        Resource compile = job.createResource(jobIri);
        Format format = Format.of(mediaType);
        if (format == null) {
            return reply.failed("a sample source is application/xml, text/xml or application/json, not " + mediaType);
        }
        if (!compile.hasProperty(Cst.kind, Cst.Compile) || !compile.hasProperty(Cst.target, Cst.target("mapping"))
            || !compile.hasProperty(Cst.status, Cst.Succeeded)) {
            return reply.failed("the job is not a finished compilation of the mapping part");
        }
        Map<String, List<Artefact>> groups = new TreeMap<>();
        for (Statement s : compile.listProperties(Cst.artefact).toList()) {
            Resource a = s.getResource();
            String group = string(a, Cst.group);
            if (group != null) {
                groups.computeIfAbsent(group, g -> new ArrayList<>()).add(new Artefact(
                    String.valueOf(string(a, Cst.path)), string(a, Cst.mediaType), String.valueOf(string(a, Cst.content))));
            }
        }
        boolean ran = false;
        for (Map.Entry<String, List<Artefact>> group : groups.entrySet()) {
            String scheme = group.getKey();
            Artefact transform = group.getValue().stream().filter(a -> format.isTransform(a.path(), a.mediaType())).findFirst().orElse(null);
            if (transform == null) {
                if (group.getValue().stream().anyMatch(a -> a.path().endsWith(".attribution.json") || a.path().endsWith(".compiled.ttl"))) {
                    reply.finding(SHACLM.Info, scheme + " was not run, since it reads no " + format.label + " source", "NotRun", scheme);
                }
                continue;
            }
            Artefact table = group.getValue().stream().filter(a -> a.path().equals(transform.path() + ".attribution.json")).findFirst().orElse(null);
            if (table == null) {
                reply.finding(SHACLM.Violation, scheme + " has no attribution table beside its transform", "NoAttribution", scheme);
                continue;
            }
            Graph written = GraphFactory.createDefaultGraph();
            try {
                String output = format == Format.XML ? Transforms.xslt(transform.content(), sample) : Transforms.jolt(transform.content(), sample);
                RDFParser.fromString(output, format.output).parse(written);
            } catch (TransformException | RuntimeException e) {
                return reply.failed(scheme + ": " + e.getMessage());
            }
            ran = true;
            for (Map.Entry<String, Set<String>> wrote : attribute(written, JSON.parseAny(table.content()).getAsArray()).entrySet()) {
                reply.artefact(wrote.getKey(), String.join("", wrote.getValue()));
            }
        }
        if (!ran) {
            reply.finding(SHACLM.Info, "no scheme of the mapping part reads a " + format.label + " source", "NotRun", null);
        }
        return reply.done();
    }

    /**
     * What each mapping wrote, by the table `mork_transforms.attribution` writes: a node is a datum's when it has one of
     * the datum's types, or its IRI is the datum's IRI or starts with the datum's prefix. A datum's mapping writes its
     * types and its glue, and each assertion's mapping its property, from the datum's node or, inverse, to it. Each
     * mapping's triples are N-Triples lines, in code point order.
     */
    static Map<String, Set<String>> attribute(Graph written, JsonArray table) {
        Map<String, Set<String>> out = new TreeMap<>();
        for (JsonValue v : table) {
            JsonObject row = v.getAsObject();
            String mapping = row.get("mapping").getAsString().value();
            Set<Node> types = new java.util.HashSet<>();
            row.get("types").getAsArray().forEach(t -> types.add(NodeFactory.createURI(t.getAsString().value())));
            String iri = text(row, "iri");
            String prefix = text(row, "prefix");
            java.util.function.Predicate<Node> mine = n -> n.isURI() && (n.getURI().equals(iri) || (prefix != null && !prefix.isEmpty()
                && n.getURI().startsWith(prefix)) || types.stream().anyMatch(t -> written.contains(n, RDF.type.asNode(), t)));
            for (Triple t : written.find().toList()) {
                if (t.getPredicate().equals(RDF.type.asNode()) && types.contains(t.getObject()) && mine.test(t.getSubject())) {
                    add(out, mapping, t);
                }
            }
            if (row.get("glue") != null && row.get("glue").isObject()) {
                JsonObject glue = row.get("glue").getAsObject();
                written(written, glue.get("property").getAsString().value(), glue.get("parentIsSubject").getAsBoolean().value(), mine, out, mapping);
            }
            for (JsonValue a : row.get("assertions").getAsArray()) {
                JsonObject assertion = a.getAsObject();
                written(written, assertion.get("property").getAsString().value(), assertion.get("inverse").getAsBoolean().value(), mine,
                    out, assertion.get("mapping").getAsString().value());
            }
        }
        return out;
    }

    private static void written(Graph g, String property, boolean toTheNode, java.util.function.Predicate<Node> mine,
                                Map<String, Set<String>> out, String mapping) {
        for (Triple t : g.find(Node.ANY, NodeFactory.createURI(property), Node.ANY).toList()) {
            if (mine.test(toTheNode ? t.getObject() : t.getSubject())) {
                add(out, mapping, t);
            }
        }
    }

    private static void add(Map<String, Set<String>> out, String mapping, Triple t) {
        Graph one = GraphFactory.createDefaultGraph();
        one.add(t);
        StringWriter line = new StringWriter();
        RDFDataMgr.write(line, one, Lang.NTRIPLES);
        out.computeIfAbsent(mapping, m -> new TreeSet<>()).add(line.toString());
    }

    private static String text(JsonObject row, String key) {
        JsonValue v = row.get(key);
        return v != null && v.isString() ? v.getAsString().value() : null;
    }

    private static String string(Resource r, Property p) {
        Statement s = r.getProperty(p);
        return s == null || !s.getObject().isLiteral() ? null : s.getString();
    }

    /** The reply graph, minted under the run's IRI as a job graph is under the job's. */
    private static final class Reply {
        private final Model m = ModelFactory.createDefaultModel();
        private final Resource run;
        private final Resource report;
        private int count;
        private boolean violation;

        Reply(String runIri, String jobIri) {
            run = m.createResource(runIri).addProperty(RDF.type, Cst.Transform).addProperty(Cst.compileJob, m.createResource(jobIri));
            report = m.createResource(runIri + "#report").addProperty(RDF.type, SHACLM.ValidationReport);
            run.addProperty(Cst.report, report);
        }

        void finding(Resource severity, String message, String code, String focus) {
            violation |= severity.equals(SHACLM.Violation);
            Resource r = m.createResource(run.getURI() + "#result-" + ++count).addProperty(RDF.type, SHACLM.ValidationResult)
                .addProperty(SHACLM.resultSeverity, severity).addProperty(SHACLM.resultMessage, message).addProperty(Cst.code, code);
            if (focus != null && focus.contains(":")) {
                r.addProperty(SHACLM.focusNode, m.createResource(focus));
            }
            report.addProperty(SHACLM.result, r);
        }

        void artefact(String mapping, String ntriples) {
            String name = mapping.replaceAll(".*[#/]", "").replaceAll("[^A-Za-z0-9_-]+", "-");
            run.addProperty(Cst.artefact, m.createResource(run.getURI() + "#artefact-" + ++count).addProperty(RDF.type, Cst.Artefact)
                .addProperty(Cst.path, "0/" + (name.isEmpty() ? "mapping" : name) + ".nt").addProperty(Cst.mediaType, "application/n-triples")
                .addProperty(Cst.content, ntriples).addProperty(Cst.group, mapping)
                .addLiteral(Cst.stratum, m.createTypedLiteral("0", XSDDatatype.XSDnonNegativeInteger)));
        }

        Model failed(String message) {
            run.addProperty(Cst.status, Cst.Failed).addProperty(Cst.failureMessage, message);
            return m;
        }

        Model done() {
            RDFNode conforms = m.createTypedLiteral(!violation);
            run.addProperty(Cst.status, Cst.Succeeded).addProperty(Cst.conforms, conforms);
            report.addProperty(SHACLM.conforms, conforms);
            return m;
        }
    }
}
