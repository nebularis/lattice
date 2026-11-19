// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.transforms;

import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.TreeSet;
import java.util.concurrent.TimeUnit;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.apache.jena.atlas.json.JSON;
import org.apache.jena.atlas.json.JsonArray;
import org.apache.jena.atlas.json.JsonNull;
import org.apache.jena.atlas.json.JsonObject;
import org.apache.jena.datatypes.xsd.XSDDatatype;
import org.apache.jena.graph.Node;
import org.apache.jena.graph.NodeFactory;
import org.apache.jena.query.ARQ;
import org.apache.jena.query.DatasetFactory;
import org.apache.jena.query.ParameterizedSparqlString;
import org.apache.jena.query.QueryCancelledException;
import org.apache.jena.query.QueryExecution;
import org.apache.jena.query.QueryExecutionFactory;
import org.apache.jena.query.QuerySolution;
import org.apache.jena.query.ResultSet;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.ModelFactory;
import org.apache.jena.rdf.model.Property;
import org.apache.jena.rdf.model.RDFNode;
import org.apache.jena.rdf.model.Resource;
import org.apache.jena.rdf.model.ResourceFactory;
import org.apache.jena.rdf.model.Statement;
import org.apache.jena.riot.Lang;
import org.apache.jena.riot.RDFParser;
import org.apache.jena.riot.RiotException;
import org.apache.jena.riot.out.NodeFmtLib;
import org.apache.jena.sparql.core.DatasetGraph;
import org.apache.jena.sparql.core.DatasetGraphFactory;
import org.apache.jena.sparql.core.Quad;
import org.apache.jena.sparql.exec.UpdateExec;
import org.apache.jena.system.Txn;
import org.apache.jena.update.UpdateFactory;
import org.apache.jena.update.UpdateRequest;
import org.apache.jena.vocabulary.RDF;
import org.nebularis.lattice.persistence.CallerCheck;
import org.nebularis.lattice.persistence.Confirmation;
import org.nebularis.lattice.persistence.ConfirmationException;
import org.nebularis.lattice.persistence.DigestException;
import org.nebularis.lattice.persistence.Iri;
import org.nebularis.lattice.persistence.Namespaces;
import org.nebularis.lattice.persistence.OperationContract;
import org.nebularis.lattice.persistence.OperationKind;
import org.nebularis.lattice.persistence.ParameterContract;
import org.nebularis.lattice.persistence.Payload;
import org.nebularis.lattice.persistence.PayloadException;
import org.nebularis.lattice.persistence.ProfileException;
import org.nebularis.lattice.persistence.Refusal;
import org.nebularis.lattice.persistence.RequestDigest;
import org.nebularis.lattice.persistence.SparqlTermException;
import org.nebularis.lattice.studio.store.Cst;

/**
 * One step of the persistence simulator (SVA-P3, ADR-A154 decisions 1 and 11, contract Runs, "A persistence step"). A step is a function of
 * its compile job and its input alone, and the time it runs at is the one the input states (PRI-56). It reads the compiled profile and the
 * operation's SPARQL from the job, checks and binds the request with the Java caller library (ADR-A132), replaces each {@code NOW()} with the
 * stated time ({@link NowPinning}), runs the update over a fresh in-memory Jena dataset made from the sample world, and tells the result
 * as four parts, each in a canonical order. Nothing is shared with another step, and nothing is stored.
 */
final class PersistenceStep {
    /** The engine every simulated write is shown to have run on (ADR-A154 decision 12). */
    static final String ENGINE = "Apache Jena ARQ " + ARQ.VERSION + ", in memory";
    private static final Set<OperationKind> RUNS = Set.of(OperationKind.CREATE, OperationKind.REPLACE, OperationKind.DELTA_REPLACE, OperationKind.TOMBSTONE);
    private static final Set<String> PAYLOAD_CODES = Set.of("PayloadOutsideBound", "EventOutsideBound");
    private static final Pattern SLOT = Pattern.compile("\\{\\{\\{([A-Za-z]+)\\}\\}\\}");
    private static final Pattern LONG = Pattern.compile("[+-]?[0-9]+");
    private static final Comparator<String> BYTES = (a, b) -> Arrays.compareUnsigned(a.getBytes(StandardCharsets.UTF_8), b.getBytes(StandardCharsets.UTF_8));

    private PersistenceStep() {
    }

    /** A part of a step's result, which the run turns into frames. */
    record Part(String role, String mediaType, String text) {
    }

    /** The parts of a step in order, or the reason the step could not be run, in words an author reads. */
    record Result(String failure, List<Part> parts) {
        Result {
            parts = List.copyOf(parts);
        }

        static Result failed(String message) {
            return new Result(message, List.of());
        }
    }

    private static final class Failed extends Exception {
        private static final long serialVersionUID = 1L;

        Failed(String message) {
            super(message);
        }
    }

    private static Property dal(String name) {
        return ResourceFactory.createProperty(Namespaces.DAL + name);
    }

    private static String string(Resource r, Property p) {
        Statement s = r.getProperty(p);
        return s == null || !s.getObject().isLiteral() ? null : s.getString();
    }

    private static String local(String iri) {
        String trimmed = iri.replaceAll("[/#]+$", "");
        return trimmed.substring(Math.max(trimmed.lastIndexOf('#'), trimmed.lastIndexOf('/')) + 1);
    }

    /**
     * Runs the step in {@code trig} against the compile job {@code jobIri}. {@code budgetMillis} bounds the update, as far as Jena stops
     * one, and the run worker stops the whole execution at the run's deadline whatever Jena does.
     */
    static Result execute(Model job, String jobIri, String trig, long budgetMillis) {
        try {
            return new Result(null, run(job, jobIri, trig, budgetMillis));
        } catch (Failed | StepRequest.StepFormatException e) {
            return Result.failed(e.getMessage());
        }
    }

    private static List<Part> run(Model job, String jobIri, String trig, long budgetMillis) throws Failed, StepRequest.StepFormatException {
        Resource compile = job.createResource(jobIri);
        if (!compile.hasProperty(Cst.kind, Cst.Compile) || !compile.hasProperty(Cst.target, Cst.target("persistence"))
            || !compile.hasProperty(Cst.status, Cst.Succeeded)) {
            throw new Failed("The job is not a finished compilation of the persistence part, so this step was not run.");
        }
        Map<String, String> artefacts = new HashMap<>();
        for (Statement s : compile.listProperties(Cst.artefact).toList()) {
            String path = string(s.getResource(), Cst.path);
            String content = string(s.getResource(), Cst.content);
            if (path != null && content != null) {
                artefacts.put(path, content);
            }
        }
        StepRequest step = StepRequest.parse(trig);

        Model profileModel = profile(artefacts);
        Resource profile = profileOf(profileModel, step);
        OperationContract contract = operationOf(profileModel, profile, step.operation());
        String text = sparqlOf(profile, contract, step, artefacts);
        Map<String, Payload> payloads = payloads(contract, step);
        Map<String, Object> values = values(contract, step, payloads);

        List<Refusal> refusals = CallerCheck.refusals(contract, values).stream()
            .filter(r -> !(r.code().equals("MissingParameter") && r.where().equals("requestDigest"))).toList();
        List<Part> parts = new ArrayList<>();
        parts.add(new Part("check", "application/json", checkJson(contract, refusals)));
        if (!refusals.isEmpty()) {
            parts.add(new Part("outcome", "application/json", refused(refusals)));
            return parts;
        }
        if (contract.parameter("requestDigest").isPresent()) {
            try {
                values.put("requestDigest", RequestDigest.requestDigest(contract, values));
            } catch (DigestException e) {
                throw new Failed("The request digest could not be computed. " + e.getMessage());
            }
        }

        UpdateRequest sent = bind(contract, text, values, payloads);
        NowPinning.Pinned pinned = NowPinning.pin(sent, step.transactionTime());
        parts.add(new Part("request", "application/sparql-update", "# Each NOW() of the operation was replaced with " + NodeFmtLib.strNT(step.transactionTime())
            + ", the step's cst:transactionTime. The engine reads no clock.\n" + pinned.request()));

        DatasetGraph dataset = DatasetGraphFactory.createTxnMem();
        Txn.executeWrite(dataset, () -> step.world().find().forEachRemaining(dataset::add));
        Set<Quad> before = Txn.calculateRead(dataset, () -> quads(dataset));
        try {
            Txn.executeWrite(dataset, () -> UpdateExec.dataset(dataset).update(pinned.request()).timeout(Math.max(budgetMillis, 1), TimeUnit.MILLISECONDS).build().execute());
        } catch (QueryCancelledException e) {
            throw new Failed("The update was still running at the run's deadline, so it was stopped.");
        } catch (RuntimeException e) {
            throw new Failed("Jena could not run the update. " + e.getMessage());
        }
        Set<Quad> after = Txn.calculateRead(dataset, () -> quads(dataset));

        LandingPlaces.Values placeValues = new LandingPlaces.Values(step.parameters().get("root"), step.parameters().get("newRev"), step.month());
        List<LandingPlaces.Place> places = LandingPlaces.of(profileModel, profile);
        Set<Quad> added = new HashSet<>(after);
        added.removeAll(before);
        Set<Quad> removed = new HashSet<>(before);
        removed.removeAll(after);
        parts.add(new Part("delta", "application/json", delta(places, placeValues, added, removed)));
        parts.add(new Part("outcome", "application/json", confirmed(dataset, contract, values)));
        return parts;
    }

    // ---- reading the job

    private static Model profile(Map<String, String> artefacts) throws Failed {
        String turtle = artefacts.get("compiled-profile.ttl");
        if (turtle == null) {
            throw new Failed("The job holds no compiled profile (compiled-profile.ttl), so this step was not run.");
        }
        Model model = ModelFactory.createDefaultModel();
        try {
            RDFParser.fromString(turtle, Lang.TURTLE).errorHandler(QuietErrors.INSTANCE).parse(model);
        } catch (RiotException e) {
            throw new Failed("The job's compiled profile could not be read, so this step was not run.");
        }
        return model;
    }

    private static Resource profileOf(Model model, StepRequest step) throws Failed {
        List<Resource> found = new ArrayList<>();
        for (Resource p : model.listSubjectsWithProperty(RDF.type, model.createResource(Namespaces.DAL + "CompiledProfile")).toList()) {
            Resource target = p.getPropertyResourceValue(dal("forTarget"));
            Resource deployment = p.getPropertyResourceValue(dal("forDeployment"));
            boolean sameDeployment = step.deployment() == null || (deployment != null && deployment.getURI().equals(step.deployment()));
            if (target != null && target.getURI().equals(step.targetClass()) && sameDeployment) {
                found.add(p);
            }
        }
        if (found.isEmpty()) {
            throw new Failed("The compiled profile has no profile for the class <" + step.targetClass() + ">"
                + (step.deployment() == null ? "" : " and the deployment <" + step.deployment() + ">") + ".");
        }
        if (found.size() > 1) {
            throw new Failed("The class <" + step.targetClass() + "> has a compiled profile for more than one deployment, so the step must say which with cst:forDeployment.");
        }
        return found.get(0);
    }

    private static OperationContract operationOf(Model model, Resource profile, String name) throws Failed {
        List<OperationContract> all;
        try {
            all = OperationContract.read(model);
        } catch (ProfileException | IllegalStateException e) {
            throw new Failed("The job's compiled profile could not be read as operations, so this step was not run.");
        }
        Set<Resource> mine = new HashSet<>();
        model.listObjectsOfProperty(profile, dal("generatedOperation")).forEachRemaining(o -> mine.add(o.asResource()));
        TreeMap<String, OperationContract> byName = new TreeMap<>();
        for (OperationContract c : all) {
            if (c.node() != null && mine.contains(c.node()) && string(c.node(), dal("forOperation")) != null) {
                byName.put(string(c.node(), dal("forOperation")), c);
            }
        }
        OperationContract chosen = byName.get(name);
        if (chosen == null) {
            throw new Failed("The profile has no operation called " + name + ". Its operations are " + String.join(", ", byName.keySet()) + ".");
        }
        if (!RUNS.contains(chosen.kind())) {
            throw new Failed("The operation " + name + " is of kind " + chosen.kind().value() + ", and a step runs only a Create, Replace, DeltaReplace or Tombstone.");
        }
        return chosen;
    }

    /** The operation's SPARQL, found in the job as the compiler wrote it, at {@code {class}[.{deployment}]/{operation}.rq}. */
    private static String sparqlOf(Resource profile, OperationContract contract, StepRequest step, Map<String, String> artefacts) throws Failed {
        Resource deployment = profile.getPropertyResourceValue(dal("forDeployment"));
        String group = local(step.targetClass()) + (deployment == null ? "" : "." + local(deployment.getURI()));
        String path = group + "/" + step.operation().replace(":", "_").replace("/", "_") + ".rq";
        String text = artefacts.get(path);
        if (text == null) {
            throw new Failed("The job holds no SPARQL for the operation " + step.operation() + " (expected at " + path + "), so this step was not run.");
        }
        return text;
    }

    // ---- binding

    private static Map<String, Payload> payloads(OperationContract contract, StepRequest step) throws Failed {
        String main = contract.payload() == null ? null : contract.payload().parameter();
        Map<String, Payload> out = new HashMap<>();
        Set<String> keys = new TreeSet<>();
        for (ParameterContract p : contract.parameters()) {
            if (p.kind().equals("Payload")) {
                String key = p.name().equals(main) ? "" : p.name();
                keys.add(key);
                try {
                    out.put(p.name(), Payload.ofJena(step.payloads().getOrDefault(key, List.of())));
                } catch (PayloadException e) {
                    throw new Failed("The payload graph <" + graphOf(key) + "> cannot be a payload. " + e.getMessage());
                }
            }
        }
        for (String key : step.payloads().keySet()) {
            if (!keys.contains(key)) {
                String valid = keys.isEmpty() ? "takes no payload" : "reads its payloads from " + keys.stream().map(k -> "<" + graphOf(k) + ">").toList();
                throw new Failed("The graph <" + graphOf(key) + "> is not a payload graph of the operation " + step.operation() + ", which " + valid + ".");
            }
        }
        return out;
    }

    private static String graphOf(String key) {
        if (key.startsWith("?")) {
            return key.substring(1);
        }
        return key.isEmpty() ? StepRequest.PAYLOAD_GRAPH : StepRequest.PAYLOAD_GRAPH + "/" + key;
    }

    private static Map<String, Object> values(OperationContract contract, StepRequest step, Map<String, Payload> payloads) throws Failed {
        Map<String, Object> values = new HashMap<>(payloads);
        Set<String> declared = new HashSet<>();
        for (ParameterContract p : contract.parameters()) {
            declared.add(p.name());
            if (p.kind().equals("Payload")) {
                continue;
            }
            String stated = step.parameters().get(p.name());
            if (p.name().equals("requestDigest")) {
                if (stated != null) {
                    throw new Failed("The step states requestDigest. The caller library computes it from the request, so leave it out.");
                }
                continue;
            }
            if (stated == null) {
                continue;
            }
            switch (p.kind()) {
                case "Iri" -> {
                    try {
                        values.put(p.name(), Iri.of(stated));
                    } catch (SparqlTermException e) {
                        throw new Failed("The parameter " + p.name() + " is not an IRI the caller library accepts. " + e.getMessage());
                    }
                }
                case "Long", "Position" -> {
                    if (!LONG.matcher(stated).matches()) {
                        throw new Failed("The parameter " + p.name() + " must be a whole number, and the step gives " + quote(stated) + ".");
                    }
                    try {
                        values.put(p.name(), Long.parseLong(stated.startsWith("+") ? stated.substring(1) : stated));
                    } catch (NumberFormatException e) {
                        throw new Failed("The parameter " + p.name() + " is outside the range of xsd:long.");
                    }
                }
                case "Digest", "String" -> values.put(p.name(), stated);
                default -> throw new Failed("The operation " + step.operation() + " has the parameter " + p.name() + " of kind " + p.kind() + ", which a step does not bind.");
            }
        }
        for (ParameterContract p : contract.parameters()) {
            if (!p.kind().equals("Payload") && !p.name().equals("requestDigest") && !step.parameters().containsKey(p.name()) && p.required()
                && !List.of("Iri", "Long", "Position", "Digest", "String").contains(p.kind())) {
                throw new Failed("The operation " + step.operation() + " has the parameter " + p.name() + " of kind " + p.kind() + ", which a step does not bind.");
            }
        }
        // A parameter the operation does not declare is left to the caller check, which names it.
        step.parameters().forEach((name, value) -> {
            if (!declared.contains(name)) {
                values.put(name, value);
            }
        });
        return values;
    }

    private static String quote(String text) {
        return "\"" + (text.length() > 40 ? text.substring(0, 40) + "..." : text) + "\"";
    }

    /** The operation's text with each parameter bound as a typed term and then each slot filled, so nothing in a payload is read as a variable. */
    private static UpdateRequest bind(OperationContract contract, String text, Map<String, Object> values, Map<String, Payload> payloads) throws Failed {
        ParameterizedSparqlString bound = new ParameterizedSparqlString(text);
        for (ParameterContract p : contract.parameters()) {
            Object value = values.get(p.name());
            if (value == null || p.kind().equals("Payload")) {
                continue;
            }
            switch (p.kind()) {
                case "Iri" -> bound.setParam(p.name(), NodeFactory.createURI(((Iri) value).value()));
                case "Long", "Position" -> bound.setParam(p.name(), NodeFactory.createLiteralDT(value.toString(), XSDDatatype.XSDlong));
                default -> bound.setParam(p.name(), NodeFactory.createLiteralString((String) value));
            }
        }
        Matcher m = SLOT.matcher(bound.toString());
        String filled = m.replaceAll(r -> {
            Payload payload = payloads.get(r.group(1));
            return Matcher.quoteReplacement(payload == null ? r.group() : Payload.slotText(contract, r.group(1), payload));
        });
        if (SLOT.matcher(filled).find()) {
            throw new Failed("The operation " + contract.templateId() + " has a slot that the step does not fill.");
        }
        try {
            return UpdateFactory.create(filled);
        } catch (RuntimeException e) {
            throw new Failed("The operation's SPARQL did not parse once bound. " + e.getMessage());
        }
    }

    // ---- the parts

    private static JsonObject refusal(Refusal r) {
        JsonObject o = new JsonObject();
        o.put("code", r.code());
        o.put("where", r.where());
        o.put("reason", r.reason());
        return o;
    }

    private static JsonObject check(String name, String verdict, List<Refusal> reasons, String note) {
        JsonObject o = new JsonObject();
        o.put("name", name);
        o.put("verdict", verdict);
        JsonArray array = new JsonArray();
        reasons.forEach(r -> array.add(refusal(r)));
        o.put("reasons", array);
        if (note != null) {
            o.put("note", note);
        }
        return o;
    }

    /** What the caller library checked before sending, and the payload check, each with its verdict. The library gives its reasons sorted. */
    private static String checkJson(OperationContract contract, List<Refusal> refusals) {
        List<Refusal> payload = refusals.stream().filter(r -> PAYLOAD_CODES.contains(r.code())).toList();
        List<Refusal> caller = refusals.stream().filter(r -> !PAYLOAD_CODES.contains(r.code())).toList();
        JsonObject root = new JsonObject();
        root.put("operation", contract.node() == null ? contract.templateId() : string(contract.node(), dal("forOperation")));
        root.put("template", contract.templateId());
        root.put("kind", contract.kind().value());
        JsonArray checks = new JsonArray();
        checks.add(check("callerCheck", caller.isEmpty() ? "passed" : "refused", caller, null));
        if (contract.kind() == OperationKind.DELTA_REPLACE) {
            checks.add(check("payloadCheck", payload.isEmpty() ? "notRun" : "refused", payload,
                payload.isEmpty() ? "A delta's bound is checked over the state it leaves, which a step does not hold, so only the overlap and the empty delta are checked." : null));
        } else if (contract.payload() == null) {
            checks.add(check("payloadCheck", "notRun", payload, "The operation takes no payload."));
        } else {
            checks.add(check("payloadCheck", payload.isEmpty() ? "passed" : "refused", payload, null));
        }
        root.put("checks", checks);
        return JSON.toString(root);
    }

    private static String refused(List<Refusal> refusals) {
        JsonObject o = new JsonObject();
        o.put("outcome", "refused");
        o.put("classification", "RefusedByCallerCheck");
        o.put("reason", "The caller library refused the request before it was sent, for " + String.join(", ", refusals.stream().map(Refusal::code).toList()) + ".");
        return JSON.toString(o);
    }

    private static Set<Quad> quads(DatasetGraph dataset) {
        Set<Quad> out = new HashSet<>();
        dataset.find().forEachRemaining(out::add);
        return out;
    }

    private static String graphName(Node graph) {
        if (Quad.isDefaultGraph(graph)) {
            return "";
        }
        return graph.isURI() ? graph.getURI() : "_:" + graph.getBlankNodeLabel();
    }

    private static String line(Quad q) {
        return NodeFmtLib.strNT(q.getSubject()) + " " + NodeFmtLib.strNT(q.getPredicate()) + " " + NodeFmtLib.strNT(q.getObject()) + " .";
    }

    private static Map<String, List<String>> byGraph(Set<Quad> quads) {
        Map<String, List<String>> out = new TreeMap<>(BYTES);
        for (Quad q : quads) {
            out.computeIfAbsent(graphName(q.getGraph()), g -> new ArrayList<>()).add(line(q));
        }
        out.values().forEach(lines -> lines.sort(BYTES));
        return out;
    }

    private static JsonArray strings(List<String> lines) {
        JsonArray a = new JsonArray();
        lines.forEach(a::add);
        return a;
    }

    /**
     * The quads added and removed in each graph, grouped by the landing places of the compiled profile. A graph is assigned to a place only by
     * equality with the place's graph, or with its template rendered from the step's own values. A changed graph that no place matches is
     * listed as unplaced and never left out, since it says the generated SPARQL wrote where the profile does not say it lands.
     */
    private static String delta(List<LandingPlaces.Place> places, LandingPlaces.Values values, Set<Quad> added, Set<Quad> removed) {
        Map<String, List<String>> add = byGraph(added);
        Map<String, List<String>> del = byGraph(removed);
        Set<String> graphs = new TreeSet<>(BYTES);
        graphs.addAll(add.keySet());
        graphs.addAll(del.keySet());
        Map<String, JsonArray> perPlace = new TreeMap<>(BYTES);
        Map<String, LandingPlaces.Place> placeOf = new HashMap<>();
        JsonArray unplaced = new JsonArray();
        for (String graph : graphs) {
            JsonObject entry = new JsonObject();
            if (graph.isEmpty()) {
                entry.put("graph", JsonNull.instance);
            } else {
                entry.put("graph", graph);
            }
            entry.put("added", strings(add.getOrDefault(graph, List.of())));
            entry.put("removed", strings(del.getOrDefault(graph, List.of())));
            List<LandingPlaces.Place> matched = LandingPlaces.assign(places, graph, values);
            if (matched.isEmpty()) {
                unplaced.add(entry);
            }
            for (LandingPlaces.Place p : matched) {
                placeOf.put(p.iri(), p);
                perPlace.computeIfAbsent(p.iri(), k -> new JsonArray()).add(entry);
            }
        }
        JsonArray placed = new JsonArray();
        perPlace.forEach((iri, entries) -> {
            JsonObject o = new JsonObject();
            o.put("place", iri);
            o.put("role", placeOf.get(iri).role());
            o.put("graphs", entries);
            placed.add(o);
        });
        JsonObject root = new JsonObject();
        root.put("places", placed);
        root.put("unplaced", unplaced);
        return JSON.toString(root);
    }

    // ---- the outcome

    /**
     * What the caller library's confirmation read says about the write (ADR-A132, STD-312). The step runs the library's read over the dataset after
     * the update, as a caller runs it on the writer, and tells its classification as it gives it. The library names the guard each classification
     * answers, and nothing here reads the store to classify. A step runs only a Create, Replace, DeltaReplace or Tombstone, and each records a
     * transaction claim, so the read always applies.
     */
    private static String confirmed(DatasetGraph ds, OperationContract contract, Map<String, Object> values) throws Failed {
        try {
            return Txn.calculateRead(ds, () -> confirm(ds, contract, values));
        } catch (ConfirmationException e) {
            throw new Failed("The write cannot be confirmed. " + e.getMessage());
        }
    }

    private static String confirm(DatasetGraph ds, OperationContract contract, Map<String, Object> values) {
        Confirmation c = Confirmation.run(query -> select(ds, query), contract, values);
        JsonObject o = new JsonObject();
        o.put("outcome", c.outcome().value());
        o.put("classification", c.classification().value());
        o.put("reason", c.reason());
        if (c.revision() != null) {
            o.put("revision", c.revision());
        }
        o.put("engine", ENGINE);
        return JSON.toString(o);
    }

    /** The adopter's client of the library, over the step's dataset, which a step reads inside its own read transaction. */
    private static List<Map<String, Object>> select(DatasetGraph ds, String query) {
        List<Map<String, Object>> rows = new ArrayList<>();
        try (QueryExecution qe = QueryExecutionFactory.create(query, DatasetFactory.wrap(ds))) {
            for (ResultSet rs = qe.execSelect(); rs.hasNext();) {
                QuerySolution s = rs.next();
                Map<String, Object> row = new HashMap<>();
                row.put("fact", s.getLiteral("fact").getString());
                RDFNode value = s.get("value");
                row.put("value", value.isLiteral() ? value.asLiteral().getLexicalForm() : value.asResource().getURI());
                rows.add(row);
            }
        }
        return rows;
    }
}
