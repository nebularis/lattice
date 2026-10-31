// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertInstanceOf;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.nimbusds.jose.JOSEException;
import com.nimbusds.jose.JWSAlgorithm;
import com.nimbusds.jose.JWSHeader;
import com.nimbusds.jose.crypto.MACSigner;
import com.nimbusds.jose.crypto.RSASSASigner;
import com.nimbusds.jose.jwk.RSAKey;
import com.nimbusds.jose.jwk.JWKSet;
import com.nimbusds.jose.jwk.gen.RSAKeyGenerator;
import com.nimbusds.jose.jwk.source.ImmutableJWKSet;
import com.nimbusds.jose.util.JSONObjectUtils;
import com.nimbusds.jwt.JWTClaimsSet;
import com.nimbusds.jwt.PlainJWT;
import com.nimbusds.jwt.SignedJWT;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.text.ParseException;
import java.util.Date;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicLong;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.Resource;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.nebularis.lattice.studio.api.ApiRequest;
import org.nebularis.lattice.studio.api.ApiResponse;
import org.nebularis.lattice.studio.api.StudioApi;
import org.nebularis.lattice.studio.auth.Authenticator;
import org.nebularis.lattice.studio.auth.LocalAuthenticator;
import org.nebularis.lattice.studio.auth.OidcAuthenticator;
import org.nebularis.lattice.studio.store.Cst;
import org.nebularis.lattice.studio.store.Graphs;

/** Who a request is (ADR-A149 decision 8), under the local and OpenID Connect authenticators, and that a write records them. */
class AuthTest {
    private static final String ISSUER = "https://idp.example.org";
    private static final String AUDIENCE = "studio";
    private static final String ADMIN = "studio-admins";
    private static final String WS = Fixture.id(1);
    private static final String LATTICE = "https://www.nebularis.org/neuro-semantic/lattice/";
    private static RSAKey key;
    private static RSAKey otherKey;

    @TempDir Path dir;

    @BeforeAll
    static void keys() throws JOSEException {
        key = new RSAKeyGenerator(2048).keyID("k1").generate();
        otherKey = new RSAKeyGenerator(2048).keyID("k1").generate();
    }

    private static OidcAuthenticator oidc(String audienceClaim) {
        return new OidcAuthenticator(ISSUER, AUDIENCE, audienceClaim, new ImmutableJWKSet<>(new JWKSet(key.toPublicJWK())),
            "sub", "groups", ADMIN, Map.of());
    }

    private static JWTClaimsSet.Builder claims() {
        return new JWTClaimsSet.Builder().issuer(ISSUER).audience(AUDIENCE).subject("alice")
            .expirationTime(new Date(System.currentTimeMillis() + 600_000));
    }

    private static String sign(JWTClaimsSet claims, RSAKey with) throws JOSEException {
        SignedJWT jwt = new SignedJWT(new JWSHeader.Builder(JWSAlgorithm.RS256).keyID(with.getKeyID()).build(), claims);
        jwt.sign(new RSASSASigner(with));
        return jwt.serialize();
    }

    private ApiResponse get(StudioApi api, String path, String authorization) {
        Map<String, String> headers = authorization == null ? Map.of() : Map.of("authorization", authorization);
        return api.handle(new ApiRequest("GET", path, null, headers, new byte[0]));
    }

    private StudioApi api(Authenticator auth) throws java.io.IOException {
        Fixture f = new Fixture(Fixture.assetsDir(dir));
        AtomicLong counter = new AtomicLong();
        return new StudioApi(f.store, f.writes, f.bus, java.time.Clock.systemUTC(), () -> new UUID(0, counter.incrementAndGet()),
            f.assets, java.util.Set.of(), auth);
    }

    private ApiResponse bearer(String token) throws java.io.IOException {
        return get(api(oidc("aud")), "/api/workspaces", "Bearer " + token);
    }

    private static Map<String, Object> json(ApiResponse r) throws ParseException {
        return JSONObjectUtils.parse(new String(r.body(), StandardCharsets.UTF_8));
    }

    @Test
    void localDefaultsToTheAdministratorAndHonoursTheHeader() throws Exception {
        StudioApi api = api(LocalAuthenticator.developers());
        assertEquals(200, get(api, "/api/workspaces", null).status());
        Map<String, Object> none = json(get(api, "/api/session", null));
        assertEquals("local", none.get("provider"));
        assertEquals(List.of("developer", "reviewer"), none.get("principalOption"));
        assertEquals("developer", none.get("principal"));
        assertEquals(true, none.get("admin"));
        ApiResponse r = api.handle(new ApiRequest("GET", "/api/session", null, Map.of("x-lattice-principal", "reviewer"), new byte[0]));
        assertEquals("reviewer", json(r).get("principal"));
        assertEquals(false, json(r).get("admin"));
    }

    @Test
    void localRefusesAnUnknownNameButAnswersHealthAndSessionToAnyone() throws Exception {
        StudioApi api = api(LocalAuthenticator.developers());
        Map<String, String> stranger = Map.of("x-lattice-principal", "mallory");
        ApiResponse refused = api.handle(new ApiRequest("GET", "/api/workspaces", null, stranger, new byte[0]));
        assertEquals(401, refused.status());
        assertNotNull(refused.headers().get("WWW-Authenticate"));
        assertEquals(200, api.handle(new ApiRequest("GET", "/api/health", null, stranger, new byte[0])).status());
        Map<String, Object> session = json(api.handle(new ApiRequest("GET", "/api/session", null, stranger, new byte[0])));
        assertEquals("local", session.get("provider"));
        assertNull(session.get("principal"));
    }

    @Test
    void fromEnvRefusesLocalOnAnyAddressButLoopback() {
        assertThrows(IllegalArgumentException.class, () -> Authenticator.fromEnv(Map.of(), "0.0.0.0"));
        assertInstanceOf(LocalAuthenticator.class, Authenticator.fromEnv(Map.of(), "127.0.0.1"));
        assertThrows(IllegalArgumentException.class, () -> Authenticator.fromEnv(Map.of("LATTICE_STUDIO_AUTH", "saml"), "127.0.0.1"));
    }

    @Test
    void oidcAcceptsASignedTokenAndNamesItsSubject() throws Exception {
        ApiResponse r = bearer(sign(claims().build(), key));
        assertEquals(200, r.status());
        StudioApi api = api(oidc("aud"));
        Map<String, Object> s = json(get(api, "/api/session", "Bearer " + sign(claims().build(), key)));
        assertEquals("oidc", s.get("provider"));
        assertEquals("alice", s.get("principal"));
        assertEquals(false, s.get("admin"));
        Map<String, Object> admin = json(get(api, "/api/session", "Bearer " + sign(claims().claim("groups", List.of("x", ADMIN)).build(), key)));
        assertEquals(true, admin.get("admin"));
    }

    @Test
    void oidcRefusesAnyTokenThatIsNotValid() throws Exception {
        assertEquals(401, bearer(sign(claims().expirationTime(new Date(System.currentTimeMillis() - 3_600_000)).build(), key)).status(), "expired");
        assertEquals(401, bearer(sign(claims().issuer("https://other.example.org").build(), key)).status(), "issuer");
        assertEquals(401, bearer(sign(claims().audience("another").build(), key)).status(), "audience");
        assertEquals(401, bearer(sign(claims().build(), otherKey)).status(), "another key");
        SignedJWT hs = new SignedJWT(new JWSHeader.Builder(JWSAlgorithm.HS256).keyID("k1").build(), claims().build());
        hs.sign(new MACSigner("0123456789abcdef0123456789abcdef"));
        assertEquals(401, bearer(hs.serialize()).status(), "HS256");
        assertEquals(401, bearer(new PlainJWT(claims().build()).serialize()).status(), "alg none");
        assertEquals(401, bearer("not-a-token").status(), "malformed");
        StudioApi api = api(oidc("aud"));
        assertEquals(401, get(api, "/api/workspaces", null).status(), "no header");
        assertEquals(401, get(api, "/api/workspaces", "Basic abc").status(), "not bearer");
    }

    @Test
    void oidcWithAClientIdClaimChecksThatInsteadOfAud() throws Exception {
        StudioApi api = api(oidc("client_id"));
        JWTClaimsSet.Builder noAud = new JWTClaimsSet.Builder().issuer(ISSUER).subject("alice")
            .expirationTime(new Date(System.currentTimeMillis() + 600_000));
        String good = sign(noAud.claim("client_id", AUDIENCE).build(), key);
        String bad = sign(noAud.claim("client_id", "another").build(), key);
        assertEquals(200, get(api, "/api/workspaces", "Bearer " + good).status());
        assertEquals(401, get(api, "/api/workspaces", "Bearer " + bad).status());
    }

    @Test
    void mcpNeedsAuthenticationUnderOidc() throws Exception {
        StudioApi api = api(oidc("aud"));
        ApiResponse r = api.handle(new ApiRequest("POST", "/mcp", null, Map.of("content-type", "application/json"), "{}".getBytes(StandardCharsets.UTF_8)));
        assertEquals(401, r.status());
        assertNotNull(r.headers().get("WWW-Authenticate"));
    }

    @Test
    void aSaveMadeAsReviewerLeavesAReceiptNamingReviewer() throws Exception {
        Fixture f = new Fixture(Fixture.assetsDir(dir));
        assertEquals(201, f.createWorkspace("One").status());
        String config = Fixture.PREFIXES + "ex:cfg <" + LATTICE + "surface#label> \"one\" .";
        ApiResponse r = f.send("PUT", "/api/workspaces/" + WS + "/graphs/surface", null,
            Map.of("content-type", Fixture.TURTLE, "if-match", "\"0\"", "x-lattice-principal", "reviewer"), config.getBytes(StandardCharsets.UTF_8));
        assertEquals(204, r.status());
        Model receipts = f.store.graph(Graphs.receipts(WS));
        List<Resource> saves = receipts.listSubjectsWithProperty(Cst.command, "save").toList();
        assertEquals(1, saves.size());
        assertEquals("reviewer", saves.get(0).getProperty(Cst.principal).getString());
        assertTrue(receipts.listSubjectsWithProperty(Cst.command, "create").toList().stream()
            .allMatch(c -> c.getProperty(Cst.principal).getString().equals("developer")));
    }
}
