// SPDX-License-Identifier: MPL-2.0
// Track C1 smoke test (formal-methods-track-c.md plan, slice C1).
// Confirms the Alloy Analyzer JAR runs headlessly under this host's Java 25
// via `exec`, and that a satisfiable and an unsatisfiable run are told apart.

sig A {}

// Expected: satisfiable, an instance is found.
run Possible { some A } for 3

// Expected: unsatisfiable, no instance is found -- "some A and no A" can
// never hold.
run Impossible { some A and no A } for 3
