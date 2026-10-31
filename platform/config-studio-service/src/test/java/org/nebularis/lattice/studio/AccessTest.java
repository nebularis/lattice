// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.time.Clock;
import java.time.Instant;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import org.apache.jena.query.Dataset;
import org.apache.jena.query.DatasetFactory;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.ModelFactory;
import org.apache.jena.rdf.model.Resource;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.nebularis.lattice.studio.api.ApiResponse;
import org.nebularis.lattice.studio.model.Workspace;
import org.nebularis.lattice.studio.store.Cst;
import org.nebularis.lattice.studio.store.Graphs;
import org.nebularis.lattice.studio.writes.Command;
import org.nebularis.lattice.studio.writes.Writer;
import org.apache.jena.atlas.json.JSON;
import org.apache.jena.atlas.json.JsonObject;

/** Who may read, write and manage a workspace by its mode and owner (ADR-A149 decision 9). */
class AccessTest {
    private static final String WS = Fixture.id(1);
    private static final String BASE = "/api/workspaces/" + WS;
    private static final String CONFIG = Fixture.PREFIXES
        + "ex:cfg <https://www.nebularis.org/neuro-semantic/lattice/surface#label> \"one\" .";

    @TempDir Path dir;
    Fixture f;

    @BeforeEach
    void setUp() throws IOException {
        f = new Fixture(Fixture.assetsDir(dir));
    }

    private ApiResponse as(String principal, String method, String path, String query, String body) {
        Map<String, String> headers = new HashMap<>(Map.of("content-type", Fixture.TURTLE));
        if (principal != null) {
            headers.put("x-lattice-principal", principal);
        }
        return f.send(method, path, query, headers, body == null ? new byte[0] : body.getBytes(StandardCharsets.UTF_8));
    }

    /** Workspace 1, made by the administrator {@code developer}. */
    private void developersWorkspace() {
        assertEquals(201, f.createWorkspace("Plan").status());
    }

    private void mode(String principal, String ws, String mode) {
        assertEquals(200, as(principal, "POST", "/api/workspaces/" + ws + "/access", "mode=" + mode, null).status());
    }

    @Test
    void theModelMatrixByModeAndPrincipal() {
        // owner, another principal, an administrator
        Object[][] expected = {
            {Workspace.LOCKED, new boolean[] {true, false, true}, new boolean[] {true, false, true}, new boolean[] {true, false, true}},
            {Workspace.READ_ONLY, new boolean[] {true, true, true}, new boolean[] {true, false, true}, new boolean[] {true, false, true}},
            {Workspace.SHARED, new boolean[] {true, true, true}, new boolean[] {true, true, true}, new boolean[] {true, false, true}},
        };
        for (Object[] row : expected) {
            String mode = (String) row[0];
            Workspace ws = Workspace.created(WS, "Plan", Instant.parse("2026-10-27T10:00:00Z"), null, "owner").withAccess("owner", mode);
            String[][] who = {{"owner", "false"}, {"other", "false"}, {"other", "true"}};
            for (int i = 0; i < 3; i++) {
                String p = who[i][0];
                boolean admin = Boolean.parseBoolean(who[i][1]);
                String label = mode + " as " + p + (admin ? " (admin)" : "");
                assertEquals(((boolean[]) row[1])[i], ws.readableBy(p, admin), "read, " + label);
                assertEquals(((boolean[]) row[2])[i], ws.writableBy(p, admin), "write, " + label);
                assertEquals(((boolean[]) row[3])[i], ws.managedBy(p, admin), "manage, " + label);
            }
        }
    }

    @Test
    void aWorkspaceIsOwnedByItsCreatorAndShared() {
        developersWorkspace();
        Workspace ws = Workspace.from(WS, f.store.graph(Graphs.description(WS)));
        assertEquals("developer", ws.owner());
        assertEquals(Workspace.SHARED, ws.mode());
    }

    @Test
    void readOnlyLetsAnotherPrincipalReadButNotWriteOrDelete() {
        developersWorkspace();
        mode(null, WS, "read-only");
        assertEquals(200, as("reviewer", "GET", BASE, null, null).status());
        assertEquals(200, as("reviewer", "GET", BASE + "/graphs/baseline", null, null).status());
        ApiResponse put = f.send("PUT", BASE + "/graphs/surface", null,
            Map.of("content-type", Fixture.TURTLE, "if-match", "\"0\"", "x-lattice-principal", "reviewer"), CONFIG.getBytes(StandardCharsets.UTF_8));
        assertEquals(403, put.status());
        assertEquals(403, as("reviewer", "DELETE", BASE, null, null).status());
        assertEquals(200, as("reviewer", "GET", BASE, null, null).status(), "still there");
        assertEquals(204, f.put(BASE + "/graphs/surface", "\"0\"", CONFIG).status(), "the owner still writes");
    }

    @Test
    void lockedHidesTheWorkspaceFromAnotherPrincipalButNotFromAnAdministrator() {
        developersWorkspace();
        ApiResponse job = f.post(BASE + "/jobs", "kind=validate&target=surface", CONFIG);
        assertEquals(202, job.status());
        String jobPath = job.headers().get("Location");
        mode(null, WS, "locked");
        for (String path : List.of(BASE, BASE + "/graphs/baseline", BASE + "/export", jobPath)) {
            assertEquals(404, as("reviewer", "GET", path, null, null).status(), path);
            assertEquals(200, f.get(path).status(), "developer, " + path);
        }
        String listed = new String(as("reviewer", "GET", "/api/workspaces", null, null).body(), StandardCharsets.UTF_8);
        assertFalse(listed.contains(WS));
        assertTrue(new String(f.get("/api/workspaces").body(), StandardCharsets.UTF_8).contains(WS));
        assertEquals(404, as("reviewer", "DELETE", BASE, null, null).status());
    }

    @Test
    void aWorkspaceReviewerLocksIsStillSeenByTheAdministrator() {
        ApiResponse made = as("reviewer", "POST", "/api/workspaces", null, Fixture.PREFIXES + "ex:a ex:p ex:b .");
        assertEquals(201, made.status());
        mode("reviewer", WS, "locked");
        assertEquals("reviewer", Workspace.from(WS, f.store.graph(Graphs.description(WS))).owner());
        assertEquals(200, as("reviewer", "GET", BASE, null, null).status());
        assertEquals(200, f.get(BASE).status());
        assertTrue(new String(f.get("/api/workspaces").body(), StandardCharsets.UTF_8).contains(WS));
    }

    @Test
    void aNonOwnerMayNotChangeAccessAndOnlyAnAdministratorGivesAnOwner() {
        developersWorkspace();
        assertEquals(403, as("reviewer", "POST", BASE + "/access", "mode=locked", null).status());
        assertEquals(Workspace.SHARED, Workspace.from(WS, f.store.graph(Graphs.description(WS))).mode());

        String mine = Fixture.id(2);
        assertEquals(201, as("reviewer", "POST", "/api/workspaces", null, Fixture.PREFIXES + "ex:a ex:p ex:b .").status());
        assertEquals(403, as("reviewer", "POST", "/api/workspaces/" + mine + "/access", "mode=shared&owner=developer", null).status());
        assertEquals("reviewer", Workspace.from(mine, f.store.graph(Graphs.description(mine))).owner());
        assertEquals(200, as(null, "POST", "/api/workspaces/" + mine + "/access", "mode=read-only&owner=developer", null).status());
        Workspace given = Workspace.from(mine, f.store.graph(Graphs.description(mine)));
        assertEquals("developer", given.owner());
        assertEquals(Workspace.READ_ONLY, given.mode());
    }

    @Test
    void anInvalidModeIsBadRequest() {
        developersWorkspace();
        assertEquals(400, as(null, "POST", BASE + "/access", "mode=secret", null).status());
        assertEquals(400, as(null, "POST", BASE + "/access", null, null).status());
    }

    @Test
    void aWriteWithNoPrincipalIsNotRefusedForAccess() {
        developersWorkspace();
        mode(null, WS, "locked");
        Writer writer = new Writer(f.store, Fixture.OPS, Clock.systemUTC());
        Instant at = Instant.parse("2026-10-28T09:00:00Z");
        assertEquals(200, writer.apply(Command.save(WS, "surface", 0, at, Fixture.model(CONFIG))).status(), "a save with no principal");

        ApiResponse job = f.post(BASE + "/jobs", "kind=validate&target=surface", CONFIG);
        String id = job.headers().get("Location").substring("/api/jobs/".length());
        String iri = Graphs.job(id);
        Model running = ModelFactory.createDefaultModel().add(f.store.graph(iri));
        Resource node = running.createResource(iri);
        running.removeAll(node, Cst.status, null);
        running.add(node, Cst.status, Cst.Running);
        Dataset d = DatasetFactory.create();
        d.addNamedModel(iri, running);
        assertEquals(200, writer.apply(Command.jobUpdate(WS, id, d)).status(), "a job update with no principal");
    }

    @Test
    void aSaveAsAnotherPrincipalIsRefusedAtTheWriterToo() {
        developersWorkspace();
        mode(null, WS, "read-only");
        Writer writer = new Writer(f.store, Fixture.OPS, Clock.systemUTC());
        Command save = Command.save(WS, "surface", 0, Instant.parse("2026-10-28T09:00:00Z"), Fixture.model(CONFIG));
        assertEquals(403, writer.apply(save.by("reviewer", false)).status());
        assertEquals(200, writer.apply(save.by("developer", false)).status());
    }

    @Test
    void aDescriptionWithoutModeOrOwnerReadsAsSharedAndAnOwnerlessWorkspaceCannotBeLocked() {
        Model old = Workspace.created(WS, "Plan", Instant.parse("2026-10-27T10:00:00Z"), null, "someone").toModel();
        Resource node = old.createResource(Graphs.workspace(WS));
        old.removeAll(node, Cst.mode, null);
        old.removeAll(node, Cst.owner, null);
        Workspace ws = Workspace.from(WS, old);
        assertEquals(Workspace.SHARED, ws.mode());
        assertNull(ws.owner());
        assertTrue(ws.writableBy("anyone", false));
        assertFalse(ws.managedBy("anyone", false));

        Writer writer = new Writer(f.store, Fixture.OPS, Clock.systemUTC());
        assertEquals(200, writer.apply(Command.create(WS, "Plan", Instant.parse("2026-10-27T10:00:00Z"), null,
            Fixture.model(Fixture.PREFIXES + "ex:a ex:p ex:b ."))).status());
        assertNull(Workspace.from(WS, f.store.graph(Graphs.description(WS))).owner(), "created with no principal");
        assertEquals(400, writer.apply(Command.setAccess(WS, Workspace.LOCKED, null)).status());
    }

    @Test
    void listWorkspacesOverMcpOmitsALockedWorkspaceOfAnotherPrincipal() {
        developersWorkspace();
        mode(null, WS, "locked");
        String call = "{\"jsonrpc\":\"2.0\",\"id\":7,\"method\":\"tools/call\",\"params\":{\"name\":\"list_workspaces\",\"arguments\":{}}}";
        assertFalse(mcp("reviewer", call).contains(WS));
        assertTrue(mcp(null, call).contains(WS));
    }

    private String mcp(String principal, String body) {
        Map<String, String> headers = new HashMap<>(Map.of("content-type", "application/json"));
        if (principal != null) {
            headers.put("x-lattice-principal", principal);
        }
        ApiResponse r = f.send("POST", "/mcp", null, headers, body.getBytes(StandardCharsets.UTF_8));
        assertEquals(200, r.status());
        JsonObject o = JSON.parse(new String(r.body(), StandardCharsets.UTF_8));
        return o.get("result").getAsObject().get("content").getAsArray().get(0).getAsObject().get("text").getAsString().value();
    }
}
