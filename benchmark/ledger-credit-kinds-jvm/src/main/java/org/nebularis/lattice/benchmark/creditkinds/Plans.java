// SPDX-License-Identifier: MPL-2.0
// NB: This module has been produced using GenAI
package org.nebularis.lattice.benchmark.creditkinds;

import static org.nebularis.lattice.benchmark.creditkinds.CreditKinds.ACCTS;
import static org.nebularis.lattice.benchmark.creditkinds.CreditKinds.num;

import java.util.ArrayList;
import java.util.List;

import org.apache.jena.atlas.json.JsonObject;
import org.apache.jena.query.Dataset;
import org.apache.jena.query.Query;
import org.apache.jena.query.QueryFactory;
import org.apache.jena.sparql.algebra.Algebra;
import org.apache.jena.sparql.algebra.Op;
import org.apache.jena.sparql.algebra.Transformer;
import org.apache.jena.sparql.algebra.op.OpBGP;
import org.apache.jena.sparql.algebra.op.OpQuadPattern;
import org.apache.jena.sparql.algebra.TransformCopy;
import org.apache.jena.sparql.engine.optimizer.reorder.ReorderTransformation;
import org.apache.jena.tdb2.store.DatasetGraphTDB;
import org.apache.jena.tdb2.sys.TDBInternal;

/**
 * What Jena will run for three reads of the root account at the largest two-level corpus: the kind-filtered fold in the OPTIONAL form, the same fold in the UNION form, and the cuts aggregate of the
 * sum with cuts. It prints the algebra as compiled, the algebra after ARQ's optimiser, and, for TDB2, its quad form and the triple order TDB2's own reordering gives. ARQ's execution logging goes
 * through SLF4J, which this module binds to a no-op logger, so the log is not available and the reordering is asked of the store directly.
 */
final class Plans {

    private Plans() {}

    /** The rows of a VALUES table are listed for the first two graphs and the last, the rest counted. */
    static String condense(String sse) {
        List<String> out = new ArrayList<>();
        List<String> rows = new ArrayList<>();
        for (String line : sse.split("\n")) {
            if (line.trim().startsWith("(row ")) {
                rows.add(line);
                continue;
            }
            flush(out, rows);
            out.add(line);
        }
        flush(out, rows);
        return String.join("\n", out);
    }

    private static void flush(List<String> out, List<String> rows) {
        if (rows.size() > 3) {
            out.add(rows.get(0));
            out.add(rows.get(1));
            out.add(rows.get(0).substring(0, rows.get(0).indexOf('(')) + "... " + (rows.size() - 3) + " more rows");
            out.add(rows.get(rows.size() - 1));
        } else {
            out.addAll(rows);
        }
        rows.clear();
    }

    static void describe(StringBuilder out, Dataset ds, String engine, JsonObject corpus) {
        CreditKinds.Acct root = ACCTS.values().stream().filter(a -> a.level() == 3).findFirst().orElseThrow();
        int point = (int) num(corpus, "last");
        out.append("# Query plans, ").append(engine.equals("tdb2") ? "Jena TDB2" : "Jena in memory").append(", the root's full read of the ").append(num(corpus, "events")).append(" posting two-level corpus at ")
                .append(corpus.get("credit_share").getAsNumber().value()).append(" credits, as of position ").append(point).append("\n\n");
        String[][] queries = {
            {"kind-filtered, OPTIONAL form", CreditKinds.PREFIX + "SELECT (SUM(?signed) AS ?sum) (COUNT(?p) AS ?folded) WHERE { " + CreditKinds.scan(root, point, true, "optional", 0, "") + " "
                    + CreditKinds.kindFilter(root) + " " + CreditKinds.SIGNED + " }"},
            {CreditKinds.UNION_FOLD, CreditKinds.unionText(root, point, 0)},
            {"cuts aggregate of the sum with cuts", CreditKinds.cutsText(root, point, 0)}};
        ReorderTransformation reorder = null;
        if (engine.equals("tdb2")) {
            DatasetGraphTDB tdb = TDBInternal.getDatasetGraphTDB(ds.asDatasetGraph());
            reorder = tdb.getReorderTransform();
            out.append("TDB2 reordering transformation: ").append(reorder.getClass().getName()).append("\n\n");
        }
        for (String[] q : queries) {
            Query query = QueryFactory.create(q[1]);
            Op compiled = Algebra.compile(query);
            Op optimized = Algebra.optimize(compiled);
            out.append("## ").append(q[0]).append("\n\n### compiled\n\n").append(condense(compiled.toString())).append("\n\n### optimised by ARQ\n\n").append(condense(optimized.toString())).append("\n\n");
            if (reorder != null) {
                Op quad = Algebra.toQuadForm(optimized);
                out.append("### quad form, as TDB2 takes it\n\n").append(condense(quad.toString())).append("\n\n");
                final ReorderTransformation r = reorder;
                Op ordered = Transformer.transform(new TransformCopy() {
                    @Override
                    public Op transform(OpBGP op) {
                        return new OpBGP(r.reorder(op.getPattern()));
                    }

                    @Override
                    public Op transform(OpQuadPattern op) {
                        return new OpQuadPattern(op.getGraphNode(), r.reorder(op.getBasicPattern()));
                    }
                }, quad);
                out.append("### with TDB2's pattern order\n\n").append(condense(ordered.toString())).append("\n\n");
            }
        }
    }
}
