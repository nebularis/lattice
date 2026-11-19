// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.transforms;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.regex.Pattern;
import org.apache.jena.graph.Node;
import org.apache.jena.graph.NodeFactory;
import org.apache.jena.query.Query;
import org.apache.jena.query.QueryFactory;
import org.apache.jena.query.QueryParseException;
import org.apache.jena.sparql.core.DatasetGraph;
import org.apache.jena.sparql.core.DatasetGraphFactory;
import org.apache.jena.sparql.exec.UpdateExec;
import org.apache.jena.sparql.expr.NodeValue;
import org.apache.jena.update.UpdateFactory;
import org.apache.jena.update.UpdateRequest;
import org.junit.jupiter.api.Test;

/**
 * Replacing {@code NOW()} with a step's time (SVA-P3, decided 2026-11-19, since Jena reads the clock afresh for each operation, see
 * {@code NowPinningProbeTest}). The replacement is Jena's expression and update transform over the parsed request.
 */
class NowPinningTest {
    private static final Node TIME = NodeValue.makeDateTime("2026-03-31T23:59:58Z").asNode();
    private static final Pattern NOW_CALL = Pattern.compile("(?i)\\bnow\\s*\\(");
    private static final String STAND_IN = "<urn:s> <urn:p> <urn:o> .";

    private static String filled(Path file) throws IOException {
        return Files.readString(file).replace("{{{logGraphs}}}", "<urn:g:txlog/2026-03>").replaceAll("\\{\\{\\{[A-Za-z]+\\}\\}\\}", STAND_IN);
    }

    @Test
    void noNowIsLeftInAnyOperationTheFacilitySampleCompilesAndEachWriteHadSome() throws IOException {
        List<String> writesThatHadNow = new ArrayList<>();
        int checked = 0;
        for (Path file : FacilityJob.operations()) {
            String text = filled(file);
            boolean mentionsNow = NOW_CALL.matcher(text).find();
            UpdateRequest update = null;
            Query query = null;
            try {
                update = UpdateFactory.create(text);
            } catch (QueryParseException notAnUpdate) {
                query = QueryFactory.create(text);
            }
            String name = FacilityJob.OPERATIONS.relativize(file).toString();
            if (update != null) {
                int before = NowPinning.remaining(update);
                assertEquals(mentionsNow, before > 0, name + " holds a NOW() exactly where its text does");
                NowPinning.Pinned pinned = NowPinning.pin(update, TIME);
                assertEquals(before, pinned.replaced(), name);
                assertEquals(0, NowPinning.remaining(pinned.request()), name + " has an E_Now left");
                assertFalse(NOW_CALL.matcher(pinned.request().toString()).find(), name + " still shows a NOW()");
                if (before > 0) {
                    writesThatHadNow.add(name);
                }
                // The transform is on the parsed request. The one it started from still holds its own.
                assertEquals(before, NowPinning.remaining(update), name + " was changed in place");
            } else {
                assertEquals(0, NowPinning.remaining(query), name);
            }
            checked++;
        }
        assertEquals(FacilityJob.operations().size(), checked);
        assertTrue(writesThatHadNow.containsAll(List.of("Facility/create-if-absent.rq", "Facility/cas-replace.rq", "Facility/replace-whole.rq",
            "Facility/tombstone-delete.rq")), writesThatHadNow.toString());
    }

    @Test
    void everyPlaceAnExpressionCanBeIsReachedInEveryOperationOfARequest() {
        UpdateRequest request = UpdateFactory.create("""
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            INSERT { GRAPH <urn:g:one> { <urn:s> <urn:t> ?t } } WHERE { BIND(NOW() AS ?t) FILTER(NOW() > "2000-01-01T00:00:00Z"^^xsd:dateTime) } ;
            INSERT { GRAPH ?g { <urn:s> <urn:t> ?t } } WHERE {
              BIND(IRI(CONCAT("urn:g:", SUBSTR(STR(NOW()), 1, 7))) AS ?g)
              OPTIONAL { <urn:s> <urn:u> ?u FILTER(?u < NOW()) }
              FILTER NOT EXISTS { <urn:s> <urn:v> ?v FILTER(?v > NOW()) }
              { SELECT ?t WHERE { BIND(NOW() AS ?t) } }
            } ;
            DELETE { <urn:s> <urn:t> ?old } WHERE { <urn:s> <urn:t> ?old FILTER(?old < NOW()) }
            """);
        int before = NowPinning.remaining(request);
        assertTrue(before >= 7, "the control sees " + before + " NOW()");
        NowPinning.Pinned pinned = NowPinning.pin(request, TIME);
        assertEquals(0, NowPinning.remaining(pinned.request()));
        assertFalse(NOW_CALL.matcher(pinned.request().toString()).find(), pinned.request().toString());
        assertEquals(3, pinned.request().getOperations().size());
    }

    @Test
    void everyOperationOfOneRequestReadsTheStatedTimeAndTheMonthGraphIsTheStatedMonth() {
        UpdateRequest request = UpdateFactory.create("""
            INSERT { GRAPH <urn:g:one> { <urn:s> <urn:now> ?t } } WHERE { BIND(NOW() AS ?t) } ;
            INSERT { GRAPH ?g { <urn:s> <urn:now> ?t } } WHERE { BIND(NOW() AS ?t) BIND(IRI(CONCAT("urn:g:txlog/", SUBSTR(STR(NOW()),1,7))) AS ?g) } ;
            INSERT { GRAPH <urn:g:three> { <urn:s> <urn:now> ?t } } WHERE { BIND(NOW() AS ?t) }
            """);
        DatasetGraph ds = DatasetGraphFactory.createTxnMem();
        UpdateExec.dataset(ds).update(NowPinning.pin(request, TIME).request()).build().execute();
        List<String> times = new ArrayList<>();
        ds.find(Node.ANY, Node.ANY, NodeFactory.createURI("urn:now"), Node.ANY).forEachRemaining(q -> times.add(q.getObject().getLiteralLexicalForm()));
        assertEquals(List.of("2026-03-31T23:59:58Z", "2026-03-31T23:59:58Z", "2026-03-31T23:59:58Z"), times);
        List<String> graphs = new ArrayList<>();
        ds.listGraphNodes().forEachRemaining(g -> graphs.add(g.getURI()));
        assertTrue(graphs.contains("urn:g:txlog/2026-03"), graphs.toString());
        assertEquals(1, graphs.stream().filter(g -> g.startsWith("urn:g:txlog/")).count(), graphs.toString());
    }
}
