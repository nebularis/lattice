// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import org.apache.jena.atlas.json.JSON;
import org.apache.jena.atlas.json.JsonObject;
import org.apache.jena.query.Dataset;
import org.apache.jena.query.DatasetFactory;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.ModelFactory;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.nebularis.lattice.studio.api.ApiResponse;
import org.nebularis.lattice.studio.events.BrokerAuth;
import org.nebularis.lattice.studio.events.Notifier;
import org.nebularis.lattice.studio.events.Relay;
import org.nebularis.lattice.studio.store.Cst;
import org.nebularis.lattice.studio.store.Graphs;
import org.nebularis.lattice.studio.writes.Command;
import org.nebularis.lattice.studio.writes.StudioEvents;

/** The completion events, the relay's watchers and the broker's checks (PM3, PM-Q10 to PM-Q12, PM-Q20 (d)). */
class EventsTest {
    private static final String WS = Fixture.id(1);
    private static final String AS = "x-lattice-principal";

    @TempDir Path dir;
    Fixture f;
    Notifier notifier;

    @BeforeEach
    void setUp() throws Exception {
        f = new Fixture(Fixture.assetsDir(dir.resolve("assets")));
        notifier = new Notifier(f.api::authenticate, f.api::mayRead);
        f.listener = notifier::deliver;
        f.api.events("ws://127.0.0.1:15675/ws");
        assertEquals(201, f.createWorkspace("One").status());
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

    /** A tab's events topic, recording what the relay sends it. */
    private static final class Recorded implements Notifier.Socket {
        final List<String> sent = new ArrayList<>();

        @Override
        public void send(String text) {
            sent.add(text);
        }

        JsonObject last() {
            return JSON.parse(sent.get(sent.size() - 1));
        }

        String lastType() {
            return last().get("type").getAsString().value();
        }
    }

    private static String subscribe(String subject, String principal) {
        return "{\"type\":\"subscribe\",\"subject\":\"" + subject + "\",\"headers\":{\"" + AS + "\":\"" + principal + "\"}}";
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

    // --- the relay's watchers ----------------------------------------------------------------------------------------

    @Test
    void aSubscribeFrameMustCarryItsOwnPrincipalsHeaders() {
        String job = submitJob();
        Recorded s = new Recorded();
        notifier.message("developer", "t1", s, "{\"type\":\"subscribe\",\"subject\":\"" + job + "\"}");
        assertEquals("error", s.lastType(), "a frame with no headers is refused");
        notifier.message("developer", "t1", s, subscribe(job, "reviewer"));
        assertEquals(2, s.sent.size(), "headers of another principal than the broker let in are refused");
        notifier.message("mallory", "t1", s, subscribe(job, "mallory"));
        assertEquals(3, s.sent.size(), "a principal the service does not know is refused");
        notifier.message("developer", "t1", s, "[1, 2");
        assertEquals(3, s.sent.size(), "a malformed frame is dropped");
        assertEquals(0, notifier.sessions());
        notifier.message("developer", "t1", s, subscribe(job, "developer"));
        assertEquals(3, s.sent.size(), "a subscription is not acknowledged");
        assertEquals(1, notifier.sessions());
    }

    @Test
    void anEventReachesOnlyTheTabsWatchingItsJob() {
        String job = submitJob();
        String other = submitJob();
        Recorded a = new Recorded();
        Recorded b = new Recorded();
        notifier.message("developer", "a", a, subscribe(job, "developer"));
        notifier.message("developer", "b", b, subscribe(other, "developer"));
        finish(job);
        assertEquals(job, a.last().get("subject").getAsString().value());
        assertTrue(b.sent.isEmpty(), "b heard nothing");
        notifier.message("developer", "a", a, "{\"type\":\"unsubscribe\",\"subject\":\"" + job + "\"}");
        finish(job);
        assertEquals(1, a.sent.size(), "an unsubscribed tab hears nothing more");
        notifier.message("developer", "b", b, "{\"type\":\"gone\"}");
        assertEquals(1, notifier.sessions(), "a tab gone, by its will message or its own frame, is forgotten");
    }

    @Test
    void noEventReachesAPrincipalWhoMayNotReadItsJobAtSubscriptionOrAtDelivery() {
        String job = submitJob();
        Recorded reviewer = new Recorded();
        notifier.message("reviewer", "t1", reviewer, subscribe(job, "reviewer"));
        assertTrue(reviewer.sent.isEmpty(), "a shared workspace's job may be waited for");

        Map<String, String> owner = new HashMap<>(Map.of("content-type", Fixture.TURTLE, AS, "developer"));
        assertEquals(200, f.send("POST", "/api/workspaces/" + WS + "/access", "mode=locked", owner, new byte[0]).status());
        finish(job);
        assertTrue(reviewer.sent.isEmpty(), "once locked, the job's event is checked as it is delivered and withheld");

        Recorded late = new Recorded();
        notifier.message("reviewer", "t2", late, subscribe(job, "reviewer"));
        assertEquals("error", late.lastType());
        assertTrue(late.last().get("message").getAsString().value().startsWith("no such subject"), "unreadable reads as absent");
        notifier.message("reviewer", "t2", late, subscribe("urn:lattice:studio:job:not-a-job", "reviewer"));
        assertEquals(2, late.sent.size());
    }

    @Test
    void aFrameLongerThanTheLimitIsDroppedUnread() {
        Recorded s = new Recorded();
        notifier.message("developer", "t1", s, "{\"type\":\"subscribe\",\"subject\":\"x\",\"pad\":\"" + "y".repeat(Notifier.MAX_FRAME) + "\"}");
        assertTrue(s.sent.isEmpty());
        assertEquals(0, notifier.sessions());
    }

    @Test
    void aPrincipalWatchesFromABoundedNumberOfTabs() {
        String job = submitJob();
        for (int i = 0; i < Notifier.MAX_TABS; i++) {
            notifier.message("developer", "t" + i, new Recorded(), subscribe(job, "developer"));
        }
        Recorded one = new Recorded();
        notifier.message("developer", "more", one, subscribe(job, "developer"));
        assertEquals("error", one.lastType());
        assertEquals(Notifier.MAX_TABS, notifier.sessions());
        notifier.message("reviewer", "t0", new Recorded(), subscribe(job, "reviewer"));
        assertEquals(Notifier.MAX_TABS + 1, notifier.sessions(), "another principal's tabs are counted apart");
    }

    // --- the broker's checks -----------------------------------------------------------------------------------------

    private String broker(String check, String form) {
        ApiResponse r = f.send("POST", BrokerAuth.PREFIX + check, null, Map.of("content-type", "application/x-www-form-urlencoded"),
            form.getBytes(StandardCharsets.UTF_8));
        assertEquals(200, r.status());
        return new String(r.body(), StandardCharsets.UTF_8);
    }

    private static String client(String principal, String tab) {
        return java.net.URLEncoder.encode(BrokerAuth.clientId(principal, tab), StandardCharsets.UTF_8);
    }

    @Test
    void theBrokerLetsAPrincipalInOnlyAsItselfFromAClientIdOfItsOwn() {
        assertEquals("allow", broker("user", "username=developer&password=local&client_id=" + client("developer", "t1")));
        assertEquals("deny", broker("user", "username=mallory&password=local&client_id=" + client("mallory", "t1")), "an unknown principal");
        assertEquals("deny", broker("user", "username=developer&password=local&client_id=" + client("reviewer", "t1")), "another's client id");
        assertEquals("deny", broker("user", "username=developer&password=local&client_id=studio%3Aabc"), "a client id naming no tab");
        assertEquals("deny", broker("user", "username=developer&password=local"), "no client id, as an AMQP connection has");
        assertEquals("allow", broker("vhost", "username=developer&vhost=%2F&client_id=" + client("developer", "t1")));
        assertEquals("deny", broker("vhost", "username=developer&vhost=other&client_id=" + client("developer", "t1")));
    }

    @Test
    void theBrokersPasswordIsTheBearerTokenOfTheDeploymentsAuthenticator() {
        BrokerAuth oidc = new BrokerAuth(h -> ("Bearer good".equals(h.get("authorization")) ? new org.nebularis.lattice.studio.auth.Principal("developer", false) : null));
        java.util.function.Function<String, String> user = form -> new String(oidc.handle("POST", BrokerAuth.PREFIX + "user",
            (form + "&client_id=" + client("developer", "t1")).getBytes(StandardCharsets.UTF_8)).body(), StandardCharsets.UTF_8);
        assertEquals("allow", user.apply("username=developer&password=good"));
        assertEquals("deny", user.apply("username=developer&password=bad"));
        assertEquals("deny", user.apply("username=developer&password="), "no token");
        assertEquals("deny", user.apply("username=reviewer&password=good"), "a token of another principal than the user named");
    }

    @Test
    void aPrincipalMayUseOnlyItsTabsSessionQueueAndTopics() {
        String c = client("developer", "t1");
        String id = BrokerAuth.clientId("developer", "t1");
        String own = "studio.u." + BrokerAuth.topicName("developer") + ".t1.";
        String theirs = "studio.u." + BrokerAuth.topicName("reviewer") + ".t1.";
        assertEquals("allow", broker("resource", "username=developer&resource=queue&permission=configure&client_id=" + c
            + "&name=" + java.net.URLEncoder.encode("mqtt-subscription-" + id + "qos0", StandardCharsets.UTF_8)));
        assertEquals("deny", broker("resource", "username=developer&resource=queue&permission=read&client_id=" + c + "&name=lattice.studio.jobs"));
        assertEquals("allow", broker("resource", "username=developer&resource=exchange&permission=read&client_id=" + c + "&name=amq.topic"));
        assertEquals("deny", broker("resource", "username=developer&resource=exchange&permission=read&client_id=" + c + "&name=" + StudioEvents.EXCHANGE),
            "the studio's own events are read by the relay alone");
        assertEquals("deny", broker("resource", "username=developer&resource=exchange&permission=configure&client_id=" + c + "&name=amq.topic"));
        String topic = "username=developer&resource=topic&name=amq.topic&variable_map.client_id=" + c;
        assertEquals("allow", broker("topic", topic + "&permission=read&routing_key=" + own + "events"));
        assertEquals("allow", broker("topic", topic + "&permission=write&routing_key=" + own + "watch"));
        assertEquals("deny", broker("topic", topic + "&permission=write&routing_key=" + own + "events"), "a tab cannot forge its own events");
        assertEquals("deny", broker("topic", topic + "&permission=read&routing_key=" + theirs + "events"), "another principal's events");
        assertEquals("deny", broker("topic", topic + "&permission=read&routing_key=" + own.replace(".t1.", ".t2.") + "events"), "another tab's events");
        assertEquals("deny", broker("topic", topic + "&permission=read&routing_key=studio.u.%23"), "a wildcard");
    }

    @Test
    void theBrokersChecksAreNotServedWhenTheStudioOffersNoEvents() {
        f.api.events(null);
        assertEquals(404, f.send("POST", BrokerAuth.PREFIX + "user", null, Map.of(), "username=developer".getBytes(StandardCharsets.UTF_8)).status());
    }

    @Test
    void theSessionNamesWhereEventsAreOffered() {
        String body = new String(f.get("/api/session").body(), StandardCharsets.UTF_8);
        assertTrue(body.contains("\"events\":\"ws:\\/\\/127.0.0.1:15675\\/ws\"") || body.contains("\"events\":\"ws://127.0.0.1:15675/ws\""), body);
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
        var read = Relay.read(properties, event.data().getBytes(StandardCharsets.UTF_8));
        assertEquals(event, read);
        headers.remove("cloudEvents:subject");
        var lacking = new com.rabbitmq.client.AMQP.BasicProperties.Builder().headers(headers).build();
        assertNull(Relay.read(lacking, new byte[0]), "a missing attribute drops the event");
    }

    private static Dataset jobGraph(String job) {
        Dataset d = DatasetFactory.create();
        Model m = ModelFactory.createDefaultModel();
        m.createResource(Graphs.job(job)).addProperty(Cst.status, Cst.Failed);
        d.addNamedModel(Graphs.job(job), m);
        return d;
    }
}
