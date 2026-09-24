// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.minting;

import java.io.ByteArrayOutputStream;
import java.nio.charset.StandardCharsets;
import java.security.GeneralSecurityException;
import java.security.MessageDigest;
import java.util.Base64;
import java.util.HexFormat;
import java.util.List;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;

/** Byte-level building blocks (identity-minting-specification.md §4, §6). */
public final class Canonical {
    private static final String BASE32 = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
    private static final byte[] UNRESERVED = new byte[128];

    static {
        for (char c : "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~".toCharArray()) {
            UNRESERVED[c] = 1;
        }
    }

    private Canonical() {
    }

    /**
     * {@code length-prefixed-utf8/1} (§4.1). The length is the UTF-8 byte count,
     * never {@link String#length()}, which counts UTF-16 code units.
     */
    public static byte[] tupleBytes(List<String> components) {
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        for (String c : components) {
            byte[] b = c.getBytes(StandardCharsets.UTF_8);
            out.writeBytes(Integer.toString(b.length).getBytes(StandardCharsets.US_ASCII));
            out.write(':');
            out.writeBytes(b);
        }
        return out.toByteArray();
    }

    public static byte[] sha256(byte[] data) {
        try {
            return MessageDigest.getInstance("SHA-256").digest(data);
        } catch (GeneralSecurityException e) {
            throw new IllegalStateException("SHA-256 is required of every Java runtime", e);
        }
    }

    /** HMAC-SHA-256. The key must not be empty: the minter refuses an empty secret first. */
    public static byte[] hmacSha256(byte[] key, byte[] data) {
        try {
            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(key, "HmacSHA256"));
            return mac.doFinal(data);
        } catch (GeneralSecurityException e) {
            throw new IllegalStateException("HmacSHA256 is required of every Java runtime", e);
        }
    }

    /** §4.3: lowercase hex, RFC 4648 base32 (uppercase) or base64url, unpadded. */
    public static String encode(byte[] data, String encoding) {
        return switch (encoding) {
            case "lowercase-hex" -> HexFormat.of().formatHex(data);
            case "base32" -> base32(data);
            case "base64url" -> Base64.getUrlEncoder().withoutPadding().encodeToString(data);
            default -> throw new IllegalArgumentException("unknown encoding " + encoding);
        };
    }

    private static String base32(byte[] data) {
        StringBuilder sb = new StringBuilder();
        int buffer = 0;
        int bits = 0;
        for (byte b : data) {
            buffer = (buffer << 8) | (b & 0xFF);
            bits += 8;
            while (bits >= 5) {
                sb.append(BASE32.charAt((buffer >> (bits - 5)) & 31));
                bits -= 5;
            }
        }
        if (bits > 0) {
            sb.append(BASE32.charAt((buffer << (5 - bits)) & 31));
        }
        return sb.toString();
    }

    /** §6.2: unreserved bytes kept, every other UTF-8 byte written %XX in uppercase hex. */
    public static String percentEncode(String value) {
        StringBuilder sb = new StringBuilder();
        for (byte b : value.getBytes(StandardCharsets.UTF_8)) {
            int u = b & 0xFF;
            if (u < 128 && UNRESERVED[u] == 1) {
                sb.append((char) u);
            } else {
                sb.append('%').append(HexFormat.of().withUpperCase().toHexDigits((byte) u));
            }
        }
        return sb.toString();
    }

    /** A version 4 UUID from 16 random bytes (RFC 9562), lowercase 8-4-4-4-12 (§6.3). */
    public static String uuid4From(byte[] random16) {
        if (random16.length != 16) {
            throw new IllegalArgumentException("a UUIDv4 needs exactly 16 random bytes");
        }
        byte[] b = random16.clone();
        b[6] = (byte) ((b[6] & 0x0F) | 0x40);
        b[8] = (byte) ((b[8] & 0x3F) | 0x80);
        String h = HexFormat.of().formatHex(b);
        return h.substring(0, 8) + "-" + h.substring(8, 12) + "-" + h.substring(12, 16) + "-" + h.substring(16, 20) + "-" + h.substring(20);
    }
}
