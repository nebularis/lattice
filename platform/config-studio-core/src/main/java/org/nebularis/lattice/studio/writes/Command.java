// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.writes;

import java.time.Instant;
import java.util.UUID;
import org.apache.jena.query.Dataset;
import org.apache.jena.query.DatasetFactory;
import org.apache.jena.rdf.model.Model;

/**
 * One write to the store, as the service or the worker asks the workspace's writer to make it. Every write names the
 * workspace it belongs to, which is the key that routes it to one writer. A refresh job's writes name none and route by the job's own id. The graphs it carries are in {@code body}: the
 * default graph for the one graph a creation or a save carries, named graphs for an import, a job's submission and a
 * job's update. The fields a type does not use are null. {@code id} names the command, so its receipt names it and a
 * redelivered command is applied once, and {@code sender} says which component sent it, unauthenticated (TD-99). {@code
 * principal} names who asked for it, as the service authenticated them, and {@code admin} whether they administer the
 * studio, both null and false for a write the worker makes for a job (PRI-54, ADR-A149 decision 8).
 */
public record Command(String id, String sender, Type type, String workspace, String job, String part, Long expect,
                      Instant at, String label, String sample, Dataset body, String principal, boolean admin) {
    public static final String SERVICE = "service";

    public enum Type {
        CREATE("create"), SAVE("save"), IMPORT("import"), DELETE_WORKSPACE("delete-workspace"),
        SAVE_DOCUMENT("save-document"), DELETE_DOCUMENT("delete-document"), SUBMIT_JOB("submit-job"), JOB_UPDATE("job-update"),
        DELETE_JOB("delete-job"), SET_ACCESS("set-access"), PUBLISH("publish"),
        SET_DEPENDENCIES("set-dependencies"), FENCE("fence"), RELEASE("release");

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
        return new Command(newId(), SERVICE, Type.CREATE, ws, null, null, null, at, label, sample, withDefault(baseline), null, false);
    }

    public static Command save(String ws, String part, long expect, Instant at, Model graph) {
        return new Command(newId(), SERVICE, Type.SAVE, ws, null, part, expect, at, null, null, withDefault(graph), null, false);
    }

    /** {@code title} is the document's, and {@code template} its template's key, carried as the command's label and sample. */
    public static Command saveDocument(String ws, String doc, long expect, Instant at, String title, String template, Model graph) {
        return new Command(newId(), SERVICE, Type.SAVE_DOCUMENT, ws, null, doc, expect, at, title, template, withDefault(graph), null, false);
    }

    public static Command deleteDocument(String ws, String doc) {
        return new Command(newId(), SERVICE, Type.DELETE_DOCUMENT, ws, null, doc, null, null, null, null, DatasetFactory.create(), null, false);
    }

    public static Command importing(String ws, Instant at, String label, Dataset graphs) {
        return new Command(newId(), SERVICE, Type.IMPORT, ws, null, null, null, at, label, null, graphs, null, false);
    }

    public static Command deleteWorkspace(String ws) {
        return new Command(newId(), SERVICE, Type.DELETE_WORKSPACE, ws, null, null, null, null, null, null, DatasetFactory.create(), null, false);
    }

    public static Command submitJob(String ws, String job, Dataset graphs) {
        return new Command(newId(), SERVICE, Type.SUBMIT_JOB, ws, job, null, null, null, null, null, graphs, null, false);
    }

    public static Command jobUpdate(String ws, String job, Dataset graphs) {
        return new Command(newId(), SERVICE, Type.JOB_UPDATE, ws, job, null, null, null, null, null, graphs, null, false);
    }

    /** {@code mode} is one of {@code Workspace.MODES}, and {@code owner} the new owner or null to keep it. */
    public static Command setAccess(String ws, String mode, String owner) {
        return new Command(newId(), SERVICE, Type.SET_ACCESS, ws, null, mode, null, null, owner, null, DatasetFactory.create(), null, false);
    }

    /** {@code content} is the version's graph, carried as the default graph. The lineage rides as the part and the version as the label. */
    public static Command publish(String ws, String lineage, String version, Model content) {
        return new Command(newId(), SERVICE, Type.PUBLISH, ws, null, lineage, null, null, version, null, withDefault(content), null, false);
    }

    /** {@code body} holds {@code <ws> cst:dependsOn <iri>} for each dependency, in the default graph. */
    public static Command setDependencies(String ws, Model body) {
        return new Command(newId(), SERVICE, Type.SET_DEPENDENCIES, ws, null, null, null, null, null, null, withDefault(body), null, false);
    }

    /** The imported graph rides as the default graph, its digest as the part and its label as the label. */
    public static Command fence(String ws, String digest, String label, Model content) {
        return new Command(newId(), SERVICE, Type.FENCE, ws, null, digest, null, null, label, null, withDefault(content), null, false);
    }

    /** The workspace stops holding the import graph of {@code digest}, which stays in the store. */
    public static Command release(String ws, String digest) {
        return new Command(newId(), SERVICE, Type.RELEASE, ws, null, digest, null, null, null, null, DatasetFactory.create(), null, false);
    }

    public static Command deleteJob(String ws, String job) {
        return new Command(newId(), SERVICE, Type.DELETE_JOB, ws, job, null, null, null, null, null, DatasetFactory.create(), null, false);
    }

    /** A refresh job's submission (ADR-A149 decision 14), which names no workspace. The job graph is its only graph. */
    public static Command submitRefresh(String job, Dataset graphs) {
        return new Command(newId(), SERVICE, Type.SUBMIT_JOB, null, job, null, null, null, null, null, graphs, null, false);
    }

    public static Command deleteRefresh(String job) {
        return new Command(newId(), SERVICE, Type.DELETE_JOB, null, job, null, null, null, null, null, DatasetFactory.create(), null, false);
    }

    /** The id that routes the write to its writer: the workspace's, or a refresh job's own, which names no workspace. */
    public String routingId() {
        return workspace != null ? workspace : job;
    }

    /** This command as {@code principal} asked for it. */
    public Command by(String principal, boolean admin) {
        return new Command(id, sender, type, workspace, job, part, expect, at, label, sample, body, principal, admin);
    }

    private static String newId() {
        return UUID.randomUUID().toString();
    }

    private static Dataset withDefault(Model model) {
        Dataset d = DatasetFactory.create();
        d.getDefaultModel().add(model);
        return d;
    }
}
