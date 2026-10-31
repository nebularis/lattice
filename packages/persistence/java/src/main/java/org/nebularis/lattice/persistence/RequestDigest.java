// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.persistence;

import java.io.ByteArrayOutputStream;
import java.math.BigInteger;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.Collection;
import java.util.HexFormat;
import java.util.List;
import java.util.Map;

/**
 * The request digest (ADR-A123 fifth addendum, ADR-A132 decision 2).
 *
 * <pre>requestDigest = hex(SHA-256(enc([kind, target, expected, part, part, ...])))</pre>
 *
 * {@code enc} writes each component as the decimal length of its UTF-8 bytes, a colon and the bytes. {@code kind} is the profile's
 * operation kind, {@code target} is the IRI without angle brackets and {@code expected} is the expected seq as a decimal string, and a
 * part the operation does not have is the empty string. Each content part is one component, the {@code enc} of the sorted, de-duplicated
 * canonical N-Triples lines of its slots, so a triple's role is part of what is hashed. The parts follow the profile's order.
 */
public final class RequestDigest {
    private RequestDigest() {}

    /** The length-prefixed tuple encoding of the components. */
    public static byte[] enc(List<byte[]> components) {
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        for (byte[] c : components) {
            out.writeBytes(Integer.toString(c.length).getBytes(StandardCharsets.US_ASCII));
            out.write(':');
            out.writeBytes(c);
        }
        return out.toByteArray();
    }

    /** The bytes that are hashed. Each of {@code parts} is the canonical N-Triples lines of one content part, in the contract's order. */
    public static byte[] digestInput(String kind, String target, String expected, List<? extends Collection<String>> parts) {
        List<byte[]> components = new ArrayList<>(List.of(Text.utf8(kind), Text.utf8(target), Text.utf8(expected)));
        for (Collection<String> lines : parts) components.add(enc(Text.sortedUnique(lines).stream().map(Text::utf8).toList()));
        return enc(components);
    }

    /** The SHA-256 of {@code data}, as lower-case hex. */
    public static String digestHex(byte[] data) {
        try {
            return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(data));
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException(e);
        }
    }

    private static String iriText(Object value) {
        if (value instanceof Iri i) return i.value();
        if (value instanceof String s) return s;
        throw new DigestException("a target must be an IRI string, got " + value);
    }

    private static List<String> lines(String slot, Object value) {
        if (value instanceof Payload p) return p.lines();
        if (value instanceof Rows r) return r.payload().lines();
        throw new DigestException("slot " + Text.repr(slot) + " must be a Payload or Rows, got " + (value == null ? "null" : value.getClass().getSimpleName()));
    }

    /** The bytes to hash for {@code operation} with the parameter and slot {@code values} of the request, read by the profile's digest contract. */
    public static byte[] requestInput(OperationContract operation, Map<String, ?> values) {
        DigestSpec spec = operation.digest();
        if (spec == null) throw new DigestException("operation " + operation.templateId() + " has no requestDigest");
        if (!spec.algorithm().equals("SHA-256")) throw new DigestException("unsupported digest algorithm " + Text.repr(spec.algorithm()));
        String target = "", expected = "";
        List<List<String>> content = new ArrayList<>();
        for (DigestPart part : spec.parts()) {
            for (String source : part.sources()) {
                if (!values.containsKey(source)) {
                    throw new DigestException(operation.templateId() + " digest part " + part.role() + " needs " + Text.repr(source) + ", which was not given");
                }
            }
            switch (part.role()) {
                case "OperationKindPart" -> { }
                case "TargetPart" -> target = part.sources().isEmpty() ? "" : iriText(values.get(part.sources().get(0)));
                case "ExpectedSeqPart" -> {
                    if (!part.sources().isEmpty()) {
                        Object seq = values.get(part.sources().get(0));
                        if (!(seq instanceof Long || seq instanceof Integer || seq instanceof Short || seq instanceof Byte || seq instanceof BigInteger)) {
                            throw new DigestException("the expected seq must be an int, got " + seq);
                        }
                        expected = seq.toString();
                    }
                }
                case "PayloadPart", "EventPart", "AddPart", "DelPart" -> {
                    List<String> all = new ArrayList<>();
                    for (String s : part.sources()) all.addAll(lines(s, values.get(s)));
                    content.add(all);
                }
                default -> throw new DigestException("unknown digest part role " + Text.repr(part.role()));
            }
        }
        return digestInput(operation.kind().value(), target, expected, content);
    }

    /** The {@code requestDigest} of a request, as lower-case hex. */
    public static String requestDigest(OperationContract operation, Map<String, ?> values) {
        return digestHex(requestInput(operation, values));
    }
}
