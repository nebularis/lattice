<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: AOR-3, versioning guarantees

**Unit:** [`applied-ontology-readiness`](../status/applied-ontology-readiness.md)
**Plan section:** [AOR-3](../plans/applied-ontology-readiness.md#aor-3-versioning-guarantees)
**Decision:** [ADR-A86 proposed addendum](../../architecture/decisions/ADR-A86-ontology-semantic-versioning.md#proposed-addendum-2026-09-25-guarantees-consumers-rely-on), items 1 to 3

## Invariant

A version IRI identifies one content of its document. Every published
ontology document (under `spec/` or `vocab/`) carries one, and a content change
never lands under an unchanged version IRI.

## Test cases

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| AOR3-01 | spec document content changed, version unchanged / check / flagged | L1 | - |
| AOR3-02 | content and version changed together / check / passes | L1 | + |
| AOR3-03 | untouched repository / both checks / pass | L1 | + |
| AOR3-04 | spec document without a version IRI / unversioned check / flagged | L1 | - |
| AOR3-05 | new vocab document without a version IRI / unversioned check / flagged | L1 | - |
| AOR3-06 | example document without a version IRI, content changed / both checks / pass | L1 | + |
| AOR3-07 | new spec document with a version IRI / both checks / pass | L1 | + |

Each test builds a throwaway git repository as its base ref.

## One command

```bash
mise run check:ontology-versioning
```

Pass: `7 passed`, then `33 in-scope ontology document(s) checked against HEAD:
no unbumped changes`.

## Artefacts to inspect

- `tools/ontology_version_check.py`: `requires_version_iri` and
  `check_unversioned`, and the `UNVERSIONED` report line.
- `.github/workflows/platform.yml`: full-history checkout, the two new test
  modules, and the check against `origin/main`.
- `pyproject.toml`: new `test` extra declaring `pytest`, installed by
  `bootstrap:python-root` and the workflow. Before this, `pytest` reached the
  root environment only through other tool packages.
- `docs/architecture/ontology-versioning-policy.md`: cascade for every bump,
  import-only changes take the imported level, enforcement scope.

## Adversarial probe (run by the agent)

Replacing `requires_version_iri`'s body with `return False` failed AOR3-04 and
AOR3-05. Disabling the unchanged-version comparison failed AOR3-01. Restoring
the file returned 7 passes.

## Deviations from the plan

- **Job-family regeneration deferred.** The Surface compiler stamps every
  generated module with `owl:versionIRI <module>/0.0.1`
  (`tools/surface/src/surface/compile.py`, `_ontology_header`). Regenerating
  the four modules under `ontology/surface/execution/job-family/` would change
  their content under an unchanged version IRI, which this slice's own check
  rejects. How generated documents are versioned needs a decision. See the
  status record.
- **CI is manual-only.** Both workflows run on `workflow_dispatch` only, so the
  CI step guards a dispatched branch against `origin/main`, not every change.

## Deliberate non-coverage

- Ontology IRIs versus the version-IRI base (addendum item 4).
- Import resolution (AOR-4).
