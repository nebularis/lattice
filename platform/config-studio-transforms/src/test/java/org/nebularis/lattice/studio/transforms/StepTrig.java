// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.transforms;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Random;

/**
 * A simulate run's TriG built from parts, so a test can write the same world and step in any order. Every statement is one N-Triples line, the
 * graphs are blocks, and a seed other than 0 shuffles the blocks, the lines of each and splits a graph over two blocks, which TriG merges.
 */
final class StepTrig {
    static final String PAT = "https://www.nebularis.org/neuro-semantic/lattice/persistence-store#";
    static final String CST = "https://www.nebularis.org/neuro-semantic/lattice/config-studio#";
    static final String EX = "https://example.org/lending#";
    static final String XSD = "http://www.w3.org/2001/XMLSchema#";
    static final String ROOT = EX + "facility-1";

    final Map<String, List<String>> graphs = new LinkedHashMap<>();
    final Map<String, String> parameters = new LinkedHashMap<>();
    final Map<String, List<String>> payloads = new LinkedHashMap<>();
    String targetClass = FacilityJob.CLASS;
    String operation;
    String time = "2026-03-31T23:59:58Z";
    final List<String> extraStepLines = new ArrayList<>();

    static String iri(String value) {
        return "<" + value + ">";
    }

    static String typed(String lexical, String datatype) {
        return "\"" + lexical + "\"^^<" + XSD + datatype + ">";
    }

    static String line(String s, String p, String o) {
        return iri(s) + " " + iri(p) + " " + o + " .";
    }

    StepTrig graph(String name, String... lines) {
        graphs.computeIfAbsent(name, k -> new ArrayList<>()).addAll(List.of(lines));
        return this;
    }

    StepTrig payload(String key, String... lines) {
        payloads.computeIfAbsent(key, k -> new ArrayList<>()).addAll(List.of(lines));
        return this;
    }

    StepTrig param(String name, String value) {
        parameters.put(name, value);
        return this;
    }

    StepTrig operation(String name) {
        this.operation = name;
        return this;
    }

    private List<String> stepLines() {
        String s = iri("urn:lattice:studio:step");
        List<String> out = new ArrayList<>();
        out.add(s + " a " + iri(CST + "SimulationStepRequest") + " .");
        if (targetClass != null) {
            out.add(line("urn:lattice:studio:step", CST + "forClass", iri(targetClass)));
        }
        if (operation != null) {
            out.add(line("urn:lattice:studio:step", CST + "operation", "\"" + operation + "\""));
        }
        if (time != null) {
            out.add(line("urn:lattice:studio:step", CST + "transactionTime", typed(time, "dateTime")));
        }
        int i = 0;
        for (Map.Entry<String, String> p : parameters.entrySet()) {
            String node = "_:p" + i++;
            out.add(s + " " + iri(CST + "parameter") + " " + node + " .");
            out.add(node + " " + iri(CST + "parameterName") + " \"" + p.getKey() + "\" .");
            out.add(node + " " + iri(CST + "parameterValue") + " \"" + p.getValue() + "\" .");
        }
        out.addAll(extraStepLines);
        return out;
    }

    /** The TriG, with the blocks and the lines in the order the seed gives, or the order they were added in for seed 0. */
    String text(long seed) {
        Map<String, List<String>> all = new LinkedHashMap<>(graphs);
        all.put("urn:lattice:studio:step", stepLines());
        payloads.forEach((key, lines) -> all.put(key.isEmpty() ? "urn:lattice:studio:step/payload" : "urn:lattice:studio:step/payload/" + key, lines));
        List<String> blocks = new ArrayList<>();
        Random random = new Random(seed);
        for (Map.Entry<String, List<String>> g : all.entrySet()) {
            List<String> lines = new ArrayList<>(g.getValue());
            if (seed == 0) {
                blocks.add(block(g.getKey(), lines));
                continue;
            }
            Collections.shuffle(lines, random);
            int cut = lines.size() / 2;
            blocks.add(block(g.getKey(), lines.subList(0, cut)));
            blocks.add(block(g.getKey(), lines.subList(cut, lines.size())));
        }
        if (seed != 0) {
            Collections.shuffle(blocks, random);
        }
        return String.join("\n", blocks);
    }

    String text() {
        return text(0);
    }

    private static String block(String graph, List<String> lines) {
        return graph.isEmpty() ? String.join("\n", lines) : "GRAPH " + iri(graph) + " {\n" + String.join("\n", lines) + "\n}";
    }

    // ---- the facility world of the sample

    /** The aggregate the replace sample stores, as N-Triples lines. */
    static List<String> aggregate(String margin) {
        String d = EX + "drawdown-1";
        return List.of(
            line(ROOT, "http://www.w3.org/1999/02/22-rdf-syntax-ns#type", iri(EX + "Facility")),
            line(ROOT, EX + "facilityReference", "\"FAC-2026-001\""),
            line(ROOT, EX + "arrangedBy", iri(EX + "branch-london")),
            line(ROOT, EX + "borrower", iri(EX + "acme-foods")),
            line(ROOT, EX + "lender", iri(EX + "lender-north")),
            line(ROOT, EX + "margin", typed(margin, "decimal")),
            line(ROOT, EX + "hasDrawdown", iri(d)),
            line(d, "http://www.w3.org/1999/02/22-rdf-syntax-ns#type", iri(EX + "Drawdown")),
            line(d, EX + "drawnUnder", iri(ROOT)),
            line(d, EX + "drawnAmount", typed("40000000.0", "decimal")));
    }

    /** The dataset at epoch 1 and the facility stored at {@code seq}, beside a facility that is not the step's. */
    static StepTrig stored(long seq) {
        StepTrig t = new StepTrig();
        t.graph("urn:g:dataset", line("urn:g:dataset", PAT + "epoch", typed("1", "long")));
        t.graph("urn:g:meta/6", line(ROOT, PAT + "epoch", typed("1", "long")), line(ROOT, PAT + "seq", typed(Long.toString(seq), "long")),
            line(ROOT, PAT + "head", iri("urn:rev:facility-1/" + seq)));
        t.graph("urn:g:facilities", aggregate("3.25").toArray(String[]::new));
        t.graph("urn:g:facilities", line(EX + "facility-2", EX + "margin", typed("4.0", "decimal")));
        return t;
    }

    /** The dataset at epoch 1 and no facility. */
    static StepTrig empty() {
        return new StepTrig().graph("urn:g:dataset", line("urn:g:dataset", PAT + "epoch", typed("1", "long")));
    }
}
