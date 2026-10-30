// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.morktransforms;

import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;

/** {@code xslt <stylesheet-file>} or {@code jolt <chain-file>}. Source on standard input, result on standard output, both UTF-8. */
public final class Main {
    private Main() {}

    public static void main(String[] args) throws Exception {
        try {
            if (args.length != 2 || !(args[0].equals("xslt") || args[0].equals("jolt"))) {
                throw new IllegalArgumentException("usage: mork-transforms (xslt <stylesheet-file> | jolt <chain-file>), source on standard input");
            }
            String spec = Files.readString(Path.of(args[1]), StandardCharsets.UTF_8);
            String in = new String(System.in.readAllBytes(), StandardCharsets.UTF_8);
            String out = args[0].equals("xslt") ? Transforms.xslt(spec, in) : Transforms.jolt(spec, in);
            PrintStream stdout = new PrintStream(System.out, false, StandardCharsets.UTF_8);
            stdout.print(out);
            stdout.flush();
        } catch (TransformException | java.io.IOException | IllegalArgumentException e) {
            System.err.println("mork-transforms: " + e.getMessage().replace('\n', ' '));
            System.exit(2);
        }
    }
}
