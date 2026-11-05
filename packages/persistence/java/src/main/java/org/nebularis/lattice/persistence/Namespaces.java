// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.persistence;

/** The namespaces of a compiled profile and of the patterns vocabulary (ADR-A132 decision 3). */
public final class Namespaces {
    private Namespaces() {}

    public static final String DAL = "https://www.nebularis.org/neuro-semantic/lattice/persistence#";
    public static final String PAT = "https://www.nebularis.org/neuro-semantic/lattice/persistence-store#";
    public static final String RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type";
    public static final String XSD_STRING = "http://www.w3.org/2001/XMLSchema#string";
    public static final String XSD_LONG = "http://www.w3.org/2001/XMLSchema#long";
}
