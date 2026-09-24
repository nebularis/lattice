// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.minting;

import static org.nebularis.lattice.minting.Values.entry;
import static org.nebularis.lattice.minting.Values.integer;
import static org.nebularis.lattice.minting.Values.list;
import static org.nebularis.lattice.minting.Values.map;

import java.math.BigInteger;
import java.nio.charset.StandardCharsets;
import java.security.SecureRandom;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.HexFormat;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.function.IntFunction;
import java.util.function.UnaryOperator;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Mints IRIs from one verified recipe (identity-minting-specification.md §6).
 *
 * <p>{@code secrets} maps a claim scheme's key id to the secret's bytes, and is
 * needed only for claimed identity. The minter copies it at construction and
 * never returns or logs it. {@code randomBytes} returns n cryptographically
 * secure random bytes; replace it only in tests.
 *
 * <p>Request inputs are the members listed in §6: {@code key} (a list of raw
 * key values), {@code scope}, {@code surrogate}, {@code target},
 * {@code namespaceToken}, {@code epoch}, {@code seq}, {@code canonicalNQuads},
 * {@code canonicalizer}, {@code iri}, and {@code randomHex} (vectors only).
 */
public final class Minter {
    public static final long MAX_POSITION = Long.MAX_VALUE;
    private static final String TOKEN_PATTERN = "^[A-Za-z0-9._~-]+$";
    private static final Pattern TOKEN = Pattern.compile(TOKEN_PATTERN);
    private static final Pattern SLOT = Pattern.compile("\\{([A-Za-z]+)\\}");
    private static final SecureRandom RANDOM = new SecureRandom();

    private final Recipe recipe;
    private final Map<String, Object> r;
    private final Map<String, byte[]> secrets;
    private final IntFunction<byte[]> random;

    public Minter(Recipe recipe) {
        this(recipe, Map.of());
    }

    public Minter(Recipe recipe, Map<String, byte[]> secrets) {
        this(recipe, secrets, Minter::secureRandomBytes);
    }

    public Minter(Recipe recipe, Map<String, byte[]> secrets, IntFunction<byte[]> randomBytes) {
        Ucd.checkRuntime();
        this.recipe = Objects.requireNonNull(recipe);
        this.r = recipe.data();
        Map<String, byte[]> copy = new HashMap<>();
        if (secrets != null) {
            secrets.forEach((k, v) -> copy.put(k, v == null ? null : v.clone()));
        }
        this.secrets = copy;
        this.random = Objects.requireNonNull(randomBytes);
    }

    private static byte[] secureRandomBytes(int n) {
        byte[] b = new byte[n];
        RANDOM.nextBytes(b);
        return b;
    }

    public Recipe recipe() {
        return recipe;
    }

    static String render(String template, Map<String, String> slots) {
        return SLOT.matcher(template).replaceAll(m -> {
            String v = slots.get(m.group(1));
            if (v == null) {
                throw new IllegalArgumentException("template slot {" + m.group(1) + "} is not available");
            }
            return Matcher.quoteReplacement(v);
        });
    }

    // ---- shared steps --------------------------------------------------------------------------------

    private String normalize(Map<String, Object> pipeline, Object raw, int index, List<Map<String, Object>> trace) {
        if (!(raw instanceof String input)) {
            throw new MintException(MintError.MissingKeyComponent, "key component " + index + " is missing");
        }
        String value = input;
        List<Object> after = new ArrayList<>();
        for (Object step : list(pipeline.get("steps"))) {
            UnaryOperator<String> fn = Ucd.step((String) step);
            value = fn.apply(value);
            after.add(entry("step", step, "output", value));
        }
        if (value.isEmpty()) {
            throw new MintException(MintError.EmptyKeyComponent, "key component " + index + " is empty after normalization");
        }
        trace.add(entry("step", "normalize", "component", (long) index, "pipeline", pipeline.get("id"),
                "input", input, "after", after, "output", value));
        return value;
    }

    private record KeyValues(List<String> scope, List<String> normalized) {
    }

    private KeyValues key(Map<String, Object> key, Map<String, ?> inputs, List<Map<String, Object>> trace) {
        List<?> values = inputs.get("key") instanceof List<?> l ? l : List.of();
        int n = list(key.get("properties")).size();
        if (values.size() < n) {
            throw new MintException(MintError.MissingKeyComponent, n + " key components needed, " + values.size() + " given");
        }
        List<String> scope = List.of();
        if (key.get("scopeProperty") instanceof String sp && !sp.isEmpty()) {
            if (!(inputs.get("scope") instanceof String s)) {
                throw new MintException(MintError.MissingKeyComponent, "the key's scope value is missing");
            }
            scope = List.of(s);
        }
        List<String> normalized = new ArrayList<>();
        for (int i = 0; i < n; i++) {
            normalized.add(normalize(map(key.get("pipeline")), values.get(i), i, trace));
        }
        return new KeyValues(scope, normalized);
    }

    private String digest(byte[] data, Map<String, Object> spec, List<Map<String, Object>> trace,
                          byte[] macKey, String keyId, Integer claim) {
        byte[] full;
        Map<String, Object> step;
        if (macKey == null) {
            full = Canonical.sha256(data);
            step = entry("step", "digest");
            tag(step, claim);
            step.put("function", "SHA-256");
        } else {
            full = Canonical.hmacSha256(macKey, data);
            step = entry("step", "mac");
            tag(step, claim);
            step.put("function", "HMAC-SHA-256");
            step.put("keyId", keyId);
        }
        step.put("hex", hex(full));
        trace.add(step);
        int width = integer(spec.get("widthBits"));
        byte[] cut = Arrays.copyOf(full, width / 8);
        Map<String, Object> truncate = entry("step", "truncate");
        tag(truncate, claim);
        truncate.put("widthBits", (long) width);
        truncate.put("hex", hex(cut));
        trace.add(truncate);
        String encoding = (String) spec.get("encoding");
        String value = Canonical.encode(cut, encoding);
        Map<String, Object> encode = entry("step", "encode");
        tag(encode, claim);
        encode.put("encoding", encoding);
        encode.put("value", value);
        trace.add(encode);
        return value;
    }

    private static void tag(Map<String, Object> step, Integer claim) {
        if (claim != null) {
            step.put("claim", (long) claim);
        }
    }

    private static String hex(byte[] b) {
        return HexFormat.of().formatHex(b);
    }

    private static String match(String pattern, Object value, String what) {
        if (!(value instanceof String s) || !Pattern.compile(pattern).matcher(s).matches()) {
            throw new MintException(MintError.PatternMismatch, what + " " + value + " does not match " + pattern);
        }
        return s;
    }

    private String uuid(Map<String, ?> inputs, List<Map<String, Object>> trace) {
        byte[] raw = inputs.get("randomHex") instanceof String h ? HexFormat.of().parseHex(h) : random.apply(16);
        String value = Canonical.uuid4From(raw);
        trace.add(entry("step", "generate-surrogate", "randomHex", hex(raw), "value", value));
        return value;
    }

    // ---- strategies ----------------------------------------------------------------------------------

    /** Mint (or, for adopted identity, validate) one identifier. A refusal throws {@link MintException}. */
    public Minted mint(Map<String, ?> inputs) {
        String s = recipe.strategy();
        List<Map<String, Object>> trace = new ArrayList<>();
        return switch (s) {
            case "AdoptedIdentity", "ExternalRegistryIdentity" -> {
                String pattern = (String) r.get("acceptedPattern");
                String iri = match(pattern, inputs.get("iri"), "identifier");
                trace.add(entry("step", "validate-iri", "pattern", pattern, "value", iri));
                yield new Minted(iri, List.of(), trace, null);
            }
            case "NaturalKeyIdentity" -> {
                KeyValues kv = key(map(r.get("key")), inputs, trace);
                List<String> parts = new ArrayList<>();
                for (String v : concat(kv.scope(), kv.normalized())) {
                    parts.add(Canonical.percentEncode(v));
                }
                trace.add(entry("step", "percent-encode", "components", parts));
                yield done(render((String) r.get("iriTemplate"), Map.of("key", String.join("/", parts))), trace, null);
            }
            case "DerivedHashIdentity" -> {
                KeyValues kv = key(map(r.get("key")), inputs, trace);
                List<String> components = new ArrayList<>();
                for (Object p : list(r.get("tuplePrefix"))) {
                    components.add((String) p);
                }
                components.addAll(kv.scope());
                components.addAll(kv.normalized());
                byte[] data = Canonical.tupleBytes(components);
                trace.add(entry("step", "tuple", "components", components, "hex", hex(data)));
                String digest = digest(data, map(r.get("digest")), trace, null, null, null);
                yield done(render((String) r.get("iriTemplate"), Map.of("digest", digest)), trace, null);
            }
            case "RandomSurrogateIdentity" ->
                    done(render((String) r.get("iriTemplate"), Map.of("surrogate", uuid(inputs, trace))), trace, null);
            case "SurrogateClaimedIdentity" -> claimed(inputs, trace);
            case "PositionDerivedEvent" -> position(inputs, trace);
            case "ContentAddressedIdentity" -> content(inputs, trace);
            default -> throw new MintException(MintError.UnsupportedRecipeFormat, "strategy " + s);
        };
    }

    private static List<String> concat(List<String> a, List<String> b) {
        List<String> out = new ArrayList<>(a);
        out.addAll(b);
        return out;
    }

    private static Minted done(String iri, List<Map<String, Object>> trace, String canonicalizer) {
        trace.add(entry("step", "render", "iri", iri));
        return new Minted(iri, List.of(), trace, canonicalizer);
    }

    private Minted claimed(Map<String, ?> inputs, List<Map<String, Object>> trace) {
        Map<String, Object> sur = map(r.get("surrogate"));
        String value;
        if ("CallerSuppliedSurrogate".equals(sur.get("kind"))) {
            String pattern = (String) sur.get("pattern");
            value = match(pattern, inputs.get("surrogate"), "surrogate");
            trace.add(entry("step", "validate-surrogate", "pattern", pattern, "value", value));
        } else {
            value = uuid(inputs, trace);
        }
        String iri = render((String) r.get("iriTemplate"), Map.of("surrogate", value));
        trace.add(entry("step", "render", "iri", iri));
        List<?> claims = list(r.get("claims"));
        KeyValues kv = key(map(map(claims.get(0)).get("key")), inputs, trace);
        List<String> claimIris = new ArrayList<>();
        for (int ix = 0; ix < claims.size(); ix++) {
            Map<String, Object> c = map(claims.get(ix));
            String keyId = (String) c.get("keyId");
            byte[] secret = secrets.get(keyId);
            if (secret == null || secret.length == 0) {
                throw new MintException(MintError.MissingSecret, "no secret supplied for key id " + keyId);
            }
            List<String> components = new ArrayList<>();
            components.add((String) c.get("schemeVersion"));
            components.add((String) c.get("constraintId"));
            components.add(kv.scope().isEmpty() ? "" : kv.scope().get(0));
            components.addAll(kv.normalized());
            byte[] data = Canonical.tupleBytes(components);
            trace.add(entry("step", "tuple", "claim", (long) ix, "components", components, "hex", hex(data)));
            String mac = digest(data, map(c.get("mac")), trace, secret, keyId, ix);
            String claimIri = render((String) c.get("iriTemplate"), Map.of(
                    "constraintId", (String) c.get("constraintId"), "schemeVersion", (String) c.get("schemeVersion"), "mac", mac));
            trace.add(entry("step", "render", "claim", (long) ix, "iri", claimIri));
            claimIris.add(claimIri);
        }
        return new Minted(iri, claimIris, trace, null);
    }

    private Minted position(Map<String, ?> inputs, List<Map<String, Object>> trace) {
        Map<String, Object> ns = map(r.get("namespace"));
        String namespace;
        if ("HashedTargetDerivation".equals(ns.get("derivation"))) {
            if (!(inputs.get("target") instanceof String target) || target.isEmpty()) {
                throw new MintException(MintError.MissingKeyComponent, "the target IRI is missing");
            }
            List<String> components = List.of("occurrence-namespace/1", target);
            byte[] data = Canonical.tupleBytes(components);
            trace.add(entry("step", "tuple", "components", components, "hex", hex(data)));
            namespace = digest(data, map(ns.get("digest")), trace, null, null, null);
        } else {
            if (!(inputs.get("namespaceToken") instanceof String token) || !TOKEN.matcher(token).matches()) {
                throw new MintException(MintError.PatternMismatch,
                        "namespace token " + inputs.get("namespaceToken") + " is not [A-Za-z0-9._~-]+");
            }
            namespace = token;
            trace.add(entry("step", "validate-token", "pattern", TOKEN_PATTERN, "value", namespace));
        }
        String epoch = pad(inputs.get("epoch"), "epoch", integer(r.get("epochWidth")));
        String seq = pad(inputs.get("seq"), "seq", integer(r.get("sequenceWidth")));
        trace.add(entry("step", "pad", "epoch", epoch, "seq", seq));
        String iri = render((String) r.get("iriTemplate"), Map.of("namespace", namespace, "epoch", epoch, "seq", seq));
        return done(iri, trace, null);
    }

    private static String pad(Object v, String name, int width) {
        if (!(v instanceof Long || v instanceof Integer || v instanceof BigInteger)) {
            throw new MintException(MintError.MissingKeyComponent, name + " is missing or not an integer");
        }
        if (v instanceof BigInteger || ((Number) v).longValue() < 0) {
            throw new MintException(MintError.PositionOutOfRange, name + " " + v + " is outside 0.." + MAX_POSITION);
        }
        String digits = Long.toString(((Number) v).longValue());
        return "0".repeat(Math.max(0, width - digits.length())) + digits;
    }

    private Minted content(Map<String, ?> inputs, List<Map<String, Object>> trace) {
        if (!(inputs.get("canonicalizer") instanceof String canonicalizer) || Ucd.trimWhiteSpace(canonicalizer).isEmpty()) {
            throw new MintException(MintError.CanonicalizerNotDeclared,
                    "content-addressed minting needs a statement of which RDFC-1.0 implementation produced "
                            + "the bytes (identity-minting-specification.md §7, CA-1)");
        }
        if (!(inputs.get("canonicalNQuads") instanceof String nquads)) {
            throw new MintException(MintError.MissingKeyComponent, "canonicalNQuads is missing");
        }
        String value = digest(nquads.getBytes(StandardCharsets.UTF_8), map(r.get("digest")), trace, null, null, null);
        return done(render((String) r.get("iriTemplate"), Map.of("digest", value)), trace, canonicalizer);
    }
}
