// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.minting;

import java.io.IOException;
import java.io.PrintStream;
import java.nio.file.Path;

/**
 * {@code java -jar lattice-minting.jar verify FILE…}: runs conformance vectors
 * or anchors against this library, one line per failure, exit status 1 on any
 * failure and 2 on bad usage.
 */
public final class Main {
    private Main() {
    }

    public static void main(String[] args) {
        System.exit(run(args, System.out, System.err));
    }

    static int run(String[] args, PrintStream out, PrintStream err) {
        if (args.length < 2 || !"verify".equals(args[0])) {
            err.println("usage: lattice-mint verify FILE…");
            return 2;
        }
        int failed = 0;
        for (int i = 1; i < args.length; i++) {
            Conformance.Report report;
            try {
                report = Conformance.verify(Path.of(args[i]));
            } catch (IOException | IllegalArgumentException e) {
                err.println(args[i] + ": " + e.getMessage());
                failed++;
                continue;
            }
            report.failures().forEach(f -> out.println("FAIL " + f));
            out.println(args[i] + ": " + report.passed() + " checks passed, " + report.failures().size() + " failed");
            failed += report.failures().size();
        }
        return failed == 0 ? 0 : 1;
    }
}
