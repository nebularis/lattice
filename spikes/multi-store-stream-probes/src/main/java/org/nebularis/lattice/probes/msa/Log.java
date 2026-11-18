// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.probes.msa;

import java.io.FileOutputStream;
import java.io.IOException;
import java.io.OutputStream;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;

/** One JSON object per line, on standard output and, when a file is named, appended to it and flushed per line. */
final class Log {
    private static volatile OutputStream file;
    private static volatile String who = "?";

    private Log() {
    }

    static void open(String id, String path) {
        who = id;
        if (path != null && !path.isEmpty()) {
            try {
                file = new FileOutputStream(path, true);
            } catch (IOException e) {
                throw new UncheckedIOException(e);
            }
        }
    }

    /** Pairs of key and value. A string is quoted, a number or a boolean is written as it is. */
    static synchronized void ev(String ev, Object... kv) {
        StringBuilder b = new StringBuilder(96);
        b.append("{\"t\":").append(System.currentTimeMillis()).append(",\"c\":");
        quote(b, who);
        b.append(",\"e\":");
        quote(b, ev);
        for (int i = 0; i + 1 < kv.length; i += 2) {
            b.append(',');
            quote(b, String.valueOf(kv[i]));
            b.append(':');
            Object v = kv[i + 1];
            if (v instanceof Number || v instanceof Boolean) {
                b.append(v);
            } else {
                quote(b, String.valueOf(v));
            }
        }
        b.append("}\n");
        byte[] bytes = b.toString().getBytes(StandardCharsets.UTF_8);
        System.out.write(bytes, 0, bytes.length);
        System.out.flush();
        OutputStream f = file;
        if (f != null) {
            try {
                f.write(bytes);
                f.flush();
            } catch (IOException e) {
                throw new UncheckedIOException(e);
            }
        }
    }

    private static void quote(StringBuilder b, String s) {
        b.append('"');
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            if (c == '"' || c == '\\') {
                b.append('\\').append(c);
            } else if (c < 0x20 || c > 0x7e) {
                b.append(String.format("\\u%04x", (int) c));
            } else {
                b.append(c);
            }
        }
        b.append('"');
    }
}
