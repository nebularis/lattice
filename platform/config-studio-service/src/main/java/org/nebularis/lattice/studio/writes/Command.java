// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.writes;

import java.time.Instant;
import org.apache.jena.query.Dataset;
import org.apache.jena.query.DatasetFactory;
import org.apache.jena.rdf.model.Model;

/**
 * One write to the store, as the service or the worker asks the workspace's writer to make it. Every write names the
 * workspace it belongs to, which is the key that routes it to one writer. The graphs it carries are in {@code body}: the
 * default graph for the one graph a creation or a save carries, named graphs for an import, a job's submission and a
 * job's update. The fields a type does not use are null.
 */
public record Command(Type type, String workspace, String job, String part, Long expect, Instant at, String label,
                      String sample, Dataset body) {

    public enum Type {
        CREATE("create"), SAVE("save"), IMPORT("import"), DELETE_WORKSPACE("delete-workspace"),
        SUBMIT_JOB("submit-job"), JOB_UPDATE("job-update"), DELETE_JOB("delete-job");

        public final String wire;

        Type(String wire) {
            this.wire = wire;
        }

        static Type of(String wire) {
            for (Type t : values()) {
                if (t.wire.equals(wire)) {
                    return t;
                }
            }
            return null;
        }
    }

    public static Command create(String ws, String label, Instant at, String sample, Model baseline) {
        return new Command(Type.CREATE, ws, null, null, null, at, label, sample, withDefault(baseline));
    }

    public static Command save(String ws, String part, long expect, Instant at, Model graph) {
        return new Command(Type.SAVE, ws, null, part, expect, at, null, null, withDefault(graph));
    }

    public static Command importing(String ws, Instant at, String label, Dataset graphs) {
        return new Command(Type.IMPORT, ws, null, null, null, at, label, null, graphs);
    }

    public static Command deleteWorkspace(String ws) {
        return new Command(Type.DELETE_WORKSPACE, ws, null, null, null, null, null, null, DatasetFactory.create());
    }

    public static Command submitJob(String ws, String job, Dataset graphs) {
        return new Command(Type.SUBMIT_JOB, ws, job, null, null, null, null, null, graphs);
    }

    public static Command jobUpdate(String ws, String job, Dataset graphs) {
        return new Command(Type.JOB_UPDATE, ws, job, null, null, null, null, null, graphs);
    }

    public static Command deleteJob(String ws, String job) {
        return new Command(Type.DELETE_JOB, ws, job, null, null, null, null, null, DatasetFactory.create());
    }

    private static Dataset withDefault(Model model) {
        Dataset d = DatasetFactory.create();
        d.getDefaultModel().add(model);
        return d;
    }
}
