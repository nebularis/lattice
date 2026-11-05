// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.auth;

import java.net.InetAddress;
import java.net.UnknownHostException;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;
import org.nebularis.lattice.studio.api.ApiRequest;

/**
 * Development sign-in with no provider: a request names one of a few developer principals in {@code X-Lattice-Principal},
 * and a request naming none is the first. It trusts the name, so {@link Authenticator#fromEnv} allows it only on a
 * loopback address. The header is not one a page of another origin can send without a preflight the service never answers.
 */
public final class LocalAuthenticator implements Authenticator {
    public static final String HEADER = "x-lattice-principal";

    private final List<String> names;
    private final Set<String> admins;

    public LocalAuthenticator(List<String> names, Set<String> admins) {
        if (names.isEmpty() || names.stream().anyMatch(n -> !n.matches("[a-z][a-z0-9-]{0,39}"))) {
            throw new IllegalArgumentException("local principals are lower-case words with hyphens, at least one");
        }
        this.names = List.copyOf(names);
        this.admins = Set.copyOf(admins);
    }

    /** {@code developer}, who administers, and {@code reviewer}, who does not. */
    public static LocalAuthenticator developers() {
        return new LocalAuthenticator(List.of("developer", "reviewer"), Set.of("developer"));
    }

    static LocalAuthenticator fromEnv(Map<String, String> env) {
        String names = env.get("LATTICE_STUDIO_LOCAL_PRINCIPALS");
        if (names == null || names.isBlank()) {
            return developers();
        }
        return new LocalAuthenticator(list(names), Set.copyOf(list(env.getOrDefault("LATTICE_STUDIO_LOCAL_ADMINS", ""))));
    }

    private static List<String> list(String csv) {
        return Arrays.stream(csv.split(",")).map(String::trim).filter(s -> !s.isEmpty()).collect(Collectors.toList());
    }

    @Override
    public Principal authenticate(ApiRequest req) {
        String name = req.header(HEADER);
        name = name == null || name.isBlank() ? names.get(0) : name.trim();
        return names.contains(name) ? new Principal(name, admins.contains(name)) : null;
    }

    @Override
    public Map<String, Object> settings() {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("provider", "local");
        out.put("principalOption", names);
        out.put("administrator", admins.stream().sorted().toList());
        return out;
    }

    static boolean isLoopback(String host) {
        try {
            return host != null && InetAddress.getByName(host).isLoopbackAddress();
        } catch (UnknownHostException e) {
            return false;
        }
    }
}
