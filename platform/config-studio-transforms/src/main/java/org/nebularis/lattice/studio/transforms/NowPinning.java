// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.transforms;

import org.apache.jena.graph.Node;
import org.apache.jena.query.Query;
import org.apache.jena.sparql.expr.E_Now;
import org.apache.jena.sparql.expr.Expr;
import org.apache.jena.sparql.expr.ExprFunction0;
import org.apache.jena.sparql.expr.ExprTransformCopy;
import org.apache.jena.sparql.expr.NodeValue;
import org.apache.jena.sparql.syntax.syntaxtransform.ElementTransformCopyBase;
import org.apache.jena.sparql.syntax.syntaxtransform.QueryTransformOps;
import org.apache.jena.sparql.syntax.syntaxtransform.UpdateTransformOps;
import org.apache.jena.update.UpdateRequest;

/**
 * Replaces every {@code NOW()} of a parsed update with a stated time, so a step reads no clock (PRI-56). Jena sets the time {@code NOW()}
 * returns again for each operation of a request, whatever the execution or the dataset states, so a time cannot be handed to the engine
 * and has to be put in the request (TSD-76, probe {@code NowPinningProbeTest}). The replacement is Jena's own expression
 * and update transform over the parsed request, in every operation, in {@code WHERE}, {@code BIND}, {@code FILTER}, in an expression of
 * a nested group or of a {@code NOT EXISTS}, and never an edit of the SPARQL text.
 */
final class NowPinning {
    private NowPinning() {
    }

    /** What the transform did to a request. */
    record Pinned(UpdateRequest request, int replaced) {
    }

    private static final class Replace extends ExprTransformCopy {
        private final Expr time;
        int replaced;

        Replace(Node time) {
            super(COPY_ONLY_ON_CHANGE);
            this.time = NodeValue.makeNode(time);
        }

        @Override
        public Expr transform(ExprFunction0 func) {
            if (func instanceof E_Now) {
                replaced++;
                return time;
            }
            return super.transform(func);
        }
    }

    /** {@code request} with each {@code NOW()} replaced by the {@code xsd:dateTime} constant {@code time}. */
    static Pinned pin(UpdateRequest request, Node time) {
        Replace replace = new Replace(time);
        UpdateRequest out = UpdateTransformOps.transform(request, new ElementTransformCopyBase(false), replace);
        return new Pinned(out, replace.replaced);
    }

    private static final class Count extends ExprTransformCopy {
        int found;

        @Override
        public Expr transform(ExprFunction0 func) {
            if (func instanceof E_Now) {
                found++;
            }
            return super.transform(func);
        }
    }

    /** How many {@code NOW()} a request still holds, which is none after {@link #pin}. */
    static int remaining(UpdateRequest request) {
        Count count = new Count();
        UpdateTransformOps.transform(request, new ElementTransformCopyBase(false), count);
        return count.found;
    }

    /** How many {@code NOW()} a query holds, for the reads a profile compiles beside its writes. */
    static int remaining(Query query) {
        Count count = new Count();
        QueryTransformOps.transform(query, new ElementTransformCopyBase(false), count);
        return count.found;
    }
}
