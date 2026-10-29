// SPDX-License-Identifier: MPL-2.0
// NB: This module has been produced using GenAI

package org.nebularis.lattice.benchmark.graphnaming;

import org.eclipse.rdf4j.query.QueryLanguage;
import org.eclipse.rdf4j.query.TupleQueryResult;
import org.eclipse.rdf4j.repository.Repository;
import org.eclipse.rdf4j.repository.RepositoryConnection;
import org.eclipse.rdf4j.repository.sail.SailRepository;
import org.eclipse.rdf4j.sail.memory.MemoryStore;

/**
 * The probe behind TSD-48: what {@code COUNT(*)} gives over a pattern with no variable that matches. SPARQL 1.1 evaluates such a pattern to one empty solution,
 * so the count is 1. Run it with {@code mvn -q -f benchmark/persistence-graph-naming-cost-jvm/pom.xml compile exec:exec -Dexec.mainClass=org.nebularis.lattice.benchmark.graphnaming.Rdf4jCountProbe}.
 */
public final class Rdf4jCountProbe {

    public static void main(String[] args) {
        Repository repository = new SailRepository(new MemoryStore());
        repository.init();
        try (RepositoryConnection connection = repository.getConnection()) {
            connection.prepareUpdate(QueryLanguage.SPARQL, "INSERT DATA { GRAPH <urn:g> { <urn:s> <urn:p> \"v2\" } }").execute();
            String[] queries = {
                "SELECT (COUNT(*) AS ?n) WHERE { GRAPH <urn:g> { <urn:s> <urn:p> \"v2\" } }",
                "SELECT (COUNT(*) AS ?n) WHERE { GRAPH <urn:g> { <urn:s> <urn:p> ?o FILTER(?o = \"v2\") } }",
                "SELECT (COUNT(*) AS ?n) WHERE { GRAPH <urn:g> { <urn:s> <urn:p> \"absent\" } }",
                "SELECT (COUNT(*) AS ?n) WHERE { <urn:s> <urn:p> \"v2\" }"};
            for (String query : queries) {
                try (TupleQueryResult result = connection.prepareTupleQuery(QueryLanguage.SPARQL, query).evaluate()) {
                    System.out.println(query + "  ->  " + (result.hasNext() ? result.next().getValue("n").stringValue() : "no row"));
                }
            }
        }
        repository.shutDown();
    }

    private Rdf4jCountProbe() {
    }
}
