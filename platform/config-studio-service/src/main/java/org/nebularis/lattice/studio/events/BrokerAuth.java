// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.events;

import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.util.Base64;
import java.util.HashMap;
import java.util.Map;
import java.util.function.Function;
import java.util.regex.Pattern;
import org.nebularis.lattice.studio.api.ApiResponse;
import org.nebularis.lattice.studio.auth.Principal;

/**
 * The answers RabbitMQ's HTTP auth backend asks for (PM-Q20 (d)). The broker checks identity only: a principal connects with its
 * name as the user and the app's own credential as the password, and may then write only its tab's watch topic and read only its
 * tab's events topic, {@code studio/u/<name>/<tab>/watch} and {@code .../events}, with the name in unpadded base64url. The rule never
 * names a workspace, so no permission the graph holds is copied into the broker, and the relay decides what each event reaches.
 *
 * <p>Each route, {@code /api/broker/<secret>/<check>}, takes the backend's form-encoded POST and answers {@code allow} or {@code deny}.
 * The secret is the one the broker was configured with, so a caller that does not know it is answered as for no route. The broker's
 * own users, the relay's among them, authenticate by its internal backend first and never reach these routes. A principal signed in
 * by the local authenticator, which trusts the name a request gives, connects with the service's local key as its password, which
 * only a page of the studio's origin can read from the session.
 */
public final class BrokerAuth {
    /** The routes' prefix, never routed by a proxy. */
    public static final String PREFIX = "/api/broker/";
    /** The exchange MQTT topics route through, the broker's default for {@code mqtt.exchange}. */
    public static final String EXCHANGE = "amq.topic";
    private static final Pattern TAB = Pattern.compile("[a-z0-9]{1,32}");
    private static final Base64.Encoder B64 = Base64.getUrlEncoder().withoutPadding();

    private final Function<Map<String, String>, Principal> authenticate;
    private final String localKey;

    /** {@code localKey} is null unless the deployment signs in locally, when it is the only password the broker's user check takes. */
    public BrokerAuth(Function<Map<String, String>, Principal> authenticate, String localKey) {
        this.authenticate = authenticate;
        this.localKey = localKey;
    }

    /** A new random key, 192 bits in base64url. */
    public static String newKey() {
        byte[] key = new byte[24];
        new java.security.SecureRandom().nextBytes(key);
        return B64.encodeToString(key);
    }

    /** The check a path names under {@code secret}, such as {@code user}, or null when the path does not carry that secret. */
    public static String check(String path, String secret) {
        if (secret == null || !path.startsWith(PREFIX)) {
            return null;
        }
        String rest = path.substring(PREFIX.length());
        int slash = rest.indexOf('/');
        if (slash < 0 || !same(rest.substring(0, slash), secret)) {
            return null;
        }
        return rest.substring(slash + 1);
    }

    /** Whether two secrets are equal, in time that does not depend on where they differ. */
    private static boolean same(String given, String expected) {
        return java.security.MessageDigest.isEqual(given.getBytes(StandardCharsets.UTF_8), expected.getBytes(StandardCharsets.UTF_8));
    }

    /** A principal's name as it appears in a topic, with no {@code .}, {@code /}, {@code +} or {@code #}. */
    public static String topicName(String principal) {
        return B64.encodeToString(principal.getBytes(StandardCharsets.UTF_8));
    }

    /** The principal a topic's name segment encodes, or null when it encodes none. */
    public static String principal(String topicName) {
        try {
            return new String(Base64.getUrlDecoder().decode(topicName), StandardCharsets.UTF_8);
        } catch (IllegalArgumentException e) {
            return null;
        }
    }

    public static boolean isTab(String tab) {
        return tab != null && TAB.matcher(tab).matches();
    }

    /** The MQTT client id a tab connects with, which names its principal so no one takes over another's session. */
    public static String clientId(String principal, String tab) {
        return "studio:" + topicName(principal) + ":" + tab;
    }

    /** The answer to {@code check}, one of {@code user}, {@code vhost}, {@code resource} and {@code topic}. */
    public ApiResponse handle(String method, String check, byte[] body) {
        if (!method.equals("POST")) {
            return ApiResponse.text(405, "method not allowed").with("Allow", "POST");
        }
        Map<String, String> p = form(body);
        boolean allow = switch (check) {
            case "user" -> user(p);
            case "vhost" -> "/".equals(p.get("vhost")) && tab(p) != null;
            case "resource" -> resource(p);
            case "topic" -> topic(p);
            default -> false;
        };
        return ApiResponse.text(200, allow ? "allow" : "deny");
    }

    private boolean user(Map<String, String> p) {
        String user = p.get("username");
        if (user == null || user.isBlank() || tab(p) == null) {
            return false;
        }
        String password = p.getOrDefault("password", "");
        Map<String, String> headers;
        if (localKey != null) {
            if (!same(password, localKey)) {
                return false;
            }
            headers = Map.of("x-lattice-principal", user);
        } else {
            if (password.isEmpty()) {
                return false;
            }
            headers = Map.of("authorization", "Bearer " + password);
        }
        Principal found = authenticate.apply(headers);
        return found != null && found.name().equals(user);
    }

    private static boolean resource(Map<String, String> p) {
        String tab = tab(p);
        if (tab == null) {
            return false;
        }
        String name = p.getOrDefault("name", "");
        return switch (p.getOrDefault("resource", "")) {
            case "queue" -> name.equals("mqtt-subscription-" + p.get("client_id") + "qos0") || name.equals("mqtt-subscription-" + p.get("client_id") + "qos1");
            case "exchange" -> name.equals(EXCHANGE) && ("read".equals(p.get("permission")) || "write".equals(p.get("permission")));
            default -> false;
        };
    }

    private static boolean topic(Map<String, String> p) {
        String tab = tab(p);
        if (tab == null || !EXCHANGE.equals(p.get("name"))) {
            return false;
        }
        String own = "studio.u." + topicName(p.get("username")) + "." + tab + ".";
        String key = p.getOrDefault("routing_key", "");
        return switch (p.getOrDefault("permission", "")) {
            case "read" -> key.equals(own + "events");
            case "write" -> key.equals(own + "watch");
            default -> false;
        };
    }

    /** The tab a request's MQTT client id names for its user, or null when the client id is not the user's, or absent, as for AMQP. */
    private static String tab(Map<String, String> p) {
        String user = p.get("username");
        String client = p.containsKey("client_id") ? p.get("client_id") : p.get("variable_map.client_id");
        if (user == null || client == null) {
            return null;
        }
        String prefix = "studio:" + topicName(user) + ":";
        String tab = client.startsWith(prefix) ? client.substring(prefix.length()) : null;
        return isTab(tab) ? tab : null;
    }

    private static Map<String, String> form(byte[] body) {
        Map<String, String> out = new HashMap<>();
        for (String pair : new String(body, StandardCharsets.UTF_8).split("&")) {
            int eq = pair.indexOf('=');
            if (eq > 0) {
                out.putIfAbsent(URLDecoder.decode(pair.substring(0, eq), StandardCharsets.UTF_8), URLDecoder.decode(pair.substring(eq + 1), StandardCharsets.UTF_8));
            }
        }
        return out;
    }
}
