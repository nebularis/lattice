// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.jobs;

import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.Resource;
import org.nebularis.lattice.studio.store.Cst;

/**
 * Which queue a job goes to. A job that takes minutes, above all a proposal that waits on a language model, goes to the long queue, whose
 * own worker runs it, so the short jobs an author waits on while editing, validations and compilations, are never behind it. A rebuild, an
 * assembly and every other job are short. The kinds that are long are this one list, and the worker needs no copy of it, since a worker
 * runs whatever its queue gives it.
 */
public final class Lanes {
    private Lanes() {
    }

    /** Whether the job described by {@code description} is long: a proposal by a language model, or a publication. */
    public static boolean isLong(Model description, String jobIri) {
        Resource job = description.createResource(jobIri);
        if (description.contains(job, Cst.kind, Cst.Publish)) {
            return true;
        }
        return description.contains(job, Cst.kind, Cst.Propose)
            && (description.contains(job, Cst.target, Cst.LanguageModelProposer) || description.contains(job, Cst.target, Cst.MappingLanguageModelProposer));
    }

    /** The routing key of the queue for the job. */
    public static String routingKey(boolean longJob) {
        return longJob ? Topology.JOBS_LONG_ROUTING_KEY : Topology.JOBS_ROUTING_KEY;
    }
}
