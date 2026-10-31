// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.writer;

import java.io.IOException;
import java.io.OutputStream;
import java.io.PrintStream;
import java.io.UncheckedIOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Clock;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SortedSet;
import java.util.regex.Pattern;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.Resource;
import org.apache.jena.riot.Lang;
import org.apache.jena.riot.RDFDataMgr;
import org.apache.jena.update.Update;
import org.apache.jena.update.UpdateRequest;
import org.apache.jena.vocabulary.RDF;
import org.nebularis.lattice.studio.model.Workspace;
import org.nebularis.lattice.studio.store.Cst;
import org.nebularis.lattice.studio.store.Graphs;
import org.nebularis.lattice.studio.store.Skolem;
import org.nebularis.lattice.studio.store.StudioOperations;
import org.nebularis.lattice.studio.store.StudioOperations.Family;
import org.nebularis.lattice.studio.store.StudioStore;

/**
 * Moves a store written before phase D onto the generated persistence operations, in place. It backs the dataset up first, then
 * moves each old workspace in one request, so a workspace moves whole or not at all, then the registry, then the imports no
 * workspace held. It is idempotent, since it moves only what it finds in the old layout and skips what already has a row.
 */
public final class Migration {
    private static final Pattern WORKSPACE_GRAPH = Pattern.compile(Pattern.quote(Graphs.WORKSPACE_PREFIX)
        + "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}");
    private static final Pattern LINEAGE_GRAPH = Pattern.compile("urn:lattice:studio:pub:[0-9a-f]{32}");
    private static final Pattern VERSION_GRAPH = Pattern.compile("urn:lattice:studio:pub:[0-9a-f]{32}:rev:[0-9a-f]{16}");
    private static final DateTimeFormatter STAMP = DateTimeFormatter.ofPattern("yyyyMMdd'T'HHmmss'Z'").withZone(ZoneOffset.UTC);

    /** What a run moved, or with a dry run would move. */
    public record Summary(int workspaces, int parts, int revisions, int documents, int imports, int lineages, int versions,
                          int graphsDropped, List<String> skipped, Path backup) {
    }

    private final StudioStore store;
    private final StudioOperations ops;
    private final Path assets;
    private final Clock clock;
    private final PrintStream out;

    private int workspaces;
    private int parts;
    private int revisions;
    private int documents;
    private int imports;
    private int lineages;
    private int versions;
    private int dropped;
    private final List<String> skipped = new ArrayList<>();
    private final Set<String> importsCreated = new HashSet<>();
    private SortedSet<String> names;

    public Migration(StudioStore store, StudioOperations ops, Path assets, Clock clock, PrintStream out) {
        this.store = store;
        this.ops = ops;
        this.assets = assets;
        this.clock = clock;
        this.out = out;
    }

    /** With {@code dryRun}, nothing is written to the store or to disk, and every request is still built, so a graph it cannot move is reported. */
    public Summary run(boolean dryRun) {
        names = store.graphNames();
        List<String> pending = new ArrayList<>();
        for (String g : names) {
            if (WORKSPACE_GRAPH.matcher(g).matches() && isOldWorkspace(g)) {
                pending.add(g);
            }
        }
        boolean oldRegistry = names.stream().anyMatch(g -> LINEAGE_GRAPH.matcher(g).matches() || VERSION_GRAPH.matcher(g).matches());
        boolean oldImports = names.stream().anyMatch(Graphs::isImportGraph);
        Path backup = null;
        if (!pending.isEmpty() || oldRegistry || oldImports) {
            backup = backup(dryRun);
            for (String g : pending) {
                workspace(g.substring(Graphs.WORKSPACE_PREFIX.length()), dryRun);
            }
            registry(dryRun);
            strayImports(dryRun);
        } else {
            out.println("Nothing to migrate");
        }
        return new Summary(workspaces, parts, revisions, documents, imports, lineages, versions, dropped, List.copyOf(skipped), backup);
    }

    /** An old description graph is its node's IRI and holds {@code cst:Workspace}, with no description in the new layout. */
    private boolean isOldWorkspace(String graph) {
        return store.graph(graph).contains(store.graph(graph).createResource(graph), RDF.type, Cst.Workspace)
            && ops.seq(store, Family.DESCRIPTION, graph).isEmpty();
    }

    private Path backup(boolean dryRun) {
        Path file = assets.resolve("migration-backup-" + STAMP.format(clock.instant()) + ".trig");
        if (dryRun) {
            out.println("Would back up " + names.size() + " graphs to " + file);
            return file;
        }
        try {
            Files.createDirectories(assets);
            try (OutputStream o = Files.newOutputStream(file)) {
                RDFDataMgr.write(o, store.snapshot(), Lang.TRIG);
            }
        } catch (IOException e) {
            throw new UncheckedIOException("cannot write the backup " + file + ", so nothing was migrated", e);
        }
        out.println("Backed up " + names.size() + " graphs to " + file);
        return file;
    }

    /** One request: the baseline's history, the parts, the documents, the held imports, then the description, then the drops. */
    private void workspace(String id, boolean dryRun) {
        String root = Graphs.workspace(id);
        Model old = store.graph(root);
        Workspace ws = Workspace.from(id, old);
        if (ws == null) {
            skipped.add(root + " has a description the studio cannot read");
            return;
        }
        Request r = new Request("urn:txn:migrate/" + id + "/");
        int revs = old.contains(old.createResource(root), Cst.baselineRevision)
            ? Math.max(1, old.getProperty(old.createResource(root), Cst.baselineRevision).getInt()) : 1;
        String baseline = Graphs.partRoot(id, "baseline");
        Model previous = null;
        for (int k = 1; k <= revs; k++) {
            String oldGraph = root + ":baseline:" + k;
            Model now = Skolem.skolemise(store.graph(oldGraph));
            r.add(k == 1 ? ops.create(Family.PART, baseline, now, r.txn())
                : ops.replaceLinear(Family.PART, baseline, k - 1, now, now.difference(previous), previous.difference(now), r.txn()));
            r.drop(oldGraph);
            previous = now;
        }
        int movedParts = 0;
        for (String name : Workspace.CONFIGS) {
            String oldGraph = root + ":" + name;
            Model m = store.graph(oldGraph);
            if (!m.isEmpty()) {
                r.add(ops.create(Family.PART, Graphs.partRoot(id, name), Skolem.skolemise(m), r.txn()));
                movedParts++;
            }
            r.drop(oldGraph);
        }
        for (String doc : ws.documents().keySet()) {
            String oldGraph = Graphs.document(id, doc);
            r.add(ops.create(Family.DOCUMENT, oldGraph, Skolem.skolemise(store.graph(oldGraph)), r.txn()));
            r.drop(oldGraph);
        }
        int movedImports = 0;
        for (String imported : ws.imports().keySet()) {
            Model m = store.graph(imported);
            if (!m.isEmpty() && !importsCreated.contains(imported) && ops.seq(store, Family.IMPORT, imported).isEmpty()) {
                r.add(ops.create(Family.IMPORT, imported, Skolem.skolemise(m), r.txn()));
                importsCreated.add(imported);
                movedImports++;
            }
        }
        r.add(ops.create(Family.DESCRIPTION, root, Skolem.skolemise(ws.stored()), r.txn()));
        r.drop(root);
        // A job names old graphs and is coordination data (PRI-52), so it goes. The workspace's receipts stay.
        store.jobGraphsOf(root).listSubjects().forEachRemaining(job -> {
            String j = job.getURI();
            String id2 = j.substring(Graphs.JOB_PREFIX.length());
            r.drop(j);
            r.drop(Graphs.jobInput(id2));
            r.drop(Graphs.jobRecord(id2));
            r.drop(Graphs.jobReceipts(id2));
        });
        send(r, dryRun);
        workspaces++;
        parts += movedParts;
        revisions += revs;
        documents += ws.documents().size();
        imports += movedImports;
        out.println("Workspace " + id + " " + (dryRun ? "would move" : "moved") + ": " + revs + " baseline revisions, " + movedParts
            + " parts, " + ws.documents().size() + " documents, " + movedImports + " imports");
    }

    /** One request: each version, each lineage, then the old graphs dropped. */
    private void registry(boolean dryRun) {
        Request r = new Request("urn:txn:migrate/registry/");
        int movedVersions = 0;
        int movedLineages = 0;
        for (String g : names) {
            if (VERSION_GRAPH.matcher(g).matches()) {
                Model m = store.graph(g);
                List<Resource> found = m.listSubjectsWithProperty(Cst.Fnd.hasIdentity).toList();
                if (found.size() != 1 || !found.get(0).isURIResource()) {
                    skipped.add(g + " is a version graph without exactly one version");
                    continue;
                }
                String version = found.get(0).getURI();
                if (ops.seq(store, Family.VERSION, version).isEmpty()) {
                    r.add(ops.create(Family.VERSION, version, Skolem.skolemise(m), r.txn()));
                    movedVersions++;
                }
                r.drop(g);
            }
        }
        for (String g : names) {
            if (LINEAGE_GRAPH.matcher(g).matches()) {
                Model m = store.graph(g);
                List<Resource> found = m.listSubjectsWithProperty(RDF.type, Cst.Fnd.PersistentIdentity).toList();
                if (found.size() != 1 || !found.get(0).isURIResource()) {
                    skipped.add(g + " is a lineage graph without exactly one lineage");
                    continue;
                }
                String lineage = found.get(0).getURI();
                if (ops.seq(store, Family.LINEAGE, lineage).isEmpty()) {
                    r.add(ops.create(Family.LINEAGE, lineage, Skolem.skolemise(m), r.txn()));
                    movedLineages++;
                }
                r.drop(g);
            }
        }
        if (r.empty()) {
            return;
        }
        send(r, dryRun);
        versions += movedVersions;
        lineages += movedLineages;
        out.println("Registry " + (dryRun ? "would move" : "moved") + ": " + movedLineages + " lineages, " + movedVersions + " versions");
    }

    /** The imports no workspace held, and then every old import graph dropped, since each has been moved or was empty. */
    private void strayImports(boolean dryRun) {
        Request r = new Request("urn:txn:migrate/imports/");
        int moved = 0;
        for (String g : names) {
            if (Graphs.isImportGraph(g)) {
                Model m = store.graph(g);
                if (!m.isEmpty() && !importsCreated.contains(g) && ops.seq(store, Family.IMPORT, g).isEmpty()) {
                    r.add(ops.create(Family.IMPORT, g, Skolem.skolemise(m), r.txn()));
                    importsCreated.add(g);
                    moved++;
                }
                r.drop(g);
            }
        }
        if (r.empty()) {
            return;
        }
        send(r, dryRun);
        imports += moved;
        out.println("Imports " + (dryRun ? "would move" : "moved") + ": " + moved + " not held by a workspace");
    }

    private void send(Request r, boolean dryRun) {
        dropped += r.drops.stream().filter(names::contains).count();
        if (!dryRun) {
            r.drops.forEach(g -> r.request.add(StudioStore.drop(g)));
            store.update(r.request);
        }
    }

    /** The operations of one request, each in a transaction of its own, then the drops. */
    private static final class Request {
        final UpdateRequest request = new UpdateRequest();
        final Set<String> drops = new java.util.LinkedHashSet<>();
        private final String prefix;
        private int n;

        Request(String prefix) {
            this.prefix = prefix;
        }

        String txn() {
            return prefix + (++n);
        }

        void add(List<Update> updates) {
            updates.forEach(request::add);
        }

        void drop(String graph) {
            drops.add(graph);
        }

        boolean empty() {
            return request.getOperations().isEmpty() && drops.isEmpty();
        }
    }
}
