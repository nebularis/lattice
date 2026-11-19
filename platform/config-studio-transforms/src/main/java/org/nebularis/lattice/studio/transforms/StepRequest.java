// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.transforms;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import org.apache.jena.datatypes.xsd.XSDDatatype;
import org.apache.jena.graph.Graph;
import org.apache.jena.graph.Node;
import org.apache.jena.graph.NodeFactory;
import org.apache.jena.graph.Triple;
import org.apache.jena.rdf.model.Literal;
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
import org.apache.jena.riot.lang.LabelToNode;
import org.apache.jena.sparql.core.DatasetGraph;
import org.apache.jena.sparql.core.DatasetGraphFactory;
import org.apache.jena.sparql.core.Quad;
import org.apache.jena.vocabulary.RDF;
import org.nebularis.lattice.studio.store.Cst;

/**
 * The input of a {@code simulate} run of target {@code persistence}, read from its TriG (contract, Runs, "A persistence step"). Every graph
 * of the input is the sample world, the default graph included, except the graph {@code <urn:lattice:studio:step>}, which holds one
 * {@code cst:SimulationStepRequest}, and the graphs {@code <urn:lattice:studio:step/payload>} and {@code <urn:lattice:studio:step/payload/{name}>},
 * which hold the payloads. A part that is missing or malformed throws a {@link StepFormatException} whose message says which part, in words an
 * author reads.
 */
record StepRequest(String targetClass, String deployment, String operation, Node transactionTime, Map<String, String> parameters,
                   Map<String, List<Triple>> payloads, DatasetGraph world) {
    static final String STEP_GRAPH = "urn:lattice:studio:step";
    static final String PAYLOAD_GRAPH = STEP_GRAPH + "/payload";
    private static final String PAYLOAD_PREFIX = PAYLOAD_GRAPH + "/";

    private static Property cst(String name) {
        return ResourceFactory.createProperty(Cst.NS + name);
    }

    static final Resource REQUEST = ResourceFactory.createResource(Cst.NS + "SimulationStepRequest");
    private static final Property FOR_CLASS = cst("forClass");
    private static final Property FOR_DEPLOYMENT = cst("forDeployment");
    private static final Property OPERATION = cst("operation");
    private static final Property TRANSACTION_TIME = cst("transactionTime");
    private static final Property PARAMETER = cst("parameter");
    private static final Property PARAMETER_NAME = cst("parameterName");
    private static final Property PARAMETER_VALUE = cst("parameterValue");

    /** The month of the transaction time, as a log graph names it. */
    String month() {
        return transactionTime.getLiteralLexicalForm().substring(0, 7);
    }

    /** A step whose part is missing or malformed. The message is for the author, so it names the part and never repeats the input. */
    static final class StepFormatException extends Exception {
        private static final long serialVersionUID = 1L;

        StepFormatException(String message) {
            super(message);
        }
    }

    /** Reads {@code trig}, or throws the reason a part of it is missing or malformed. */
    static StepRequest parse(String trig) throws StepFormatException {
        if (trig.isBlank()) {
            throw new StepFormatException("The step is empty. Send TriG with the step in the graph <" + STEP_GRAPH + ">.");
        }
        DatasetGraph input = DatasetGraphFactory.create();
        try {
            // A blank node keeps the label the TriG gives it, so the same text always gives the same delta.
            RDFParser.create().fromString(trig).lang(Lang.TRIG).errorHandler(QuietErrors.INSTANCE).labelToNode(LabelToNode.createUseLabelEncoded())
                .parse(input);
        } catch (RiotException e) {
            throw new StepFormatException("The sample world is not valid TriG. " + e.getMessage());
        }
        Graph stepGraph = input.getGraph(NodeFactory.createURI(STEP_GRAPH));
        Model step = ModelFactory.createModelForGraph(stepGraph);
        List<Resource> requests = step.listSubjectsWithProperty(RDF.type, REQUEST).toList();
        if (requests.isEmpty()) {
            throw new StepFormatException("The step graph <" + STEP_GRAPH + "> holds no cst:SimulationStepRequest, so there is no step to run.");
        }
        if (requests.size() > 1) {
            throw new StepFormatException("The step graph <" + STEP_GRAPH + "> holds " + requests.size() + " steps, and a run takes one.");
        }
        Resource request = requests.get(0);
        String targetClass = iri(request, FOR_CLASS, "cst:forClass, the class the compiled profile is for", true);
        String deployment = iri(request, FOR_DEPLOYMENT, "cst:forDeployment", false);
        String operation = string(request, OPERATION, "cst:operation, the name of the operation in the compiled profile");
        Node time = time(request);
        Map<String, String> parameters = parameters(request);

        Map<String, List<Triple>> payloads = new TreeMap<>();
        DatasetGraph world = DatasetGraphFactory.create();
        input.find().forEachRemaining(q -> {
            if (!Quad.isDefaultGraph(q.getGraph()) && q.getGraph().isURI() && q.getGraph().getURI().equals(STEP_GRAPH)) {
                return;
            }
            String payload = !Quad.isDefaultGraph(q.getGraph()) && q.getGraph().isURI() ? payloadKey(q.getGraph().getURI()) : null;
            if (payload != null) {
                payloads.computeIfAbsent(payload, k -> new ArrayList<>()).add(q.asTriple());
            } else {
                world.add(q);
            }
        });
        return new StepRequest(targetClass, deployment, operation, time, parameters, payloads, world);
    }

    /**
     * The key of a payload graph, "" for {@code step/payload} and the parameter's name for {@code step/payload/{name}}. Null for a graph of the
     * sample world. A graph under {@code urn:lattice:studio:step/} that is neither is reserved, and is read as the key "?" so the caller refuses it.
     */
    private static String payloadKey(String graph) {
        if (graph.equals(PAYLOAD_GRAPH)) {
            return "";
        }
        if (graph.startsWith(PAYLOAD_PREFIX) && graph.length() > PAYLOAD_PREFIX.length()) {
            return graph.substring(PAYLOAD_PREFIX.length());
        }
        if (graph.startsWith(STEP_GRAPH + "/") || graph.equals(PAYLOAD_PREFIX)) {
            return "?" + graph;
        }
        return null;
    }

    private static String iri(Resource request, Property property, String what, boolean required) throws StepFormatException {
        List<Statement> values = request.listProperties(property).toList();
        if (values.isEmpty()) {
            if (required) {
                throw new StepFormatException("The step does not say " + what + ". Add it to the step graph as an IRI.");
            }
            return null;
        }
        if (values.size() > 1 || !values.get(0).getObject().isURIResource()) {
            throw new StepFormatException("The step must give " + what + " once, as an IRI.");
        }
        return values.get(0).getResource().getURI();
    }

    private static String string(Resource request, Property property, String what) throws StepFormatException {
        List<Statement> values = request.listProperties(property).toList();
        if (values.isEmpty()) {
            throw new StepFormatException("The step does not say " + what + ". Add it to the step graph as a string.");
        }
        if (values.size() > 1 || !values.get(0).getObject().isLiteral() || !isString(values.get(0).getObject().asLiteral())
            || values.get(0).getString().isEmpty()) {
            throw new StepFormatException("The step must give " + what + " once, as a non-empty string.");
        }
        return values.get(0).getString();
    }

    private static boolean isString(Literal l) {
        return l.getDatatype() == null || l.getDatatypeURI().equals(XSDDatatype.XSDstring.getURI());
    }

    private static Node time(Resource request) throws StepFormatException {
        List<Statement> values = request.listProperties(TRANSACTION_TIME).toList();
        if (values.isEmpty()) {
            throw new StepFormatException("The step does not say cst:transactionTime, the time it runs at. Add it as an xsd:dateTime with a time zone.");
        }
        RDFNode value = values.get(0).getObject();
        String lexical = value.isLiteral() ? value.asLiteral().getLexicalForm() : "";
        boolean ok = values.size() == 1 && value.isLiteral() && XSDDatatype.XSDdateTime.getURI().equals(value.asLiteral().getDatatypeURI())
            && XSDDatatype.XSDdateTime.isValid(lexical) && lexical.matches("[0-9]{4}-[0-9]{2}-[0-9]{2}T.*(Z|[+-][0-9]{2}:[0-9]{2})");
        if (!ok) {
            throw new StepFormatException("The step must give cst:transactionTime once, as a valid xsd:dateTime with a time zone, for example 2026-03-31T23:59:58Z.");
        }
        return value.asNode();
    }

    private static Map<String, String> parameters(Resource request) throws StepFormatException {
        Map<String, String> out = new LinkedHashMap<>();
        List<Statement> nodes = request.listProperties(PARAMETER).toList();
        nodes.sort(Comparator.comparing(s -> s.getObject().toString()));
        for (Statement s : nodes) {
            if (!s.getObject().isResource()) {
                throw new StepFormatException("A cst:parameter of the step must be a node with a cst:parameterName and a cst:parameterValue.");
            }
            Resource p = s.getResource();
            String name = one(p, PARAMETER_NAME, "cst:parameterName");
            String value = one(p, PARAMETER_VALUE, "cst:parameterValue");
            if (out.put(name, value) != null) {
                throw new StepFormatException("The step states the parameter " + name + " more than once.");
            }
        }
        return out;
    }

    private static String one(Resource parameter, Property property, String what) throws StepFormatException {
        List<Statement> values = parameter.listProperties(property).toList();
        if (values.size() != 1 || !values.get(0).getObject().isLiteral() || !isString(values.get(0).getObject().asLiteral())) {
            throw new StepFormatException("Each cst:parameter of the step must have one " + what + " as a string.");
        }
        return values.get(0).getString();
    }
}
