// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.auth;

import com.nimbusds.jose.JWSAlgorithm;
import com.nimbusds.jose.jwk.source.JWKSource;
import com.nimbusds.jose.jwk.source.JWKSourceBuilder;
import com.nimbusds.jose.proc.JWSVerificationKeySelector;
import com.nimbusds.jose.proc.SecurityContext;
import com.nimbusds.jose.util.JSONObjectUtils;
import com.nimbusds.jwt.JWTClaimsSet;
import com.nimbusds.jwt.proc.DefaultJWTClaimsVerifier;
import com.nimbusds.jwt.proc.DefaultJWTProcessor;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.Collection;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;
import org.nebularis.lattice.studio.api.ApiRequest;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Sign-in through an OpenID Connect provider, for example Okta, Microsoft Entra ID or AWS Cognito. A request carries an
 * access token as {@code Authorization: Bearer}, which is accepted when the provider's published keys verify its
 * signature, with an asymmetric algorithm only, and it names the configured issuer and audience and has not expired. The
 * principal's name is a configured claim, and a principal administers when another claim holds a configured value. The
 * browser obtains the token itself, by the authorization code flow with PKCE, from the endpoints {@link #settings()} gives.
 */
public final class OidcAuthenticator implements Authenticator {
    private static final Logger LOG = LoggerFactory.getLogger(OidcAuthenticator.class);
    private static final Set<JWSAlgorithm> ALGORITHMS = Set.of(JWSAlgorithm.RS256, JWSAlgorithm.RS384, JWSAlgorithm.RS512,
        JWSAlgorithm.PS256, JWSAlgorithm.PS384, JWSAlgorithm.PS512, JWSAlgorithm.ES256, JWSAlgorithm.ES384);

    private final DefaultJWTProcessor<SecurityContext> processor = new DefaultJWTProcessor<>();
    private final String audience;
    private final String audienceClaim;
    private final String nameClaim;
    private final String adminClaim;
    private final String adminValue;
    private final Map<String, Object> settings;

    /**
     * {@code audienceClaim} is {@code aud} for most providers, and {@code client_id} for one whose access tokens carry
     * no audience, as Cognito's do. {@code adminValue} null makes nobody an administrator.
     */
    public OidcAuthenticator(String issuer, String audience, String audienceClaim, JWKSource<SecurityContext> keys,
                             String nameClaim, String adminClaim, String adminValue, Map<String, Object> browser) {
        this.audience = audience;
        this.audienceClaim = audienceClaim;
        this.nameClaim = nameClaim;
        this.adminClaim = adminClaim;
        this.adminValue = adminValue;
        processor.setJWSKeySelector(new JWSVerificationKeySelector<>(ALGORITHMS, keys));
        DefaultJWTClaimsVerifier<SecurityContext> verifier = "aud".equals(audienceClaim)
            ? new DefaultJWTClaimsVerifier<>(audience, new JWTClaimsSet.Builder().issuer(issuer).build(), Set.of("exp", nameClaim))
            : new DefaultJWTClaimsVerifier<>(new JWTClaimsSet.Builder().issuer(issuer).build(), Set.of("exp", nameClaim, audienceClaim));
        verifier.setMaxClockSkew(60);
        processor.setJWTClaimsSetVerifier(verifier);
        Map<String, Object> s = new LinkedHashMap<>();
        s.put("provider", "oidc");
        s.put("issuer", issuer);
        s.putAll(browser);
        this.settings = Map.copyOf(s);
    }

    /**
     * Reads {@code LATTICE_STUDIO_OIDC_ISSUER} and {@code LATTICE_STUDIO_OIDC_AUDIENCE}, both required, and the
     * provider's discovery document for its keys and endpoints, unless {@code LATTICE_STUDIO_OIDC_JWKS_URL} names the keys.
     */
    static OidcAuthenticator fromEnv(Map<String, String> env) {
        String issuer = required(env, "LATTICE_STUDIO_OIDC_ISSUER").replaceAll("/+$", "");
        String audience = required(env, "LATTICE_STUDIO_OIDC_AUDIENCE");
        Map<String, Object> discovery = discover(issuer);
        String jwks = env.getOrDefault("LATTICE_STUDIO_OIDC_JWKS_URL", String.valueOf(discovery.get("jwks_uri")));
        JWKSource<SecurityContext> keys;
        try {
            keys = JWKSourceBuilder.create(URI.create(jwks).toURL()).retrying(true).build();
        } catch (java.net.MalformedURLException | IllegalArgumentException e) {
            throw new IllegalArgumentException("the provider's keys are not at a URL: " + jwks, e);
        }
        Map<String, Object> browser = new LinkedHashMap<>();
        browser.put("clientId", env.getOrDefault("LATTICE_STUDIO_OIDC_CLIENT_ID", audience));
        browser.put("scope", env.getOrDefault("LATTICE_STUDIO_OIDC_SCOPE", "openid profile email"));
        browser.put("authorizationEndpoint", String.valueOf(discovery.get("authorization_endpoint")));
        browser.put("tokenEndpoint", String.valueOf(discovery.get("token_endpoint")));
        return new OidcAuthenticator(issuer, audience, env.getOrDefault("LATTICE_STUDIO_OIDC_AUDIENCE_CLAIM", "aud"), keys,
            env.getOrDefault("LATTICE_STUDIO_OIDC_NAME_CLAIM", "sub"), env.getOrDefault("LATTICE_STUDIO_OIDC_ADMIN_CLAIM", "groups"),
            env.get("LATTICE_STUDIO_OIDC_ADMIN_VALUE"), browser);
    }

    private static String required(Map<String, String> env, String name) {
        String v = env.get(name);
        if (v == null || v.isBlank()) {
            throw new IllegalArgumentException(name + " is required when LATTICE_STUDIO_AUTH=oidc");
        }
        return v.trim();
    }

    private static Map<String, Object> discover(String issuer) {
        try {
            HttpResponse<String> r = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(10)).build().send(
                HttpRequest.newBuilder(URI.create(issuer + "/.well-known/openid-configuration")).timeout(Duration.ofSeconds(10)).build(),
                HttpResponse.BodyHandlers.ofString());
            if (r.statusCode() != 200) {
                throw new IllegalStateException("the provider's discovery document answered " + r.statusCode());
            }
            return JSONObjectUtils.parse(r.body());
        } catch (java.io.IOException | java.text.ParseException e) {
            throw new IllegalStateException("the provider's discovery document could not be read from " + issuer, e);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException("interrupted reading the provider's discovery document", e);
        }
    }

    @Override
    public Principal authenticate(ApiRequest req) {
        String header = req.header("authorization");
        if (header == null || !header.regionMatches(true, 0, "Bearer ", 0, 7)) {
            return null;
        }
        try {
            JWTClaimsSet claims = processor.process(header.substring(7).trim(), null);
            if (!"aud".equals(audienceClaim) && !audience.equals(claims.getClaim(audienceClaim))) {
                return null;
            }
            Object name = claims.getClaim(nameClaim);
            if (!(name instanceof String n) || n.isBlank()) {
                return null;
            }
            Object groups = claims.getClaim(adminClaim);
            boolean admin = adminValue != null && (adminValue.equals(groups)
                || (groups instanceof Collection<?> c && c.contains(adminValue)));
            return new Principal(n, admin);
        } catch (java.text.ParseException | com.nimbusds.jose.proc.BadJOSEException | com.nimbusds.jose.JOSEException e) {
            LOG.debug("a bearer token was refused: {}", e.getMessage());
            return null;
        }
    }

    @Override
    public Map<String, Object> settings() {
        return settings;
    }
}
