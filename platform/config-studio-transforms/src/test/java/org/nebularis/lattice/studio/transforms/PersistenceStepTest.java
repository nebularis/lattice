// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.transforms;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.nebularis.lattice.studio.transforms.StepTrig.CST;
import static org.nebularis.lattice.studio.transforms.StepTrig.EX;
import static org.nebularis.lattice.studio.transforms.StepTrig.PAT;
import static org.nebularis.lattice.studio.transforms.StepTrig.ROOT;
import static org.nebularis.lattice.studio.transforms.StepTrig.iri;
import static org.nebularis.lattice.studio.transforms.StepTrig.line;
import static org.nebularis.lattice.studio.transforms.StepTrig.typed;

import java.io.IOException;
import java.io.StringWriter;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.TreeSet;
import org.apache.jena.atlas.json.JSON;
import org.apache.jena.atlas.json.JsonArray;
import org.apache.jena.atlas.json.JsonObject;
import org.apache.jena.atlas.json.JsonValue;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.ModelFactory;
import org.apache.jena.riot.Lang;
import org.apache.jena.riot.RDFDataMgr;
import org.apache.jena.riot.RDFParser;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.nebularis.lattice.studio.store.Cst;

/**
 * One step of the persistence simulator over the facility sample (SVA-P3). The facility's profile keeps a patch log, a dataset guard and one owned
 * member, so its create, delta replace and tombstone write the data graph, the add and delete graphs of the revision, the version row, the
 * transaction claim and the log graph of the month.
 *
 * <p>What the persistence conformance suite expects of these operations is stated for other examples, and no vector of it names the facility.
 * Its tests for the same operations are {@code test_composite_lifecycle.py} HO7-T2 (a create writes the payload to the data graph, a version row
 * at seq 1 and one revision), HO7-T5 (a tombstone removes the aggregate and tombstones the row), HO7-T6 (a stale position changes nothing) and
 * {@code test_patch_log.py} H2.6d-T1, T3, T4 and T6 (the add and delete graphs of a replace, a tombstone and a create, and a lost race
 * writes nothing). Each test below states the same expectation for the facility's graphs from first principles, since those tests run on their
 * own example and engine.
 */
class PersistenceStepTest {
    private static Model job;
    private static final String META = "urn:g:meta/6";
    private static final String DATA = "urn:g:facilities";
    private static final String TXN = "urn:g:txn";

    @BeforeAll
    static void readJob() throws IOException {
        job = FacilityJob.job();
    }

    // ---- reading a result

    /** The added and removed lines of each graph the step changed, whether the profile places it or not. */
    private record Changes(List<String> added, List<String> removed) {
    }

    private static PersistenceStep.Result run(String trig) {
        return PersistenceStep.execute(job, Examples.JOB, trig, 20_000);
    }

    private static PersistenceStep.Result ran(String trig) {
        PersistenceStep.Result r = run(trig);
        assertNull(r.failure(), r.failure());
        return r;
    }

    private static PersistenceStep.Part part(PersistenceStep.Result r, String role) {
        return r.parts().stream().filter(p -> p.role().equals(role)).findFirst().orElseThrow(() -> new AssertionError("no " + role + " part in " + roles(r)));
    }

    private static List<String> roles(PersistenceStep.Result r) {
        return r.parts().stream().map(PersistenceStep.Part::role).toList();
    }

    private static JsonObject json(PersistenceStep.Result r, String role) {
        return JSON.parse(part(r, role).text());
    }

    private static List<String> strings(JsonValue array) {
        List<String> out = new ArrayList<>();
        array.getAsArray().forEach(v -> out.add(v.getAsString().value()));
        return out;
    }

    private static Map<String, Changes> changes(PersistenceStep.Result r) {
        Map<String, Changes> out = new TreeMap<>();
        JsonObject delta = json(r, "delta");
        List<JsonObject> entries = new ArrayList<>();
        delta.get("places").getAsArray().forEach(p -> p.getAsObject().get("graphs").getAsArray().forEach(g -> entries.add(g.getAsObject())));
        delta.get("unplaced").getAsArray().forEach(g -> entries.add(g.getAsObject()));
        for (JsonObject g : entries) {
            out.put(g.get("graph").getAsString().value(), new Changes(strings(g.get("added")), strings(g.get("removed"))));
        }
        return out;
    }

    /** The graph and the role of each place the delta lists, and the graphs it lists as unplaced. */
    private static Map<String, Set<String>> placed(PersistenceStep.Result r) {
        Map<String, Set<String>> out = new TreeMap<>();
        json(r, "delta").get("places").getAsArray().forEach(p -> p.getAsObject().get("graphs").getAsArray()
            .forEach(g -> out.computeIfAbsent(g.getAsObject().get("graph").getAsString().value(), k -> new TreeSet<>()).add(p.getAsObject().get("role").getAsString().value())));
        return out;
    }

    private static List<String> unplaced(PersistenceStep.Result r) {
        List<String> out = new ArrayList<>();
        json(r, "delta").get("unplaced").getAsArray().forEach(g -> out.add(g.getAsObject().get("graph").getAsString().value()));
        return out;
    }

    private static String outcome(PersistenceStep.Result r) {
        return json(r, "outcome").get("outcome").getAsString().value();
    }

    private static String classification(PersistenceStep.Result r) {
        return json(r, "outcome").get("classification").getAsString().value();
    }

    /** The sorted lines Jena's own N-Triples writer gives for Turtle text, an expectation independent of how the step writes a quad. */
    private static List<String> ntriples(String turtle) {
        Model m = ModelFactory.createDefaultModel();
        RDFParser.fromString("@prefix ex: <" + EX + "> .\n@prefix xsd: <" + StepTrig.XSD + "> .\n" + turtle, Lang.TURTLE).parse(m);
        StringWriter w = new StringWriter();
        RDFDataMgr.write(w, m, Lang.NTRIPLES);
        List<String> lines = new ArrayList<>(Arrays.asList(w.toString().split("\n")));
        lines.removeIf(String::isBlank);
        lines.sort(PersistenceStepTest::bytes);
        return lines;
    }

    private static int bytes(String a, String b) {
        return Arrays.compareUnsigned(a.getBytes(StandardCharsets.UTF_8), b.getBytes(StandardCharsets.UTF_8));
    }

    private static List<String> sorted(String... lines) {
        List<String> out = new ArrayList<>(List.of(lines));
        out.sort(PersistenceStepTest::bytes);
        return out;
    }

    private static final String DIGEST = "\"[0-9a-f]{64}\"";

    private static void assertClaim(Changes txn, String txnId, String rev) {
        assertEquals(2, txn.added().size(), txn.added().toString());
        assertTrue(txn.added().contains(line(txnId, PAT + "rev", iri(rev))), txn.added().toString());
        assertTrue(txn.added().stream().anyMatch(l -> l.matches(iri(txnId) + " " + iri(PAT + "requestDigest") + " " + DIGEST + " \\.")), txn.added().toString());
        assertEquals(List.of(), txn.removed());
    }

    // ---- the four writes

    private static final List<String> NEW_FACILITY = ntriples("""
        ex:facility-1 a ex:Facility ; ex:facilityReference "FAC-2026-001" ; ex:arrangedBy ex:branch-london ; ex:borrower ex:acme-foods ;
            ex:lender ex:lender-north ; ex:margin 3.25 ; ex:hasDrawdown ex:drawdown-1 .
        ex:drawdown-1 a ex:Drawdown ; ex:drawnUnder ex:facility-1 ; ex:drawnAmount 40000000.0 .
        """);

    private static StepTrig create() {
        StepTrig t = StepTrig.empty().operation("create-if-absent").param("root", ROOT).param("epoch", "1").param("newRev", "urn:rev:facility-1/1")
            .param("txnId", "urn:txn:facility-1-create");
        t.payload("", StepTrig.aggregate("3.25").toArray(String[]::new));
        return t;
    }

    private static StepTrig replace(long expectedSeq) {
        StepTrig t = StepTrig.stored(2).operation("cas-replace").param("root", ROOT).param("epoch", "1").param("expectedSeq", Long.toString(expectedSeq))
            .param("nextSeq", Long.toString(expectedSeq + 1)).param("newRev", "urn:rev:facility-1/" + (expectedSeq + 1)).param("txnId", "urn:txn:facility-1-margin");
        t.time = "2026-04-02T09:30:00Z";
        t.payload("", line(ROOT, EX + "margin", typed("3.5", "decimal")));
        t.payload("retractTriples", line(ROOT, EX + "margin", typed("3.25", "decimal")));
        return t;
    }

    private static StepTrig delete() {
        StepTrig t = StepTrig.stored(2).operation("tombstone-delete").param("root", ROOT).param("epoch", "1").param("expectedSeq", "2").param("nextSeq", "3")
            .param("newRev", "urn:rev:facility-1/3").param("txnId", "urn:txn:facility-1-delete").param("cause", "urn:decision:1").param("actor", "urn:actor:1");
        t.time = "2026-04-02T09:30:00Z";
        return t;
    }

    @Test
    void aCreateWritesThePayloadTheVersionRowTheClaimTheRevisionAndTheAddGraphAndNothingElse() throws IOException {
        // HO7-T2 and H2.6d-T4, for the facility's graphs.
        PersistenceStep.Result r = ran(create().text());
        assertEquals(List.of("check", "request", "delta", "outcome"), roles(r));
        Map<String, Changes> c = changes(r);
        assertEquals(new TreeSet<>(List.of(DATA, META, TXN, "urn:g:txlog/2026-03", "urn:rev:facility-1/1/add")), c.keySet());
        assertEquals(NEW_FACILITY, c.get(DATA).added());
        assertEquals(NEW_FACILITY, c.get("urn:rev:facility-1/1/add").added(), "the add graph of a create holds its payload");
        assertEquals(List.of(), c.get(DATA).removed());
        assertEquals(sorted(line(ROOT, PAT + "epoch", typed("1", "long")), line(ROOT, PAT + "seq", typed("1", "long")), line(ROOT, PAT + "head", iri("urn:rev:facility-1/1")),
            line(ROOT, "http://www.w3.org/1999/02/22-rdf-syntax-ns#type", iri(PAT + "VersionRow"))), c.get(META).added());
        assertClaim(c.get(TXN), "urn:txn:facility-1-create", "urn:rev:facility-1/1");
        String rev = "urn:rev:facility-1/1";
        assertEquals(sorted(
            line(rev, "http://www.w3.org/1999/02/22-rdf-syntax-ns#type", iri(PAT + "Revision")), line(rev, PAT + "target", iri(ROOT)),
            line(rev, PAT + "epoch", typed("1", "long")), line(rev, PAT + "seq", typed("1", "long")), line(rev, PAT + "txn", "\"urn:txn:facility-1-create\""),
            line(rev, PAT + "recordedAt", typed("2026-03-31T23:59:58Z", "dateTime")), line(rev, PAT + "asserts", iri(rev + "/add"))), c.get("urn:g:txlog/2026-03").added());
        assertEquals("applied", outcome(r));
        assertEquals("Applied", classification(r));
        assertEquals(Map.of(DATA, Set.of("DataRole"), META, Set.of("MetaRole"), TXN, Set.of("TxnRole"), "urn:g:txlog/2026-03", Set.of("LogRole"),
            "urn:rev:facility-1/1/add", Set.of("PatchRole")), placed(r));
        assertEquals(List.of(), unplaced(r));
    }

    @Test
    void aDeltaReplaceChangesOnlyTheDeltaMovesTheRowAndWritesTheAddAndDeleteGraphs() throws IOException {
        // DR1-T8 and H2.6d-T1: the data graph holds the new state, the add and delete graphs the caller's delta, the row moves and a revision chains to the one before.
        PersistenceStep.Result r = ran(replace(2).text());
        Map<String, Changes> c = changes(r);
        assertEquals(new TreeSet<>(List.of(DATA, META, TXN, "urn:g:txlog/2026-04", "urn:rev:facility-1/3/add", "urn:rev:facility-1/3/del")), c.keySet());
        assertEquals(ntriples("ex:facility-1 ex:margin 3.5 ."), c.get(DATA).added());
        assertEquals(ntriples("ex:facility-1 ex:margin 3.25 ."), c.get(DATA).removed());
        assertEquals(ntriples("ex:facility-1 ex:margin 3.5 ."), c.get("urn:rev:facility-1/3/add").added());
        assertEquals(ntriples("ex:facility-1 ex:margin 3.25 ."), c.get("urn:rev:facility-1/3/del").added());
        assertEquals(sorted(line(ROOT, PAT + "seq", typed("3", "long")), line(ROOT, PAT + "head", iri("urn:rev:facility-1/3"))), c.get(META).added());
        assertEquals(sorted(line(ROOT, PAT + "seq", typed("2", "long")), line(ROOT, PAT + "head", iri("urn:rev:facility-1/2"))), c.get(META).removed());
        assertClaim(c.get(TXN), "urn:txn:facility-1-margin", "urn:rev:facility-1/3");
        String rev = "urn:rev:facility-1/3";
        assertEquals(sorted(
            line(rev, "http://www.w3.org/1999/02/22-rdf-syntax-ns#type", iri(PAT + "Revision")), line(rev, PAT + "target", iri(ROOT)),
            line(rev, PAT + "epoch", typed("1", "long")), line(rev, PAT + "seq", typed("3", "long")), line(rev, PAT + "prevRev", iri("urn:rev:facility-1/2")),
            line(rev, PAT + "txn", "\"urn:txn:facility-1-margin\""), line(rev, PAT + "recordedAt", typed("2026-04-02T09:30:00Z", "dateTime")),
            line(rev, PAT + "asserts", iri(rev + "/add")), line(rev, PAT + "retracts", iri(rev + "/del"))), c.get("urn:g:txlog/2026-04").added());
        assertEquals("applied", outcome(r));
        assertEquals(List.of(), unplaced(r));
    }

    @Test
    void aTombstoneRemovesTheAggregateAndNotItsNeighbourMarksTheRowAndKeepsTheOldAggregateInTheDeleteGraph() throws IOException {
        // HO7-T5 and H2.6d-T3.
        PersistenceStep.Result r = ran(delete().text());
        assertEquals(List.of("check", "request", "delta", "outcome"), roles(r));
        Map<String, Changes> c = changes(r);
        assertEquals(new TreeSet<>(List.of(DATA, META, TXN, "urn:g:txlog/2026-04", "urn:rev:facility-1/3/del")), c.keySet());
        assertEquals(NEW_FACILITY, c.get(DATA).removed(), "the root and its owned member go, and facility-2 stays");
        assertEquals(List.of(), c.get(DATA).added());
        assertEquals(NEW_FACILITY, c.get("urn:rev:facility-1/3/del").added());
        assertEquals(sorted(line(ROOT, PAT + "seq", typed("3", "long")), line(ROOT, PAT + "head", iri("urn:rev:facility-1/3")),
            line(ROOT, PAT + "deleted", typed("true", "boolean"))), c.get(META).added());
        assertEquals(sorted(line(ROOT, PAT + "seq", typed("2", "long")), line(ROOT, PAT + "head", iri("urn:rev:facility-1/2"))), c.get(META).removed());
        String rev = "urn:rev:facility-1/3";
        assertEquals(sorted(
            line(rev, "http://www.w3.org/1999/02/22-rdf-syntax-ns#type", iri(PAT + "Revision")), line(rev, "http://www.w3.org/1999/02/22-rdf-syntax-ns#type", iri(PAT + "Deletion")),
            line(rev, PAT + "target", iri(ROOT)), line(rev, PAT + "epoch", typed("1", "long")), line(rev, PAT + "seq", typed("3", "long")),
            line(rev, PAT + "prevRev", iri("urn:rev:facility-1/2")), line(rev, PAT + "txn", "\"urn:txn:facility-1-delete\""),
            line(rev, PAT + "recordedAt", typed("2026-04-02T09:30:00Z", "dateTime")), line(rev, PAT + "cause", iri("urn:decision:1")),
            line(rev, PAT + "actor", iri("urn:actor:1")), line(rev, PAT + "retracts", iri(rev + "/del"))), c.get("urn:g:txlog/2026-04").added());
        assertEquals("applied", outcome(r));
        assertEquals(List.of(), unplaced(r));
    }

    @Test
    void aReplaceFromAnEarlierPositionChangesNothingAndIsClassifiedAsALostRace() throws IOException {
        // HO7-T6 and H2.6d-T6: a stale position writes nothing in any graph, the delta graphs included.
        PersistenceStep.Result r = ran(replace(1).text());
        assertEquals(List.of("check", "request", "delta", "outcome"), roles(r));
        assertEquals(Map.of(), changes(r));
        assertEquals("lostRace", outcome(r));
        assertEquals("PreconditionFailed", classification(r));
        assertTrue(json(r, "outcome").get("reason").getAsString().value().contains("position 2, not 1"), part(r, "outcome").text());
        assertEquals(PersistenceStep.ENGINE, json(r, "outcome").get("engine").getAsString().value());
    }

    @Test
    void theOtherReasonsAGuardCanFailAreEachClassified() {
        StepTrig noEpoch = replace(2);
        noEpoch.graphs.put("urn:g:dataset", List.of(line("urn:g:dataset", PAT + "epoch", typed("2", "long"))));
        assertEquals("EpochChanged", classification(ran(noEpoch.text())));

        StepTrig gone = replace(2);
        gone.graph(META, line(ROOT, PAT + "deleted", typed("true", "boolean")));
        assertEquals("Gone", classification(ran(gone.text())));

        StepTrig exists = create();
        exists.graph(META, line(ROOT, PAT + "epoch", typed("1", "long")), line(ROOT, PAT + "seq", typed("1", "long")));
        PersistenceStep.Result already = ran(exists.text());
        assertEquals("lostRace", outcome(already));
        assertEquals("AlreadyExists", classification(already));
        assertEquals(Map.of(), changes(already));

        StepTrig orphan = create();
        orphan.graph(DATA, line(ROOT, EX + "margin", typed("9.0", "decimal")));
        PersistenceStep.Result noRow = ran(orphan.text());
        assertEquals("lostRace", outcome(noRow));
        assertEquals("AlreadyExists", classification(noRow), "HO7-T4: data with no version row is not created over, which the composite create's guard on the root's triples refuses");
        assertEquals(Map.of(), changes(noRow));

        StepTrig reused = create();
        reused.graph(TXN, line("urn:txn:facility-1-create", PAT + "rev", iri("urn:rev:other")), line("urn:txn:facility-1-create", PAT + "requestDigest", "\"" + "0".repeat(64) + "\""));
        PersistenceStep.Result same = ran(reused.text());
        assertEquals("refused", outcome(same));
        assertEquals("IdempotencyKeyReuse", classification(same));
        assertEquals(Map.of(), changes(same));
    }

    @Test
    void aRetryOfAnAppliedStepIsAppliedAgainByAnEarlierAttemptAndChangesNothing() {
        PersistenceStep.Result first = ran(create().text());
        String claim = changes(first).get(TXN).added().stream().filter(l -> l.contains("requestDigest")).findFirst().orElseThrow();
        // The world a second send starts from holds what the first wrote, so the same request finds its own claim and writes nothing.
        StepTrig retry = create();
        retry.graph(TXN, line("urn:txn:facility-1-create", PAT + "rev", iri("urn:rev:facility-1/1")), claim);
        retry.graph(META, line(ROOT, PAT + "epoch", typed("1", "long")), line(ROOT, PAT + "seq", typed("1", "long")));
        PersistenceStep.Result second = ran(retry.text());
        assertEquals("applied", outcome(second));
        assertTrue(json(second, "outcome").get("reason").getAsString().value().contains("earlier attempt"));
        assertEquals(Map.of(), changes(second));
    }

    @Test
    void theMonthGraphIsTheMonthOfTheStatedTimeNotOfToday() {
        PersistenceStep.Result r = ran(create().text());
        Set<String> logs = new TreeSet<>();
        changes(r).keySet().stream().filter(g -> g.startsWith("urn:g:txlog/")).forEach(logs::add);
        assertEquals(Set.of("urn:g:txlog/2026-03"), logs);
        assertTrue(part(r, "request").text().contains("\"2026-03-31T23:59:58Z\"^^<http://www.w3.org/2001/XMLSchema#dateTime>"), part(r, "request").text());
        StepTrig later = create();
        later.time = "2031-12-31T23:59:59+02:00";
        assertEquals(Set.of("urn:g:txlog/2031-12"), changes(ran(later.text())).keySet().stream().filter(g -> g.startsWith("urn:g:txlog/")).collect(java.util.stream.Collectors.toSet()));
        assertEquals("2031-12-31T23:59:59+02:00", changes(ran(later.text())).get("urn:g:txlog/2031-12").added().stream().filter(l -> l.contains("recordedAt")).findFirst()
            .orElseThrow().replaceAll(".*\"([^\"]+)\"\\^\\^.*", "$1"), "the time is the stated one, kept as stated");
    }

    @Test
    void theRequestPartIsTheUpdateAsItRanWithTheLineSayingEachNowWasReplaced() {
        String request = part(ran(create().text()), "request").text();
        assertTrue(request.startsWith("# Each NOW() of the operation was replaced with "), request);
        assertEquals(1, request.lines().filter(l -> l.startsWith("#")).count(), "one comment line");
        assertFalse(request.lines().skip(1).anyMatch(l -> l.matches("(?i).*\\bnow\\s*\\(.*")), "no NOW() is left after the comment line");
        assertTrue(request.contains("<https://example.org/lending#facility-1>"), "the parameters are bound");
        assertTrue(request.contains("<https://example.org/lending#facilityReference> \"FAC-2026-001\""), "the slots are filled");
        assertFalse(request.contains("{{{"), request);
        assertFalse(request.contains("$root"), request);
        // The text parses again as an update, which a request that is shown as sent must.
        org.apache.jena.update.UpdateFactory.create(request);
    }

    // ---- the caller's checks

    @Test
    void aRequestTheCallerCheckRefusesEndsAtTheCheckWithARefusedOutcomeAndSendsNothing() {
        StepTrig stray = create();
        stray.payload("", line(EX + "somebody-else", EX + "margin", typed("1.0", "decimal")));
        PersistenceStep.Result r = ran(stray.text());
        assertEquals(List.of("check", "outcome"), roles(r), "no request is shown and no delta, since nothing was sent");
        assertEquals("refused", outcome(r));
        assertEquals("RefusedByCallerCheck", classification(r));
        assertNull(json(r, "outcome").get("engine"), "nothing was evaluated");
        JsonObject check = json(r, "check");
        JsonArray checks = check.get("checks").getAsArray();
        assertEquals("callerCheck", checks.get(0).getAsObject().get("name").getAsString().value());
        assertEquals("passed", checks.get(0).getAsObject().get("verdict").getAsString().value());
        assertEquals("payloadCheck", checks.get(1).getAsObject().get("name").getAsString().value());
        assertEquals("refused", checks.get(1).getAsObject().get("verdict").getAsString().value());
        assertEquals("PayloadOutsideBound", checks.get(1).getAsObject().get("reasons").getAsArray().get(0).getAsObject().get("code").getAsString().value());
    }

    @Test
    void aPassingStepShowsEachCheckWithItsVerdictAndADeltaOverlapIsRefused() {
        PersistenceStep.Result r = ran(create().text());
        JsonObject check = json(r, "check");
        assertEquals("create-if-absent", check.get("operation").getAsString().value());
        assertEquals("Create", check.get("kind").getAsString().value());
        assertEquals("passed", check.get("checks").getAsArray().get(0).getAsObject().get("verdict").getAsString().value());
        assertEquals("passed", check.get("checks").getAsArray().get(1).getAsObject().get("verdict").getAsString().value());

        PersistenceStep.Result delta = ran(replace(2).text());
        assertEquals("notRun", json(delta, "check").get("checks").getAsArray().get(1).getAsObject().get("verdict").getAsString().value());

        StepTrig overlap = replace(2);
        overlap.payload("retractTriples", line(ROOT, EX + "margin", typed("3.5", "decimal")));
        PersistenceStep.Result refused = ran(overlap.text());
        assertEquals("refused", outcome(refused));
        assertTrue(part(refused, "check").text().contains("DeltaOverlap"), part(refused, "check").text());

        StepTrig empty = replace(2);
        empty.payloads.clear();
        assertTrue(part(ran(empty.text()), "check").text().contains("EmptyDelta"));
    }

    @Test
    void aMissingParameterAnUnknownOneAndAWrongKindAreRefusedByTheCheckAndNamedBeforeAnythingIsSent() {
        StepTrig noRoot = create();
        noRoot.parameters.remove("root");
        PersistenceStep.Result missing = ran(noRoot.text());
        assertEquals("refused", outcome(missing));
        assertTrue(part(missing, "check").text().contains("MissingParameter"), part(missing, "check").text());
        assertFalse(part(missing, "check").text().contains("requestDigest"), "the digest is computed and so never missing");

        StepTrig extra = create().param("colour", "red");
        PersistenceStep.Result unknown = ran(extra.text());
        assertEquals("refused", outcome(unknown));
        assertTrue(part(unknown, "check").text().contains("UnknownParameter"), part(unknown, "check").text());
    }

    // ---- places

    @Test
    void aChangedGraphThatNoPlaceStatesIsListedAsUnplacedAndNotDropped() throws IOException {
        // The profile of this job no longer says where the log graph lands, as a compiler that missed a place would give it.
        Model withoutLog = FacilityJob.job(m -> {
            var landsIn = m.createProperty("https://www.nebularis.org/neuro-semantic/lattice/persistence#landsIn");
            for (var s : m.listStatements(null, landsIn, (org.apache.jena.rdf.model.RDFNode) null).toList()) {
                if (s.getObject().asResource().getURI().contains("place-log")) {
                    m.remove(s);
                }
            }
        });
        PersistenceStep.Result r = PersistenceStep.execute(withoutLog, Examples.JOB, create().text(), 20_000);
        assertNull(r.failure(), r.failure());
        assertEquals(List.of("urn:g:txlog/2026-03"), unplaced(r));
        assertFalse(placed(r).containsKey("urn:g:txlog/2026-03"));
        assertTrue(changes(r).containsKey("urn:g:txlog/2026-03"), "the graph is in the delta, with its quads");
        assertEquals(1, changes(r).get("urn:g:txlog/2026-03").added().stream().filter(l -> l.contains("recordedAt")).count());
    }

    @Test
    void eachPlaceCarriesItsIriFromTheCompiledProfileSoTheCanvasCanLightIt() {
        JsonArray places = json(ran(create().text()), "delta").get("places").getAsArray();
        Set<String> iris = new TreeSet<>();
        places.forEach(p -> iris.add(p.getAsObject().get("place").getAsString().value()));
        assertEquals(new TreeSet<>(List.of(
            "https://example.org/lending/Facility/compiled/profile#place-data-urn%3Ag%3Afacilities",
            "https://example.org/lending/Facility/compiled/profile#place-keys-urn%3Ag%3Akeys".replace("keys-urn%3Ag%3Akeys", "log-urn%3Ag%3Atxlog%2F%7Bmonth%7D"),
            "https://example.org/lending/Facility/compiled/profile#place-meta-urn%3Ag%3Ameta%2F6",
            "https://example.org/lending/Facility/compiled/profile#place-patch-%7BnewRev%7D%2Fadd",
            "https://example.org/lending/Facility/compiled/profile#place-txn-urn%3Ag%3Atxn")), iris);
    }

    // ---- a step that cannot be run

    private static String failure(String trig) {
        PersistenceStep.Result r = run(trig);
        assertNotNull(r.failure(), "expected a failed step, got " + roles(r));
        assertEquals(List.of(), r.parts());
        return r.failure();
    }

    private static void assertFailure(String trig, String contains) {
        String failure = failure(trig);
        assertTrue(failure.contains(contains), failure);
    }

    @Test
    void eachMissingOrMalformedPartOfTheStepIsOneFailedStepThatSaysWhichPart() {
        assertFailure("", "The step is empty");
        assertFailure("   \n", "The step is empty");
        assertFailure("GRAPH <urn:g> { not trig", "not valid TriG");
        assertFailure("<urn:g:dataset> { <urn:g:dataset> <" + PAT + "epoch> 1 . }", "holds no cst:SimulationStepRequest");
        StepTrig two = create();
        // a second request in the step graph
        String twoSteps = two.text() + "\nGRAPH <urn:lattice:studio:step> { <urn:other> a " + iri(CST + "SimulationStepRequest") + " . }";
        assertFailure(twoSteps, "holds 2 steps");

        StepTrig noClass = create();
        noClass.targetClass = null;
        assertFailure(noClass.text(), "cst:forClass");
        StepTrig noOperation = create();
        noOperation.operation = null;
        assertFailure(noOperation.text(), "cst:operation");
        StepTrig noTime = create();
        noTime.time = null;
        assertFailure(noTime.text(), "cst:transactionTime");
        StepTrig noZone = create();
        noZone.time = "2026-03-31T23:59:58";
        assertFailure(noZone.text(), "time zone");
        StepTrig badTime = create();
        badTime.time = "2026-13-45T25:00:00Z";
        assertFailure(badTime.text(), "valid xsd:dateTime");

        StepTrig twice = create();
        String s = iri("urn:lattice:studio:step");
        twice.extraStepLines.add(s + " " + iri(CST + "parameter") + " _:dup .");
        twice.extraStepLines.add("_:dup " + iri(CST + "parameterName") + " \"root\" .");
        twice.extraStepLines.add("_:dup " + iri(CST + "parameterValue") + " \"urn:other\" .");
        assertFailure(twice.text(), "states the parameter root more than once");
        StepTrig noValue = create();
        noValue.extraStepLines.add(s + " " + iri(CST + "parameter") + " _:half .");
        noValue.extraStepLines.add("_:half " + iri(CST + "parameterName") + " \"colour\" .");
        assertFailure(noValue.text(), "one cst:parameterValue");
    }

    @Test
    void theOperationTheProfileAndTheParametersAreCheckedAgainstTheCompiledProfile() {
        StepTrig unknownClass = create();
        unknownClass.targetClass = EX + "Nothing";
        assertFailure(unknownClass.text(), "no profile for the class <" + EX + "Nothing>");
        StepTrig unknownDeployment = create();
        unknownDeployment.extraStepLines.add(line("urn:lattice:studio:step", CST + "forDeployment", iri("urn:deployment:none")));
        assertFailure(unknownDeployment.text(), "the deployment <urn:deployment:none>");

        String missing = failure(create().operation("cas-swap").text());
        assertTrue(missing.contains("no operation called cas-swap") && missing.contains("create-if-absent, ") && missing.contains("tombstone-delete"), missing);
        assertFailure(create().operation("gap-scan-audit").text(), "is of kind Audit, and a step runs only a Create, Replace, DeltaReplace or Tombstone");

        assertFailure(create().param("epoch", "one").text(), "The parameter epoch must be a whole number");
        assertFailure(create().param("epoch", "99999999999999999999").text(), "outside the range of xsd:long");
        assertFailure(create().param("root", "urn:with space").text(), "not an IRI the caller library accepts");
        assertFailure(create().param("requestDigest", "0".repeat(64)).text(), "The caller library computes it from the request");
    }

    @Test
    void aPayloadGraphThatNothingReadsAndABlankNodeInAPayloadAreMalformedParts() {
        StepTrig extra = delete();
        extra.payload("", line(ROOT, EX + "margin", typed("1.0", "decimal")));
        assertFailure(extra.text(), "is not a payload graph of the operation tombstone-delete, which takes no payload");
        StepTrig wrongName = replace(2);
        wrongName.payload("assertTriples", line(ROOT, EX + "margin", typed("1.0", "decimal")));
        assertFailure(wrongName.text(), "is not a payload graph of the operation cas-replace, which reads its payloads from [<urn:lattice:studio:step/payload>, <urn:lattice:studio:step/payload/retractTriples>]");
        StepTrig reserved = create();
        reserved.graph("urn:lattice:studio:step/other", line(ROOT, EX + "margin", typed("1.0", "decimal")));
        assertFailure(reserved.text(), "<urn:lattice:studio:step/other> is not a payload graph");
        StepTrig blank = create();
        blank.payload("", "_:b " + iri(EX + "margin") + " " + typed("1.0", "decimal") + " .");
        assertFailure(blank.text(), "cannot be a payload");
    }

    @Test
    void aJobThatIsNotAFinishedPersistenceCompilationOrLacksItsArtefactsIsOneFailedStep() throws IOException {
        Model mapping = Examples.compileJob(false);
        assertTrue(PersistenceStep.execute(mapping, Examples.JOB, create().text(), 1000).failure().contains("not a finished compilation of the persistence part"));
        Model failed = FacilityJob.job();
        failed.removeAll(failed.createResource(Examples.JOB), Cst.status, null);
        failed.createResource(Examples.JOB).addProperty(Cst.status, Cst.Failed);
        assertTrue(PersistenceStep.execute(failed, Examples.JOB, create().text(), 1000).failure().contains("not a finished compilation of the persistence part"));

        Model noProfile = FacilityJob.job();
        for (var a : noProfile.listObjectsOfProperty(noProfile.createResource(Examples.JOB), Cst.artefact).toList()) {
            if ("compiled-profile.ttl".equals(a.asResource().getProperty(Cst.path).getString())) {
                noProfile.removeAll(noProfile.createResource(Examples.JOB), Cst.artefact, a);
            }
        }
        assertTrue(PersistenceStep.execute(noProfile, Examples.JOB, create().text(), 1000).failure().contains("holds no compiled profile"));

        Model broken = FacilityJob.job();
        for (var a : broken.listObjectsOfProperty(broken.createResource(Examples.JOB), Cst.artefact).toList()) {
            if ("compiled-profile.ttl".equals(a.asResource().getProperty(Cst.path).getString())) {
                broken.removeAll(a.asResource(), Cst.content, null);
                a.asResource().addProperty(Cst.content, "this is not turtle {");
            }
        }
        assertTrue(PersistenceStep.execute(broken, Examples.JOB, create().text(), 1000).failure().contains("compiled profile could not be read"));

        Model noSparql = FacilityJob.job();
        for (var a : noSparql.listObjectsOfProperty(noSparql.createResource(Examples.JOB), Cst.artefact).toList()) {
            if ("Facility/create-if-absent.rq".equals(a.asResource().getProperty(Cst.path).getString())) {
                noSparql.removeAll(noSparql.createResource(Examples.JOB), Cst.artefact, a);
            }
        }
        String reason = PersistenceStep.execute(noSparql, Examples.JOB, create().text(), 1000).failure();
        assertTrue(reason.contains("no SPARQL for the operation create-if-absent") && reason.contains("Facility/create-if-absent.rq"), reason);
    }

    // ---- determinism

    private static List<StepTrig> steps() {
        StepTrig stray = create();
        stray.payload("", line(EX + "somebody-else", EX + "margin", typed("1.0", "decimal")));
        return List.of(create(), replace(2), delete(), replace(1), stray);
    }

    @Test
    void aStepGivesTheSamePartsOnARepeatAndWhenTheQuadsOfItsInputAreInAnyOrder() {
        for (StepTrig step : steps()) {
            PersistenceStep.Result baseline = ran(step.text(0));
            assertEquals(baseline, ran(step.text(0)), "a repeat");
            for (long seed = 1; seed <= 6; seed++) {
                assertEquals(baseline, ran(step.text(seed)), step.operation + " with the input permuted by seed " + seed);
            }
        }
    }

    @Test
    void theFramesOfAStepAreTheSameOnARepeatAndAreOrderedAsTheContractSays() {
        for (StepTrig step : steps()) {
            List<JsonObject> a = RunFrames.ofStep(Examples.RUN, ran(step.text(0)));
            List<JsonObject> b = RunFrames.ofStep(Examples.RUN, ran(step.text(3)));
            assertEquals(a.stream().map(JSON::toStringFlat).toList(), b.stream().map(JSON::toStringFlat).toList());
            JsonObject last = a.get(a.size() - 1);
            assertTrue(last.get("last").getAsBoolean().value());
            assertEquals("succeeded", last.get("status").getAsString().value());
            List<String> roles = new ArrayList<>();
            a.forEach(f -> {
                if (f.hasKey("part")) {
                    roles.add(f.get("part").getAsObject().get("role").getAsString().value());
                }
            });
            assertTrue(List.of(List.of("check", "request", "delta", "outcome"), List.of("check", "outcome")).contains(roles), roles.toString());
        }
    }

    @Test
    void theSamplesOfTheContractRunAndGiveTheDeltasTheyAreDescribedAs() throws IOException {
        PersistenceStep.Result create = ran(Files.readString(FacilityJob.SAMPLES.resolve("facility-step-create.trig")));
        assertEquals("applied", outcome(create));
        assertEquals(new TreeSet<>(List.of(DATA, META, TXN, "urn:g:txlog/2026-03", "urn:rev:facility-1/1/add")), changes(create).keySet());
        PersistenceStep.Result replace = ran(Files.readString(FacilityJob.SAMPLES.resolve("facility-step-replace.trig")));
        assertEquals("applied", outcome(replace));
        assertEquals(new TreeSet<>(List.of(DATA, META, TXN, "urn:g:txlog/2026-04", "urn:rev:facility-1/3/add", "urn:rev:facility-1/3/del")), changes(replace).keySet());
        assertEquals(List.of(), unplaced(create));
        assertEquals(List.of(), unplaced(replace));
        String stale = Files.readString(FacilityJob.SAMPLES.resolve("facility-step-replace.trig")).replace("cst:parameterName \"expectedSeq\" ; cst:parameterValue \"2\"",
            "cst:parameterName \"expectedSeq\" ; cst:parameterValue \"1\"");
        assertEquals("lostRace", outcome(ran(stale)));
    }

    // ---- bounds

    @Test
    void aResultOverTheFrameBoundIsOneFailedFrameThatSaysSoAndAStepsFramesAreWithinTheBound() {
        List<String> lines = new ArrayList<>();
        for (int i = 0; i < 22_000; i++) {
            lines.add(line(ROOT, EX + "note", "\"" + "v".repeat(60) + String.format("%06d", i) + "\""));
        }
        StepTrig big = create();
        big.payloads.clear();
        big.payload("", lines.toArray(String[]::new));
        PersistenceStep.Result r = ran(big.text());
        List<JsonObject> frames = RunFrames.ofStep(Examples.RUN, r);
        assertEquals(1, frames.size());
        assertEquals("failed", frames.get(0).get("status").getAsString().value());
        assertTrue(frames.get(0).get("message").getAsString().value().contains("too large for one run"));

        List<JsonObject> small = RunFrames.ofStep(Examples.RUN, ran(create().text()));
        assertTrue(small.size() <= RunFrames.MAX_FRAMES);
        for (JsonObject f : small) {
            if (f.hasKey("text")) {
                assertTrue(f.get("text").getAsString().value().getBytes(StandardCharsets.UTF_8).length <= RunFrames.MAX_TEXT_BYTES);
            }
        }
    }

    @Test
    void aFailedStepIsOneFailedFrameAtSeqZero() {
        List<JsonObject> frames = RunFrames.ofStep(Examples.RUN, run(""));
        assertEquals(1, frames.size());
        assertEquals(0, frames.get(0).get("seq").getAsNumber().value().intValue());
        assertTrue(frames.get(0).get("last").getAsBoolean().value());
        assertEquals("failed", frames.get(0).get("status").getAsString().value());
    }

    @Test
    void anUpdateStillRunningWhenItsBudgetEndsIsStoppedAndSaysSo() {
        // Jena's update timeout stops the evaluation, so a step over a world far larger than the budget fails and holds nothing back.
        StepTrig big = delete();
        List<String> notes = new ArrayList<>();
        for (int i = 0; i < 150_000; i++) {
            notes.add(line(ROOT, EX + "note", "\"note " + i + "\""));
        }
        big.graph(DATA, notes.toArray(String[]::new));
        PersistenceStep.Result r = PersistenceStep.execute(job, Examples.JOB, big.text(), 1);
        assertEquals("The update was still running at the run's deadline, so it was stopped.", r.failure());
        assertEquals(List.of(), r.parts());
    }

    @Test
    void twoStepsNeverShareADataset() {
        // The world of a step is parsed afresh for each step, so what one step writes is not in the next one's world.
        PersistenceStep.Result first = ran(create().text());
        PersistenceStep.Result second = ran(create().text());
        assertEquals(first, second);
        assertEquals("applied", outcome(second));
    }
}
