// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.probes.msa;

import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/** Runs one probe mode. The modes and their options are listed in the README. */
public final class Main {
    private Main() {
    }

    /** Options as {@code --key value} pairs. */
    record Args(Map<String, String> map) {
        String str(String key, String fallback) {
            return map.getOrDefault(key, fallback);
        }

        int num(String key, int fallback) {
            return map.containsKey(key) ? Integer.parseInt(map.get(key)) : fallback;
        }

        long lng(String key, long fallback) {
            return map.containsKey(key) ? Long.parseLong(map.get(key)) : fallback;
        }

        boolean flag(String key) {
            return Boolean.parseBoolean(map.getOrDefault(key, "false"));
        }

        List<String> list(String key, String fallback) {
            return Arrays.asList(str(key, fallback).split(","));
        }
    }

    public static void main(String[] argv) throws Exception {
        if (argv.length == 0) {
            System.err.println("modes: declare delete publish consume dedup-pub count amqp-dup analyze");
            System.exit(2);
        }
        Map<String, String> map = new HashMap<>();
        for (int i = 1; i + 1 < argv.length; i += 2) {
            map.put(argv[i].replaceFirst("^--", ""), argv[i + 1]);
        }
        Args args = new Args(map);
        Log.open(args.str("id", argv[0]), args.str("log", ""));
        switch (argv[0]) {
            case "declare" -> Topo.declareMain(args);
            case "delete" -> Topo.deleteMain(args);
            case "publish" -> Pub.main(args);
            case "consume" -> Sac.main(args);
            case "dedup-pub" -> Dedup.publishMain(args);
            case "count" -> Dedup.countMain(args);
            case "amqp-dup" -> Dedup.amqpDupMain(args);
            case "analyze" -> Analyze.main(args);
            case "stored-offset" -> Offsets.main(args);
            default -> {
                System.err.println("unknown mode " + argv[0]);
                System.exit(2);
            }
        }
        System.out.flush();
        System.exit(0);
    }
}
