// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.auth;

import java.util.Map;
import org.nebularis.lattice.studio.api.ApiRequest;

/**
 * Finds who made a request (ADR-A149 decision 8). The studio ships two: {@code local}, for development on a loopback
 * address, and {@code oidc}, for any OpenID Connect provider. A deployment may add its own.
 */
public interface Authenticator {
    /** The request's principal, or null when it does not authenticate. */
    Principal authenticate(ApiRequest req);

    /** What the browser needs to sign in, as {@code cst:} terms of the session description: the provider's name first. */
    Map<String, Object> settings();

    /**
     * The authenticator {@code LATTICE_STUDIO_AUTH} names, {@code local} when it names none. {@code local} refuses an
     * address other than loopback, since it trusts the name a request gives.
     */
    static Authenticator fromEnv(Map<String, String> env, String bind) {
        String kind = env.getOrDefault("LATTICE_STUDIO_AUTH", "local").trim();
        return switch (kind) {
            case "local" -> {
                if (!LocalAuthenticator.isLoopback(bind)) {
                    throw new IllegalArgumentException("LATTICE_STUDIO_AUTH=local trusts the name a request gives, so the service binds only to loopback, not " + bind);
                }
                yield LocalAuthenticator.fromEnv(env);
            }
            case "oidc" -> OidcAuthenticator.fromEnv(env);
            default -> throw new IllegalArgumentException("LATTICE_STUDIO_AUTH is local or oidc, not " + kind);
        };
    }
}
