// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.persistence;

import java.util.Set;

/**
 * What the caller says of the version it appends under delta membership: the domain's membership property, the members the version has once
 * its changes are applied, and whether it is a checkpoint (ADR-A132 decision 2).
 */
public record Membership(Iri property, Set<Iri> members, boolean checkpoint) {
    public Membership {
        members = Set.copyOf(members);
    }
}
