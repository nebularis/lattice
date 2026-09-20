package org.nebularis.lattice.surface;

import static org.junit.jupiter.api.Assertions.assertEquals;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.Optional;
import org.junit.jupiter.api.Test;

class SurfaceRevisionApiTest {
    private static final String DIGEST = "sha256:" + "a".repeat(64);

    @Test
    void createsAndTransitionsTypedRevisionViews() {
        var api = api();
        var created = api.create(createRequest());

        assertEquals(201, created.status());
        assertEquals("draft", created.body().state());

        var transitioned = api.transition("revision-1", new SurfaceRevisionApi.TransitionRequest(0, SurfaceRevisionAction.REQUEST_REVIEW, Optional.empty(), Optional.empty()));

        assertEquals(200, transitioned.status());
        assertEquals("review_requested", transitioned.body().state());
        assertEquals(1, transitioned.body().version());
    }

    @Test
    void returnsConflictForStaleTransition() {
        var api = api();
        api.create(createRequest());
        api.transition("revision-1", new SurfaceRevisionApi.TransitionRequest(0, SurfaceRevisionAction.REQUEST_REVIEW, Optional.empty(), Optional.empty()));

        var response = api.transition("revision-1", new SurfaceRevisionApi.TransitionRequest(0, SurfaceRevisionAction.SUPERSEDE, Optional.empty(), Optional.empty()));

        assertEquals(409, response.status());
    }

    @Test
    void returnsNotFoundForMissingRevision() {
        assertEquals(404, api().get("missing").status());
    }

    private static SurfaceRevisionApi api() {
        return new SurfaceRevisionApi(new InMemorySurfaceRevisionRepository(Clock.fixed(Instant.EPOCH, ZoneOffset.UTC)));
    }

    private static SurfaceRevisionApi.CreateRevisionRequest createRequest() {
        return new SurfaceRevisionApi.CreateRevisionRequest("revision-1", "contract-1", graph("contract"), graph("profile"));
    }

    private static SurfaceRevisionApi.GraphReferenceView graph(String family) {
        return new SurfaceRevisionApi.GraphReferenceView("tenant", "project", "https://example.test/graphs/" + family, DIGEST);
    }
}