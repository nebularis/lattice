// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.store;

public record DocumentView(String documentId, String title, String templateId, int latestRevision) {
}
