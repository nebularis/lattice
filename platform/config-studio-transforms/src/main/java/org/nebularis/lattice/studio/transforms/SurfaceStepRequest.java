// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.transforms;

import java.io.ByteArrayOutputStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import org.apache.jena.graph.Graph;
import org.apache.jena.graph.Node;
import org.apache.jena.graph.NodeFactory;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.ModelFactory;
import org.apache.jena.rdf.model.Property;
import org.apache.jena.rdf.model.Resource;
import org.apache.jena.rdf.model.Statement;
import org.apache.jena.riot.Lang;
import org.apache.jena.riot.RDFParser;
import org.apache.jena.riot.RiotException;
import org.apache.jena.riot.lang.LabelToNode;
import org.apache.jena.sparql.core.DatasetGraph;
import org.apache.jena.sparql.core.DatasetGraphFactory;
import org.apache.jena.sparql.core.Quad;
import org.apache.jena.vocabulary.RDF;
import org.nebularis.lattice.studio.store.Cst;
import org.nebularis.lattice.studio.store.Graphs;
import org.nebularis.lattice.studio.transforms.StepRequest.StepFormatException;

/**
 * The input of a {@code simulate} run of target {@code surface}, read from its TriG (contract, Runs, "A surface step"). The step is a
 * {@code cst:SimulationStepRequest} in the graph {@code <urn:lattice:studio:step>} that says {@code cst:forPart cst:Surface} and gives the
 * time it runs at. The edit is the quads a write added and removed, which is what a persistence step's {@code delta} part states, in the
 * graphs {@code <urn:lattice:studio:step/added>} and {@code <urn:lattice:studio:step/removed>} for the default graph and
 * {@code <urn:lattice:studio:step/added/{graph}>} and {@code <urn:lattice:studio:step/removed/{graph}>} for a named graph, whose IRI is
 * percent-encoded as {@code ENCODE_FOR_URI} does. Every other graph is the sample world as it was before the edit. A part that is missing or
 * malformed throws a {@link StepFormatException} whose message says which part, in words an author reads.
 */
record SurfaceStepRequest(Node transactionTime, Set<Quad> added, Set<Quad> removed, DatasetGraph world) {
    private static final String ADDED = StepRequest.STEP_GRAPH + "/added";
    private static final String REMOVED = StepRequest.STEP_GRAPH + "/removed";
    private static final Property FOR_PART = StepRequest.cst("forPart");
    private static final Property FOR_CLASS = StepRequest.cst("forClass");

    /** Reads {@code trig}, or throws the reason a part of it is missing or malformed. */
    static SurfaceStepRequest parse(String trig) throws StepFormatException {
        if (trig.isBlank()) {
            throw new StepFormatException("The step is empty. Send TriG with the step in the graph <" + StepRequest.STEP_GRAPH + ">.");
        }
        DatasetGraph input = DatasetGraphFactory.create();
        try {
            // A blank node keeps the label the TriG gives it, so the same text always gives the same rows.
            RDFParser.create().fromString(trig).lang(Lang.TRIG).errorHandler(QuietErrors.INSTANCE).labelToNode(LabelToNode.createUseLabelEncoded())
                .parse(input);
        } catch (RiotException e) {
            throw new StepFormatException("The sample world is not valid TriG. " + e.getMessage());
        }
        Graph stepGraph = input.getGraph(NodeFactory.createURI(StepRequest.STEP_GRAPH));
        Model step = ModelFactory.createModelForGraph(stepGraph);
        List<Resource> requests = step.listSubjectsWithProperty(RDF.type, StepRequest.REQUEST).toList();
        if (requests.isEmpty()) {
            throw new StepFormatException("The step graph <" + StepRequest.STEP_GRAPH + "> holds no cst:SimulationStepRequest, so there is no step to run.");
        }
        if (requests.size() > 1) {
            throw new StepFormatException("The step graph <" + StepRequest.STEP_GRAPH + "> holds " + requests.size() + " steps, and a run takes one.");
        }
        Resource request = requests.get(0);
        part(request);
        Node time = StepRequest.time(request);

        Set<Quad> added = new HashSet<>();
        Set<Quad> removed = new HashSet<>();
        DatasetGraph world = DatasetGraphFactory.create();
        List<StepFormatException> failures = new ArrayList<>();
        input.find().forEachRemaining(q -> {
            if (!failures.isEmpty() || (!Quad.isDefaultGraph(q.getGraph()) && q.getGraph().isURI() && q.getGraph().getURI().equals(StepRequest.STEP_GRAPH))) {
                return;
            }
            try {
                Quad edit = edit(q);
                if (edit == null) {
                    world.add(q);
                } else if (q.getGraph().getURI().startsWith(ADDED)) {
                    added.add(edit);
                } else {
                    removed.add(edit);
                }
            } catch (StepFormatException e) {
                failures.add(e);
            }
        });
        if (!failures.isEmpty()) {
            throw failures.get(0);
        }
        for (Quad q : sorted(added)) {
            if (removed.contains(q)) {
                throw new StepFormatException("The edit both adds and removes " + PersistenceStep.line(q) + " in " + where(q.getGraph()) + ". Give a change once.");
            }
        }
        return new SurfaceStepRequest(time, added, removed, world);
    }

    private static List<Quad> sorted(Set<Quad> quads) {
        return quads.stream().sorted(Comparator.comparing(q -> PersistenceStep.graphName(q.getGraph()) + " " + PersistenceStep.line(q), PersistenceStep.BYTES)).toList();
    }

    private static String where(Node graph) {
        return Quad.isDefaultGraph(graph) ? "the default graph" : "<" + graph.getURI() + ">";
    }

    /** The part the step simulates must be the surface, and a persistence step sent here is told so. */
    private static void part(Resource request) throws StepFormatException {
        List<Statement> parts = request.listProperties(FOR_PART).toList();
        if (parts.isEmpty()) {
            if (request.hasProperty(FOR_CLASS)) {
                throw new StepFormatException("The step names cst:forClass, as a persistence step does, and this run simulates the surface part. Send cst:forPart cst:Surface and the edit in the graphs <"
                    + ADDED + "> and <" + REMOVED + ">.");
            }
            throw new StepFormatException("The step does not say cst:forPart, the part it simulates. Add cst:forPart cst:Surface to the step graph.");
        }
        if (parts.size() > 1 || !parts.get(0).getObject().isURIResource()) {
            throw new StepFormatException("The step must give cst:forPart once, as an IRI.");
        }
        if (!parts.get(0).getResource().equals(Cst.Surface)) {
            throw new StepFormatException("The step is for <" + parts.get(0).getResource().getURI() + ">, and this run simulates the surface part, cst:Surface.");
        }
    }

    /**
     * The quad a reserved graph's quad edits, or null for a quad of the sample world. A graph under {@code urn:lattice:studio:step/} that is
     * not one of the four forms is reserved and malformed here.
     */
    private static Quad edit(Quad q) throws StepFormatException {
        if (Quad.isDefaultGraph(q.getGraph()) || !q.getGraph().isURI() || !q.getGraph().getURI().startsWith(StepRequest.STEP_GRAPH + "/")) {
            return null;
        }
        String name = q.getGraph().getURI();
        Node target;
        if (name.equals(ADDED) || name.equals(REMOVED)) {
            target = Quad.defaultGraphIRI;
        } else if (name.startsWith(ADDED + "/") || name.startsWith(REMOVED + "/")) {
            String graph = decode(name, name.substring((name.startsWith(ADDED + "/") ? ADDED : REMOVED).length() + 1));
            if (graph.isEmpty() || graph.indexOf(':') < 1 || graph.chars().anyMatch(c -> Character.isWhitespace(c) || c == '<' || c == '>' || c == '"')) {
                throw new StepFormatException("The graph <" + name + "> names the edited graph <" + graph + ">, which is not an IRI.");
            }
            if (graph.equals(StepRequest.STEP_GRAPH) || graph.startsWith(StepRequest.STEP_GRAPH + "/")) {
                throw new StepFormatException("The graph <" + name + "> edits a graph that is reserved for the step.");
            }
            if (graph.startsWith(Graphs.PROMOTED_PREFIX)) {
                throw new StepFormatException("The graph <" + name + "> edits the derived rows <" + graph + ">. A step edits a source, and the rows are what it maintains.");
            }
            target = NodeFactory.createURI(graph);
        } else {
            throw new StepFormatException("The graph <" + name + "> is reserved for the step and is not one a surface step reads. The edit is in <" + ADDED + "> and <" + REMOVED
                + "> and in a graph of each named from the edited graph, as <" + ADDED + "/{graph}>.");
        }
        return Quad.create(target, q.getSubject(), q.getPredicate(), q.getObject());
    }

    /** The graph an encoded name stands for, as {@code ENCODE_FOR_URI} wrote it, or throws. */
    private static String decode(String name, String encoded) throws StepFormatException {
        ByteArrayOutputStream bytes = new ByteArrayOutputStream();
        for (int i = 0; i < encoded.length(); i++) {
            char c = encoded.charAt(i);
            if (c == '%') {
                if (i + 2 >= encoded.length()) {
                    throw new StepFormatException("The graph <" + name + "> is not percent-encoded as ENCODE_FOR_URI writes it.");
                }
                int hi = Character.digit(encoded.charAt(i + 1), 16);
                int lo = Character.digit(encoded.charAt(i + 2), 16);
                if (hi < 0 || lo < 0) {
                    throw new StepFormatException("The graph <" + name + "> is not percent-encoded as ENCODE_FOR_URI writes it.");
                }
                bytes.write(hi * 16 + lo);
                i += 2;
            } else if (c < 0x80) {
                bytes.write(c);
            } else {
                byte[] utf8 = String.valueOf(c).getBytes(StandardCharsets.UTF_8);
                bytes.write(utf8, 0, utf8.length);
            }
        }
        return new String(bytes.toByteArray(), StandardCharsets.UTF_8);
    }

    /** The world as it is once the edit is applied. A removal of a quad the world lacks and an addition of one it holds change nothing. */
    DatasetGraph after() {
        DatasetGraph out = DatasetGraphFactory.create();
        world.find().forEachRemaining(out::add);
        removed.forEach(out::delete);
        added.forEach(out::add);
        return out;
    }

    /** The named graphs the edit changes, which are the sources the write keeps rows for, in the order of their UTF-8 bytes. */
    List<String> sources() {
        Set<String> out = new HashSet<>();
        for (Quad q : added) {
            if (!Quad.isDefaultGraph(q.getGraph())) {
                out.add(q.getGraph().getURI());
            }
        }
        for (Quad q : removed) {
            if (!Quad.isDefaultGraph(q.getGraph())) {
                out.add(q.getGraph().getURI());
            }
        }
        return out.stream().sorted(PersistenceStep.BYTES).toList();
    }
}
