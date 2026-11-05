// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.sparql;

import java.io.BufferedReader;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.PrintStream;
import java.io.FileDescriptor;
import java.io.FileOutputStream;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Map;

import org.apache.jena.atlas.json.JSON;
import org.apache.jena.atlas.json.JsonObject;
import org.apache.jena.query.Dataset;
import org.apache.jena.query.DatasetFactory;
import org.apache.jena.query.Query;
import org.apache.jena.query.QueryExecution;
import org.apache.jena.query.QueryFactory;
import org.apache.jena.query.ResultSet;
import org.apache.jena.query.ResultSetFormatter;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.riot.Lang;
import org.apache.jena.riot.RDFDataMgr;
import org.apache.jena.riot.RDFFormat;
import org.apache.jena.riot.RDFParser;
import org.apache.jena.riot.lang.LabelToNode;
import org.apache.jena.sparql.core.DatasetGraph;
import org.apache.jena.system.Txn;
import org.apache.jena.update.UpdateAction;
import org.apache.jena.update.UpdateFactory;
import org.apache.jena.update.UpdateRequest;

/**
 * Test-only Apache Jena ARQ, for tests that run SPARQL on a third engine (ADR-A125, with ADR-A83's
 * pattern). {@code serve} holds in-memory datasets and answers one JSON request per line on standard
 * input with one JSON line on standard output. A request that fails answers {@code {"error": "..."}} and
 * does not end the server, which ends when standard input does.
 *
 * <pre>
 * {"op": "load", "format": "nquads" | "trig", "data": "..."}   -> {"result": "ok"}
 * {"op": "query", "text": "..."}   -> {"form": "select" | "ask", "result": SPARQL 1.1 JSON results}
 *                                     {"form": "graph", "result": "N-Triples text"} for CONSTRUCT and DESCRIBE
 * {"op": "update", "text": "..."}  -> {"result": "ok"}
 * {"op": "reset"}                  -> {"result": "ok"}
 * {"op": "drop"}                   -> {"result": "ok"}, forgets the dataset
 * </pre>
 *
 * Every request may name a {@code "dataset"}, created empty on first use, so that several callers in one
 * process each have their own. Without one the request is for the dataset {@code "default"}.
 *
 * The dataset is Jena's transactional in-memory one. Each load and each update request runs in one write
 * transaction, so a request that fails leaves the dataset as it was. A query runs in a read transaction.
 * The default graph is the dataset's own default graph, not the union of the named graphs.
 */
public final class SparqlTestkit {
    /** One in-memory dataset and the same dataset as a graph, which the API wants in different places. */
    private record Store(Dataset dataset, DatasetGraph dsg) {}

    private final Map<String, Store> stores = new HashMap<>();

    private Store store(String name) {
        return stores.computeIfAbsent(name, n -> {
            Dataset dataset = DatasetFactory.createTxnMem();
            return new Store(dataset, dataset.asDatasetGraph());
        });
    }

    public void load(String name, String format, String data) {
        DatasetGraph dsg = store(name).dsg();
        Lang lang = switch (format) {
            case "nquads" -> Lang.NQUADS;
            case "trig" -> Lang.TRIG;
            default -> throw new IllegalArgumentException("unknown format " + format + ", expected nquads or trig");
        };
        Txn.executeWrite(dsg, () -> RDFParser.create().fromString(data).lang(lang).labelToNode(LabelToNode.createUseLabelEncoded()).parse(dsg));
    }

    public void update(String name, String text) {
        DatasetGraph dsg = store(name).dsg();
        UpdateRequest request = UpdateFactory.create(text);
        Txn.executeWrite(dsg, () -> UpdateAction.execute(request, dsg));
    }

    public void reset(String name) {
        DatasetGraph dsg = store(name).dsg();
        Txn.executeWrite(dsg, dsg::clear);
    }

    /** The form of the answer and the JSON text of its result. */
    public String[] query(String name, String text) {
        Store store = store(name);
        DatasetGraph dsg = store.dsg();
        Dataset dataset = store.dataset();
        Query query = QueryFactory.create(text);
        return Txn.calculateRead(dsg, () -> {
            try (QueryExecution exec = QueryExecution.create().query(query).dataset(dataset).build()) {
                ByteArrayOutputStream out = new ByteArrayOutputStream();
                if (query.isSelectType()) {
                    ResultSet rs = exec.execSelect();
                    ResultSetFormatter.outputAsJSON(out, rs);
                    return new String[] {"select", flat(out.toString(StandardCharsets.UTF_8))};
                }
                if (query.isAskType()) {
                    ResultSetFormatter.outputAsJSON(out, exec.execAsk());
                    return new String[] {"ask", flat(out.toString(StandardCharsets.UTF_8))};
                }
                Model model = query.isConstructType() ? exec.execConstruct() : exec.execDescribe();
                RDFDataMgr.write(out, model, RDFFormat.NTRIPLES_UTF8);
                return new String[] {"graph", jsonString(out.toString(StandardCharsets.UTF_8))};
            }
        });
    }

    private static String flat(String json) {
        return JSON.toStringFlat(JSON.parse(json));
    }

    static String jsonString(String text) {
        StringBuilder out = new StringBuilder("\"");
        for (char c : text.toCharArray()) {
            switch (c) {
                case '"' -> out.append("\\\"");
                case '\\' -> out.append("\\\\");
                case '\n' -> out.append("\\n");
                case '\r' -> out.append("\\r");
                case '\t' -> out.append("\\t");
                default -> {
                    if (c < 0x20) {
                        out.append(String.format("\\u%04x", (int) c));
                    } else {
                        out.append(c);
                    }
                }
            }
        }
        return out.append('"').toString();
    }

    /** The one-line answer to one request line. */
    String answer(String line) {
        try {
            JsonObject request = JSON.parse(line);
            if (!request.hasKey("op")) {
                throw new IllegalArgumentException("a request needs an op");
            }
            String op = request.get("op").getAsString().value();
            String name = request.hasKey("dataset") ? request.get("dataset").getAsString().value() : "default";
            switch (op) {
                case "load" -> {
                    load(name, request.get("format").getAsString().value(), request.get("data").getAsString().value());
                    return "{\"result\": \"ok\"}";
                }
                case "update" -> {
                    update(name, request.get("text").getAsString().value());
                    return "{\"result\": \"ok\"}";
                }
                case "reset" -> {
                    reset(name);
                    return "{\"result\": \"ok\"}";
                }
                case "query" -> {
                    String[] answer = query(name, request.get("text").getAsString().value());
                    return "{\"form\": \"" + answer[0] + "\", \"result\": " + answer[1] + "}";
                }
                case "drop" -> {
                    stores.remove(name);
                    return "{\"result\": \"ok\"}";
                }
                default -> throw new IllegalArgumentException("unknown op " + op);
            }
        } catch (Exception | StackOverflowError failure) {
            String message = failure.getMessage() == null ? failure.getClass().getName() : failure.getMessage();
            return "{\"error\": " + jsonString(failure.getClass().getSimpleName() + ": " + message) + "}";
        }
    }

    /** Answers each line of {@code in} on {@code out} until {@code in} ends. */
    void serve(BufferedReader in, PrintStream out) throws IOException {
        String line;
        while ((line = in.readLine()) != null) {
            if (line.isBlank()) {
                continue;
            }
            // One line is one answer, in every host's reading, never println's platform separator.
            out.print(answer(line));
            out.print('\n');
            out.flush();
        }
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 1 || !args[0].equals("serve")) {
            System.err.println("usage: sparql-testkit serve");
            System.exit(2);
        }
        // The protocol owns standard output, so a library that prints cannot corrupt an answer.
        PrintStream protocol = new PrintStream(new FileOutputStream(FileDescriptor.out), false, StandardCharsets.UTF_8);
        System.setOut(System.err);
        new SparqlTestkit().serve(new BufferedReader(new InputStreamReader(System.in, StandardCharsets.UTF_8)), protocol);
    }
}
