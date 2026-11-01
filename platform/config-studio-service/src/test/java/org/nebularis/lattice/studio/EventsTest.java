// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.WebSocket;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.CompletionStage;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.TimeUnit;
import org.apache.jena.atlas.json.JSON;
import org.apache.jena.atlas.json.JsonObject;
import org.apache.jena.query.Dataset;
import org.apache.jena.query.DatasetFactory;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.ModelFactory;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.nebularis.lattice.studio.api.ApiResponse;
import org.nebularis.lattice.studio.events.Notifier;
import org.nebularis.lattice.studio.http.StudioHttpServer;
import org.nebularis.lattice.studio.store.Cst;
import org.nebularis.lattice.studio.store.Graphs;
import org.nebularis.lattice.studio.writes.Command;
import org.nebularis.lattice.studio.writes.StudioEvents;

/** The completion events and the WebSocket notifier (PM3, PM-Q10 to PM-Q12). */
class EventsTest {
    private static final String WS = Fixture.id(1);
    private static final String AS = "x-lattice-principal";

    @TempDir Path dir;
    Fixture f;
    Notifier notifier;
    StudioHttpServer server;

    @BeforeEach
    void setUp() throws Exception {
        f = new Fixture(Fixture.assetsDir(dir.resolve("assets")));
        notifier = new Notifier(f.api::authenticate, f.api::mayRead);
        f.listener = notifier::deliver;
        server = new StudioHttpServer(f.api, "127.0.0.1", 0, null, notifier);
        server.start();
        assertEquals(201, f.createWorkspace("One").status());
    }

    @AfterEach
    void tearDown() {
        server.close();
    }

    private String submitJob() {
        ApiResponse r = f.post("/api/workspaces/" + WS + "/jobs", "kind=validate&target=vocabulary", Fixture.PREFIXES + "ex:a ex:p ex:b .");
        assertEquals(202, r.status());
        return Graphs.job(r.headers().get("Location").substring("/api/jobs/".length()));
    }

    /** The job's update to Succeeded, as the worker sends it. */
    private void finish(String jobIri) {
        Model m = ModelFactory.createDefaultModel().add(f.store.graph(jobIri));
        m.removeAll(m.createResource(jobIri), Cst.status, null);
        m.createResource(jobIri).addProperty(Cst.status, Cst.Succeeded);
        Dataset d = DatasetFactory.create();
        d.addNamedModel(jobIri, m);
        assertEquals(200, f.writes.send(Command.jobUpdate(WS, jobIri.substring(Graphs.job("").length()), d)).status());
    }

    /** A socket that records what the notifier sends it. */
    private static final class Recorded implements Notifier.Socket {
        final List<String> sent = new ArrayList<>();
        Integer closed;

        @Override
        public void send(String text) {
            sent.add(text);
        }

        @Override
        public void close(int code, String reason) {
            closed = code;
        }

        JsonObject last() {
            return JSON.parse(sent.get(sent.size() - 1));
        }
    }

    private static String auth(String principal) {
        return "{\"type\":\"auth\",\"headers\":{\"" + AS + "\":\"" + principal + "\"}}";
    }

    private static String subscribe(String subject) {
        return "{\"type\":\"subscribe\",\"subject\":\"" + subject + "\"}";
    }

    // --- the event ---------------------------------------------------------------------------------------------------

    @Test
    void anAppliedJobUpdateIsOneEventNamingTheJobWithItsStatusAndWorkspaceAndNoContent() {
        String job = submitJob();
        int before = f.events.size();
        finish(job);
        assertEquals(before + 1, f.events.size(), "one event for the update, none for the submission");
        var event = f.events.get(f.events.size() - 1);
        assertEquals(StudioEvents.JOB_UPDATED, event.type());
        assertEquals(job, event.subject());
        assertEquals("{\"status\":\"Succeeded\",\"workspace\":\"" + WS + "\"}", event.data());
        String json = Notifier.json(event);
        assertTrue(json.length() < 512, "an event is a few hundred bytes, 414 here: " + json.length());
        JsonObject parsed = JSON.parse(json);
        assertEquals("1.0", parsed.get("specversion").getAsString().value());
        assertEquals("Succeeded", parsed.get("data").getAsObject().get("status").getAsString().value());
    }

    @Test
    void aRefusedJobUpdatePublishesNothing() {
        String job = submitJob();
        int before = f.events.size();
        Dataset d = DatasetFactory.create();
        d.addNamedModel(job, ModelFactory.createDefaultModel());
        d.addNamedModel("urn:other", ModelFactory.createDefaultModel().add(
            ModelFactory.createDefaultModel().createResource("urn:a"), Cst.status, Cst.Succeeded));
        assertEquals(400, f.writes.send(Command.jobUpdate(WS, job.substring(Graphs.job("").length()), d)).status());
        assertEquals(before, f.events.size());
    }

    // --- the notifier ------------------------------------------------------------------------------------------------

    @Test
    void aSessionAuthenticatesFirstAndAnyOtherFirstFrameClosesIt() {
        Recorded s = new Recorded();
        notifier.opened(s);
        notifier.message(s, subscribe(submitJob()));
        assertEquals(Notifier.POLICY, s.closed);
        assertEquals(0, notifier.sessions());

        Recorded unknown = new Recorded();
        notifier.opened(unknown);
        notifier.message(unknown, auth("mallory"));
        assertEquals(Notifier.POLICY, unknown.closed, "a principal the service does not know is refused");

        Recorded junk = new Recorded();
        notifier.opened(junk);
        notifier.message(junk, "[1, 2");
        assertEquals(Notifier.POLICY, junk.closed);

        Recorded ok = new Recorded();
        notifier.opened(ok);
        notifier.message(ok, auth("reviewer"));
        assertNull(ok.closed);
        assertEquals("ready", ok.last().get("type").getAsString().value());
    }

    @Test
    void anEventReachesOnlyTheSessionsSubscribedToItsJob() {
        String job = submitJob();
        String other = submitJob();
        Recorded a = new Recorded();
        Recorded b = new Recorded();
        for (Recorded s : List.of(a, b)) {
            notifier.opened(s);
            notifier.message(s, auth("developer"));
        }
        notifier.message(a, subscribe(job));
        notifier.message(b, subscribe(other));
        finish(job);
        assertEquals(job, a.last().get("subject").getAsString().value());
        assertEquals(2, b.sent.size(), "b heard only its ready and subscribed frames");
        notifier.message(a, "{\"type\":\"unsubscribe\",\"subject\":\"" + job + "\"}");
        finish(job);
        assertEquals(3, a.sent.size(), "an unsubscribed session hears nothing more");
    }

    @Test
    void noEventReachesAPrincipalWhoMayNotReadItsJobAtSubscriptionOrAtDelivery() {
        String job = submitJob();
        Recorded reviewer = new Recorded();
        notifier.opened(reviewer);
        notifier.message(reviewer, auth("reviewer"));
        notifier.message(reviewer, subscribe(job));
        assertEquals("subscribed", reviewer.last().get("type").getAsString().value(), "a shared workspace's job may be waited for");

        Map<String, String> owner = new HashMap<>(Map.of("content-type", Fixture.TURTLE, AS, "developer"));
        assertEquals(200, f.send("POST", "/api/workspaces/" + WS + "/access", "mode=locked", owner, new byte[0]).status());
        finish(job);
        assertEquals("subscribed", reviewer.last().get("type").getAsString().value(), "once locked, the job's event is checked as it is delivered and withheld");

        Recorded late = new Recorded();
        notifier.opened(late);
        notifier.message(late, auth("reviewer"));
        notifier.message(late, subscribe(job));
        assertEquals("error", late.last().get("type").getAsString().value());
        assertTrue(late.last().get("message").getAsString().value().startsWith("no such subject"), "unreadable reads as absent");
        notifier.message(late, subscribe("urn:lattice:studio:job:not-a-job"));
        assertEquals("error", late.last().get("type").getAsString().value());
    }

    @Test
    void aFrameLongerThanTheLimitIsRefusedUnread() {
        Recorded s = new Recorded();
        notifier.opened(s);
        notifier.message(s, auth("developer"));
        notifier.message(s, "{\"type\":\"subscribe\",\"subject\":\"x\",\"pad\":\"" + "y".repeat(Notifier.MAX_FRAME) + "\"}");
        assertEquals(Notifier.POLICY, s.closed);
    }

    // --- the WebSocket -----------------------------------------------------------------------------------------------

    private static final class Received implements WebSocket.Listener {
        final BlockingQueue<String> frames = new LinkedBlockingQueue<>();
        private final StringBuilder part = new StringBuilder();

        @Override
        public CompletionStage<?> onText(WebSocket ws, CharSequence data, boolean last) {
            part.append(data);
            if (last) {
                frames.add(part.toString());
                part.setLength(0);
            }
            ws.request(1);
            return null;
        }
    }

    private WebSocket open(Received listener, String origin) throws Exception {
        WebSocket.Builder b = HttpClient.newHttpClient().newWebSocketBuilder();
        if (origin != null) {
            b.header("Origin", origin);
        }
        return b.buildAsync(URI.create("ws://127.0.0.1:" + server.port() + StudioHttpServer.EVENTS), listener).get(10, TimeUnit.SECONDS);
    }

    @Test
    void aBrowserWaitingOnTheSocketHearsItsJobFinishWithNoPoll() throws Exception {
        String job = submitJob();
        Received heard = new Received();
        WebSocket ws = open(heard, "http://127.0.0.1:" + server.port());
        ws.sendText(auth("developer"), true).get(5, TimeUnit.SECONDS);
        assertEquals("ready", JSON.parse(heard.frames.poll(5, TimeUnit.SECONDS)).get("type").getAsString().value());
        ws.sendText(subscribe(job), true).get(5, TimeUnit.SECONDS);
        assertEquals("subscribed", JSON.parse(heard.frames.poll(5, TimeUnit.SECONDS)).get("type").getAsString().value());
        finish(job);
        String frame = heard.frames.poll(5, TimeUnit.SECONDS);
        assertTrue(frame != null, "the event arrived");
        JsonObject event = JSON.parse(frame);
        assertEquals(StudioEvents.JOB_UPDATED, event.get("type").getAsString().value());
        assertEquals(job, event.get("subject").getAsString().value());
        ws.sendClose(WebSocket.NORMAL_CLOSURE, "done").get(5, TimeUnit.SECONDS);
    }

    @Test
    void aSocketOpenedFromAnotherSiteIsRefused() {
        Received heard = new Received();
        assertThrows(Exception.class, () -> open(heard, "https://elsewhere.example"));
        assertFalse(heard.frames.iterator().hasNext());
    }

    @Test
    void theEventsOfTheBrokerAreReadBackFromTheirHeaders() {
        var event = StudioEvents.of(Command.jobUpdate(WS, Fixture.id(9), jobGraph(Fixture.id(9))), java.time.Instant.parse("2026-11-01T10:00:00Z"));
        Map<String, Object> headers = new HashMap<>();
        headers.put("cloudEvents:id", event.id().toString());
        headers.put("cloudEvents:source", event.source().toString());
        headers.put("cloudEvents:type", event.type());
        headers.put("cloudEvents:subject", event.subject());
        headers.put("cloudEvents:time", event.time().toString());
        var properties = new com.rabbitmq.client.AMQP.BasicProperties.Builder().headers(headers).build();
        var read = org.nebularis.lattice.studio.events.EventConsumer.read(properties, event.data().getBytes(StandardCharsets.UTF_8));
        assertEquals(event, read);
        headers.remove("cloudEvents:subject");
        var lacking = new com.rabbitmq.client.AMQP.BasicProperties.Builder().headers(headers).build();
        assertNull(org.nebularis.lattice.studio.events.EventConsumer.read(lacking, new byte[0]), "a missing attribute drops the event");
    }

    private static Dataset jobGraph(String job) {
        Dataset d = DatasetFactory.create();
        Model m = ModelFactory.createDefaultModel();
        m.createResource(Graphs.job(job)).addProperty(Cst.status, Cst.Failed);
        d.addNamedModel(Graphs.job(job), m);
        return d;
    }
}
