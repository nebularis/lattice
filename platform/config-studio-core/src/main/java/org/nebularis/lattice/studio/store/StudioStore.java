// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.store;

import java.net.Authenticator;
import java.net.PasswordAuthentication;
import java.net.http.HttpClient;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import org.apache.jena.query.DatasetFactory;
import org.apache.jena.query.ParameterizedSparqlString;
import org.apache.jena.query.Query;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.ModelFactory;
import org.apache.jena.rdfconnection.RDFConnection;
import org.apache.jena.rdfconnection.RDFConnectionFuseki;
import org.apache.jena.sparql.core.Quad;
import org.apache.jena.sparql.modify.request.UpdateDrop;
import org.apache.jena.sparql.modify.request.UpdateModify;
import org.apache.jena.sparql.syntax.ElementGroup;
import org.apache.jena.update.Update;
import org.apache.jena.update.UpdateRequest;

/**
 * The studio's dataset behind Jena's {@link RDFConnection}, in memory or on Fuseki through the same code.
 * Reads are constant CONSTRUCT queries with typed bindings and writes are {@link UpdateRequest}s built
 * from the typed API, never strings (PRI-55).
 */
public final class StudioStore implements AutoCloseable {
    private static final String PREFIXES = "PREFIX cst: <" + Cst.NS + ">\n";
    private static final String GRAPH_QUERY = "CONSTRUCT { ?s ?p ?o } WHERE { GRAPH ?g { ?s ?p ?o } }";
    private static final String PROJECTION_PREFIXES = PREFIXES + "PREFIX prj: <" + Projections.NS + ">\n";
    /** The registry projection, read as the lineage graphs hold it: {@code ?lineage cst:current ?version}. */
    private static final String REGISTRY_QUERY = PROJECTION_PREFIXES
        + "CONSTRUCT { ?lineage cst:current ?version } WHERE { GRAPH ?g { ?lineage prj:current ?version } }";
    /** The summaries projection without its refresh node. */
    private static final String SUMMARIES_QUERY = "CONSTRUCT { ?s ?p ?o } WHERE { GRAPH ?g { ?s ?p ?o } FILTER (?s != ?g) }";
    private static final String HOLDERS_QUERY = PROJECTION_PREFIXES + """
        CONSTRUCT { ?w ?edge ?held } WHERE {
          GRAPH ?g {
            { ?w prj:dependsOn ?held . FILTER (?held = ?iri || STRSTARTS(STR(?held), CONCAT(STR(?iri), "/rev/"))) BIND (cst:dependsOn AS ?edge) }
            UNION
            { ?w prj:holdsImport ?held . FILTER (?held = ?iri) BIND (cst:holdsImport AS ?edge) }
          }
        }""";
    private static final String TERMS_QUERY = PROJECTION_PREFIXES + """
        SELECT ?concept ?label ?version WHERE {
          GRAPH ?g {
            ?concept prj:prefLabel ?label .
            OPTIONAL { ?concept prj:inScheme ?version }
            FILTER (CONTAINS(LCASE(STR(?label)), LCASE(?q)))
          }
        } ORDER BY ?label ?concept ?version LIMIT 50""";
    private static final String COMPILE_JOBS_QUERY = PREFIXES + """
        CONSTRUCT {
          ?job a cst:Job ; cst:kind cst:Compile ; cst:target ?target ; cst:status ?status ;
               cst:submittedAt ?submitted ; cst:startedAt ?started ; cst:finishedAt ?finished .
        } WHERE {
          GRAPH ?job {
            ?job a cst:Job ; cst:workspace ?ws ; cst:kind cst:Compile ; cst:target ?target ;
                 cst:status ?status ; cst:submittedAt ?submitted .
            OPTIONAL { ?job cst:startedAt ?started }
            OPTIONAL { ?job cst:finishedAt ?finished }
          }
        }""";

    /** The jobs projection, read as the job graphs hold it: {@code ?job cst:workspace ?ws}. */
    private static final String JOBS_OF_QUERY = PROJECTION_PREFIXES
        + "CONSTRUCT { ?job cst:workspace ?ws } WHERE { GRAPH ?g { ?job prj:workspace ?ws } }";
    /** The jobs of a workspace as their graphs hold them, which the writer deletes with it and so cannot take from a projection that lags. */
    private static final String JOB_GRAPHS_OF_QUERY = PREFIXES
        + "CONSTRUCT { ?job cst:workspace ?ws } WHERE { GRAPH ?job { ?job a cst:Job ; cst:workspace ?ws } }";
    private static final String EXPIRED_JOBS_QUERY = PREFIXES + """
        CONSTRUCT { ?job cst:workspace ?ws } WHERE {
          GRAPH ?job { ?job a cst:Job ; cst:workspace ?ws ; cst:finishedAt ?finished }
          FILTER (?finished < ?cutoff)
        }""";

    private static final String VERSION_ROW_QUERY = "PREFIX pat: <" + org.nebularis.lattice.persistence.Namespaces.PAT + ">\n"
        + "SELECT ?seq ?deleted WHERE { GRAPH ?meta { ?root pat:seq ?seq OPTIONAL { ?root pat:deleted ?deleted } } }";
    // ponytail: a scan of the meta graph for every row under a prefix, once for each workspace read. Read the rows by root if it matters.
    private static final String VERSION_ROWS_QUERY = "PREFIX pat: <" + org.nebularis.lattice.persistence.Namespaces.PAT + ">\n"
        + "SELECT ?root ?seq ?deleted WHERE { GRAPH ?meta { ?root pat:seq ?seq OPTIONAL { ?root pat:deleted ?deleted } "
        + "FILTER (STRSTARTS(STR(?root), ?prefix)) } }";
    private static final String CLAIM_QUERY = "PREFIX pat: <" + org.nebularis.lattice.persistence.Namespaces.PAT + ">\n"
        + "SELECT ?rev WHERE { GRAPH ?txn { ?claim pat:rev ?rev } }";

    private static final String RECEIPTS_QUERY = PREFIXES
        + "SELECT ?id ?revision WHERE { GRAPH ?g { ?r cst:commandId ?id OPTIONAL { ?r cst:receiptRevision ?revision } } }";

    private static final String GRAPH_NAMES_QUERY = "SELECT DISTINCT ?g WHERE { GRAPH ?g { ?s ?p ?o } }";

    private final RDFConnection connection;

    public StudioStore(RDFConnection connection) {
        this.connection = connection;
    }

    public static StudioStore inMemory() {
        return new StudioStore(RDFConnection.connect(DatasetFactory.createTxnMem()));
    }

    public static StudioStore fuseki(String url, String dataset, String user, String password) {
        String base = url.endsWith("/") ? url.substring(0, url.length() - 1) : url;
        HttpClient.Builder client = HttpClient.newBuilder();
        if (user != null && password != null) {
            client.authenticator(new Authenticator() {
                @Override
                protected PasswordAuthentication getPasswordAuthentication() {
                    return new PasswordAuthentication(user, password.toCharArray());
                }
            });
        }
        return new StudioStore(RDFConnectionFuseki.create()
            .destination(base + "/" + dataset).httpClient(client.build()).build());
    }

    /** The triples of one named graph, empty when the graph does not exist, with each skolem IRI read as a blank node. */
    public Model graph(String graphIri) {
        ParameterizedSparqlString query = new ParameterizedSparqlString(GRAPH_QUERY);
        query.setIri("g", graphIri);
        return Skolem.unskolemise(connection.queryConstruct(query.asQuery()));
    }

    /** As {@link #graph}, with each skolem IRI kept, which is how the graph is stored and what a delta is computed against. */
    public Model rawGraph(String graphIri) {
        ParameterizedSparqlString query = new ParameterizedSparqlString(GRAPH_QUERY);
        query.setIri("g", graphIri);
        return connection.queryConstruct(query.asQuery());
    }

    /** The name of every named graph that holds a triple. */
    public java.util.SortedSet<String> graphNames() {
        java.util.SortedSet<String> out = new java.util.TreeSet<>();
        connection.querySelect(constant(GRAPH_NAMES_QUERY), row -> out.add(row.getResource("g").getURI()));
        return out;
    }

    /**
     * A copy of every named graph as stored, for a backup, each read by a query, since Fuseki's update service serves no
     * read of the whole dataset. The studio writes no triple to the default graph.
     */
    public org.apache.jena.query.Dataset snapshot() {
        org.apache.jena.query.Dataset copy = DatasetFactory.create();
        for (String name : graphNames()) {
            copy.addNamedModel(name, rawGraph(name));
        }
        return copy;
    }

    /** The {@code pat:seq} of {@code root}'s version row in {@code metaGraph}, empty when it has no row or the row is tombstoned. */
    public java.util.Optional<Long> versionSeq(String metaGraph, String root) {
        ParameterizedSparqlString query = new ParameterizedSparqlString(VERSION_ROW_QUERY);
        query.setIri("meta", metaGraph);
        query.setIri("root", root);
        List<Long> out = new ArrayList<>();
        connection.querySelect(query.asQuery(), row -> {
            if (!(row.contains("deleted") && "true".equals(row.getLiteral("deleted").getLexicalForm()))) {
                out.add(row.getLiteral("seq").getLong());
            }
        });
        return out.stream().findFirst();
    }

    /** The {@code pat:seq} of every live row in {@code metaGraph} whose root starts with {@code prefix}, by root. */
    public java.util.Map<String, Long> versionRows(String metaGraph, String prefix) {
        ParameterizedSparqlString query = new ParameterizedSparqlString(VERSION_ROWS_QUERY);
        query.setIri("meta", metaGraph);
        query.setLiteral("prefix", prefix);
        java.util.Map<String, Long> out = new java.util.HashMap<>();
        connection.querySelect(query.asQuery(), row -> {
            if (!(row.contains("deleted") && "true".equals(row.getLiteral("deleted").getLexicalForm()))) {
                out.put(row.getResource("root").getURI(), row.getLiteral("seq").getLong());
            }
        });
        return out;
    }

    /** The {@code pat:rev} that transaction {@code txnId} claimed in {@code txnGraph}, empty when it has not claimed one. */
    public java.util.Optional<String> claimRev(String txnGraph, String txnId) {
        ParameterizedSparqlString query = new ParameterizedSparqlString(CLAIM_QUERY);
        query.setIri("txn", txnGraph);
        query.setIri("claim", txnId);
        List<String> out = new ArrayList<>();
        connection.querySelect(query.asQuery(), row -> out.add(row.getResource("rev").getURI()));
        return out.stream().findFirst();
    }

    /** Every published lineage with its current version (ADR-A149), read from the registry projection. */
    public Model registry() {
        return construct(REGISTRY_QUERY, "registry");
    }

    /** The summaries projection: each workspace's label, owner, mode, time and the sequence of each part and document. */
    public Model summaries() {
        return construct(SUMMARIES_QUERY, "summaries");
    }

    /** The workspaces that follow, pin or hold {@code iri}, as {@code ?w cst:dependsOn ?held} and {@code ?w cst:holdsImport ?held}. */
    public Model holders(String iri) {
        ParameterizedSparqlString query = new ParameterizedSparqlString(HOLDERS_QUERY);
        query.setIri("g", Graphs.projection("holders"));
        query.setIri("iri", iri);
        return connection.queryConstruct(query.asQuery());
    }

    /** The concepts whose label contains {@code text}, in any case, at most 50, as {@code skos:prefLabel} and {@code skos:inScheme}. */
    public Model terms(String text) {
        ParameterizedSparqlString query = new ParameterizedSparqlString(TERMS_QUERY);
        query.setIri("g", Graphs.projection("terms"));
        query.setLiteral("q", text);
        Model out = ModelFactory.createDefaultModel();
        connection.querySelect(query.asQuery(), row -> {
            var concept = out.createResource(row.getResource("concept").getURI());
            concept.addProperty(SKOS_LABEL, row.getLiteral("label"));
            if (row.contains("version")) {
                concept.addProperty(SKOS_IN_SCHEME, row.getResource("version"));
            }
        });
        return out;
    }

    private static final org.apache.jena.rdf.model.Property SKOS_LABEL =
        ModelFactory.createDefaultModel().createProperty("http://www.w3.org/2004/02/skos/core#prefLabel");
    private static final org.apache.jena.rdf.model.Property SKOS_IN_SCHEME =
        ModelFactory.createDefaultModel().createProperty("http://www.w3.org/2004/02/skos/core#inScheme");

    private Model construct(String text, String projection) {
        ParameterizedSparqlString query = new ParameterizedSparqlString(text);
        query.setIri("g", Graphs.projection(projection));
        return connection.queryConstruct(query.asQuery());
    }

    /** The compile jobs of one workspace, without their reports and artefacts: its jobs from the jobs projection, each then read from its graph. */
    public Model compileJobs(String workspaceIri) {
        Model out = ModelFactory.createDefaultModel();
        jobsOf(workspaceIri).listSubjects().forEachRemaining(job -> {
            ParameterizedSparqlString query = new ParameterizedSparqlString(COMPILE_JOBS_QUERY);
            query.setIri("ws", workspaceIri);
            query.setIri("job", job.getURI());
            out.add(connection.queryConstruct(query.asQuery()));
        });
        return out;
    }

    /** The jobs of one workspace, as {@code ?job cst:workspace ?ws}, from the jobs projection. A job just submitted may not be there yet. */
    public Model jobsOf(String workspaceIri) {
        ParameterizedSparqlString query = new ParameterizedSparqlString(JOBS_OF_QUERY);
        query.setIri("g", Graphs.projection("jobs"));
        query.setIri("ws", workspaceIri);
        return connection.queryConstruct(query.asQuery());
    }

    /** The jobs of one workspace as their graphs hold them, which are the store's own answer and never lag. */
    public Model jobGraphsOf(String workspaceIri) {
        ParameterizedSparqlString query = new ParameterizedSparqlString(JOB_GRAPHS_OF_QUERY);
        query.setIri("ws", workspaceIri);
        return connection.queryConstruct(query.asQuery());
    }

    /** The jobs that finished before {@code cutoff}, as {@code ?job cst:workspace ?ws}. */
    public Model expiredJobs(java.time.Instant cutoff) {
        ParameterizedSparqlString query = new ParameterizedSparqlString(EXPIRED_JOBS_QUERY);
        query.setLiteral("cutoff", cutoff.toString(), org.apache.jena.datatypes.xsd.XSDDatatype.XSDdateTime);
        return connection.queryConstruct(query.asQuery());
    }

    /** Applies one update request, which the store runs as one transaction. */
    public void update(UpdateRequest request) {
        connection.update(request);
    }

    /** For each command id with a receipt in the store, its receipt's revision, or 0 for a receipt without one. */
    public Map<String, Long> receipts(java.util.Collection<String> ids) {
        Map<String, Long> out = new java.util.HashMap<>();
        if (ids.isEmpty()) {
            return out;
        }
        Query query = constant(RECEIPTS_QUERY);
        org.apache.jena.sparql.core.Var id = org.apache.jena.sparql.core.Var.alloc("id");
        query.setValuesDataBlock(List.of(id), ids.stream().map(v -> org.apache.jena.sparql.engine.binding.BindingFactory
            .binding(id, org.apache.jena.graph.NodeFactory.createLiteralString(v))).toList());
        connection.querySelect(query, row -> out.put(row.getLiteral("id").getString(),
            row.contains("revision") ? row.getLiteral("revision").getLong() : 0L));
        return out;
    }

    /** Drops the graphs in {@code drops}, then replaces each graph in {@code replacements}, in one request. */
    public void write(List<String> drops, Map<String, Model> replacements) {
        UpdateRequest request = new UpdateRequest();
        for (String graph : drops) {
            request.add(drop(graph));
        }
        for (Map.Entry<String, Model> entry : replacements.entrySet()) {
            request.add(drop(entry.getKey()));
            if (!entry.getValue().isEmpty()) {
                request.add(insert(entry.getKey(), entry.getValue()));
            }
        }
        connection.update(request);
    }

    public void drop(List<String> graphs) {
        write(graphs, Map.of());
    }

    private static Query constant(String text) {
        return new ParameterizedSparqlString(text).asQuery();
    }

    /** {@code DROP SILENT GRAPH}, built from the typed API. */
    public static Update drop(String graphIri) {
        return new UpdateDrop(org.apache.jena.graph.NodeFactory.createURI(graphIri), true);
    }

    /**
     * INSERT with an empty pattern rather than INSERT DATA, which Fuseki refuses when the graph holds
     * blank nodes. The template's blank nodes are minted once, so the graph keeps its structure.
     */
    private static Update insert(String graphIri, Model model) {
        var graphNode = org.apache.jena.graph.NodeFactory.createURI(graphIri);
        UpdateModify update = new UpdateModify();
        List<Quad> quads = new ArrayList<>();
        model.getGraph().find().forEachRemaining(t -> quads.add(Quad.create(graphNode, t)));
        quads.forEach(q -> update.getInsertAcc().addQuad(q));
        update.setElement(new ElementGroup());
        return update;
    }

    public static Model emptyModel() {
        return ModelFactory.createDefaultModel();
    }

    @Override
    public void close() {
        connection.close();
    }
}
