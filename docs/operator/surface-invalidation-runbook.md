<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Surface Layer — Invalidation and Regeneration Runbook

**Purpose:** Operational procedures for invalidation detection and minimal-scope regeneration  
**Status:** Phase 7 complete; depth-1 scope only  
**Last updated:** 2026-09-22

---

## Overview

When a source declaration changes (a concept is renamed, a scheme is rebound, an instance is asserted, or a surface is redefined), use this runbook to identify the smallest set of packages that require regeneration.

Uses canonical read-set digests and dependency edges to minimize impact. All procedures use APIs in `tools/surface/invalidation.py`.

**Scope:** Stack depth 1 only (promotion, single-level indexing, closure over one hierarchy). Deeper stacking and transitive freshness are deferred.

---

## Core Algorithm

```
1. Identify change source (declaration, scheme, instance, or surface)
2. Recompute current canonical digest for that source
3. Extract recorded digest from manifest (read-set entry)
4. Compare digests → determine invalidation scope
5. Plan minimal regeneration using dependency edges
6. Regenerate only affected surfaces
7. Recompile affected mappings and artefacts
8. Validate and replace atomically
9. Verify parity checks
```

---

## Scenario 1: Normal Source Change

**When to use:** A concept is renamed, merged, deprecated, or reindexed; a parent hierarchy changes; instance assertions change.

**Step 1: Recompute current digest**

```python
from rdflib import Graph
from surface.invalidation import compute_read_source_digest

# Load the changed source
g = Graph()
g.parse("path/to/changed/source.ttl")

# Compute current digest for the source IRI
source_iri = "http://example.org/concepts/Coverage_Cyber"
current_digest = compute_read_source_digest(g, source_iri)
print(f"Current digest: {current_digest}")
```

**Step 2: Extract recorded read-set**

```python
from surface.invalidation import read_set_from_manifest

# Load the generated surface package
manifest_g = Graph()
manifest_g.parse("ontology/surface/execution/my-contract/manifest.ttl")

# Extract all recorded read-set entries
read_set = read_set_from_manifest(manifest_g)

# Find entries for the source
for entry in read_set:
    if entry['readSource'] == source_iri:
        print(f"Recorded digest: {entry['readHash']}")
        print(f"Recorded version: {entry['readVersion']}")
        break
```

**Step 3: Compare digests**

```python
from surface.invalidation import compare_read_set

# Get all recorded entries
all_entries = read_set_from_manifest(manifest_g)

# Find which entries are stale
stale_entries = compare_read_set(all_entries, {'source_iri': current_digest})

if stale_entries:
    print(f"Surface is stale: {len(stale_entries)} entry/ies changed")
else:
    print("Surface is fresh; no regeneration needed")
```

**Step 4: Plan regeneration**

```python
from surface.invalidation import plan_regeneration

# Identify changed sources
changed_sources = [source_iri]

# Get the regeneration scope
surfaces, mappings, artefacts = plan_regeneration(
    changed_sources=changed_sources,
    changed_mappings=[],
    changed_profiles=[],
    graph=manifest_g
)

print(f"Surfaces to regenerate: {len(surfaces)}")
print(f"Mappings to recompile: {len(mappings)}")
print(f"Artefacts to replace: {len(artefacts)}")
```

**Step 5: Regenerate affected surfaces**

```python
import subprocess

for surface_key in surfaces:
    contract_path = f"ontology/surface/examples/{surface_key}.ttl"
    print(f"Regenerating {surface_key}...")
    
    result = subprocess.run(
        ["python", "-m", "surface", "lower", "--contracts", contract_path],
        cwd="/Users/t4/work/lattice",
        capture_output=True
    )
    
    if result.returncode != 0:
        print(f"ERROR: Regeneration failed for {surface_key}")
        print(result.stderr.decode())
        return False

print("✅ All surfaces regenerated")
```

**Step 6: Recompile mappings and artefacts**

```python
# For each affected mapping in MORK
for mapping_iri in mappings:
    # Identify which backend(s) target this mapping
    
    # SPARQL backend
    result = subprocess.run(
        ["python", "-m", "mork_compilers", "compile", "--backend", "sparql", mapping_iri],
        capture_output=True
    )
    
    # SHACL backend
    result = subprocess.run(
        ["python", "-m", "mork_compilers", "compile", "--backend", "shacl", mapping_iri],
        capture_output=True
    )
    
    print(f"✅ Recompiled {mapping_iri}")
```

**Step 7: Replace and validate**

```bash
# Atomic replacement (recommended: use git or versioning system)
cd /Users/t4/work/lattice

# Backup old packages
cp -r ontology/surface/execution/ ontology/surface/execution.backup.$(date +%s)/

# Run all validation gates
python -m pytest tools/surface/test_surface.py -v
python -m pytest tools/mork_compilers/test_mork_compilers.py -v

# Run parity checks
python tools/surface/parity.py ontology/surface/examples/ --validate

# If all pass, commit and publish
git add ontology/surface/execution/
git commit -m "Invalidation: regenerate surfaces for $SOURCE_IRI change"
```

**Exit criteria:**
- ✅ All Surface unit tests pass
- ✅ All MORK compiler tests pass
- ✅ Read-set freshness clean
- ✅ MORK governance validation passes
- ✅ SHACL and SPARQL checks pass
- ✅ Parity checks pass

---

## Scenario 2: Mapping or Template Change

**When to use:** A MORK mapping is modified, a compiler template is updated, or a backend policy changes.

**Step 1: Identify the changed mapping**

```python
changed_mapping_iri = "http://example.org/mappings/CoverageTypeProjection_v1"

print(f"Changed mapping: {changed_mapping_iri}")
```

**Step 2: Plan mapping-based regeneration**

```python
from surface.invalidation import plan_regeneration

# Plan based on mapping change
surfaces, mappings, artefacts = plan_regeneration(
    changed_sources=[],
    changed_mappings=[changed_mapping_iri],
    changed_profiles=[],
    graph=manifest_g
)

print(f"Affected artefacts: {len(artefacts)}")
```

**Step 3: Traverse dependency edges**

```python
# Load MORK graph to find dependencies
mork_g = Graph()
mork_g.parse("ontology/mork/spec/Mork.ttl")

# Find what depends on the changed mapping
dependents = []
for s, p, o in mork_g.triples((None, mork_ns.dependsOnMapping, changed_mapping_iri)):
    dependents.append(s)

print(f"Dependent mappings: {dependents}")

# Follow generatedBy edges for artefacts
for artefact_iri in artefacts:
    print(f"Regenerate artefact: {artefact_iri}")
```

**Step 4: Recompile each affected artefact**

```bash
python -m mork_compilers compile --backend sparql --mapping "$changed_mapping_iri"
python -m mork_compilers compile --backend shacl --mapping "$changed_mapping_iri"
python -m mork_compilers compile --backend swrl --mapping "$changed_mapping_iri"
```

**Step 5: Run release gates** (same as Scenario 1)

---

## Scenario 3: Profile Change

**When to use:** Naming policy changes, canonicalisation version updates, or symbol mode toggles.

**Step 1: Identify profile change**

```python
# A profile change is intentionally broad
changed_profile = "http://example.org/profiles/GeneralV2"

print(f"Changed profile: {changed_profile}")
```

**Step 2: Plan profile-based regeneration**

```python
from surface.invalidation import plan_regeneration

# Profile changes affect everything downstream
surfaces, mappings, artefacts = plan_regeneration(
    changed_sources=[],
    changed_mappings=[],
    changed_profiles=[changed_profile],
    graph=manifest_g
)

print(f"⚠️  Broad impact: {len(surfaces)} surfaces, {len(mappings)} mappings, {len(artefacts)} artefacts")
```

**Why profile changes are broad:**

- Naming policy affects all generated symbol IRIs
- Canonicalisation version invalidates all hashes
- Entailment regime changes whether inferences are read
- Symbol mode changes output form
- Stack policy affects composition rules

**Step 3: Regenerate in dependency order**

Regenerate all affected surfaces, then mappings, then artefacts in dependency order:

```python
# Topological sort by dependency
from surface.invalidation import topo_sort_by_dependency

surfaces_ordered = topo_sort_by_dependency(surfaces, graph=manifest_g)

for surface_key in surfaces_ordered:
    print(f"Regenerating {surface_key}...")
    # [regeneration code from Scenario 1]
```

**Step 4: Update profile version in manifests and contracts**

```python
# After successful regeneration, update all manifests
for surface_key in surfaces:
    manifest_path = f"ontology/surface/execution/{surface_key}/manifest.ttl"
    g = Graph()
    g.parse(manifest_path)
    
    # Update profile reference (example)
    profile_old = rdflib.Namespace("http://example.org/profiles/GeneralV1")
    profile_new = rdflib.Namespace("http://example.org/profiles/GeneralV2")
    
    # Replace references
    for s, p, o in g.triples((None, rdflib.RDF.type, profile_old.SurfaceProfile)):
        g.remove((s, p, o))
        g.add((s, p, profile_new.SurfaceProfile))
    
    g.serialize(manifest_path, format="turtle")
```

**Step 5: Run release gates** (same as Scenario 1)

---

## Scenario 4: Canonicalisation Change

**When to use:** The canonicalization contract version changes (e.g., `srf-canon/1` → `srf-canon/2`). Rare operation with high impact.

**⚠️ WARNING:** This invalidates every recorded hash. Mixing old and new canonicalisation in production is unsafe.

**Step 1: Set canonicalisation-changed flag**

```python
canonicalisation_changed = True
recorded_version = "srf-canon/1"  # old
new_version = "srf-canon/2"       # new

print(f"Canonicalisation cutover: {recorded_version} → {new_version}")
```

**Step 2: Mark all hashes as stale**

```python
from surface.invalidation import invalidate_all_hashes

# Every recorded srf:readHash, srf:semanticContentHash, srf:artefactHash is now stale
for surface_package in all_package_paths():
    manifest_g = Graph()
    manifest_g.parse(f"{surface_package}/manifest.ttl")
    
    # Remove all old hashes
    invalidate_all_hashes(manifest_g)
    
    # Will be recomputed during regeneration
    manifest_g.serialize(f"{surface_package}/manifest.ttl", format="turtle")
```

**Step 3: Regenerate entire estate in dependency order**

```bash
# Full regeneration of all known surfaces
python -m surface lower --contracts ontology/surface/examples/*.ttl

# Recompile all mappings
python -m mork_compilers compile --all

# Recompile all artefacts
# (depends on backend selection)
```

**Step 4: Update canonicalisation version in all profiles**

```python
for surface_package in all_package_paths():
    g = Graph()
    contract_path = f"{surface_package}/contract.ttl"
    g.parse(contract_path)
    
    # Update canonicalisation version
    surface_profile = g.value(None, RDF.type, SRF.SurfaceProfile)
    g.set((surface_profile, SRF.canonicalisationVersion, Literal(new_version)))
    
    g.serialize(contract_path, format="turtle")
```

**Step 5: Atomically replace all packages**

```bash
# Do NOT mix old and new canonicalisation in production

# Option A: Blue-green deployment
mv ontology/surface/execution ontology/surface/execution-old
mv ontology/surface/execution-new ontology/surface/execution

# Option B: Staged rollout per domain
for domain in domain1 domain2 domain3; do
    # Move new packages into production
    cp -r ontology/surface/execution-new/$domain/* ontology/surface/execution/$domain/
    # Wait for verification
    sleep 300
done
```

**Step 6: Run full release gates**

```bash
# ALL gates must pass
pytest tools/surface/test_surface.py -v
pytest tools/mork_compilers/test_mork_compilers.py -v
python tools/phase8_conformance.py --full
python tools/surface/parity.py --all --validate

# Verify no mixing
python tools/repository_topology_check.py --check-canonicalisation-consistency
```

**Step 7: Record the change**

Update the runbook in [revision-lifecycle.md](surface-revision-lifecycle.md) with the cutover date and migration notes.

---

## Release Gates (All Scenarios)

Before publishing any regenerated output, verify:

| Gate | Command | Pass criterion |
|------|---------|---|
| Surface unit tests | `pytest tools/surface/test_surface.py -v` | All pass, 61/61 ✅ |
| MORK compiler tests | `pytest tools/mork_compilers/test_mork_compilers.py -v` | All pass, 15/15 ✅ |
| Read-set freshness | `python tools/surface/invalidation.py --check-manifests` | No stale entries |
| MORK governance | `python tools/mork/validate.py --mode production` | All shapes pass |
| SHACL conformance | `python tools/phase8_conformance.py --backend shacl` | All fixtures conform |
| SPARQL conformance | `python tools/phase8_conformance.py --backend sparql` | All queries return expected results |
| Parity checks | `python tools/surface/parity.py --all` | Parity ratio ≥ 99% |
| Provenance completeness | `python tools/surface/invalidation.py --check-provenance` | No missing traces |
| Extraction drift | `python tools/literate_extract.py --check` | No README⇄spec divergence |

---

## Common Situations

### Multiple sources changed at once

```python
changed_sources = [
    "http://example.org/concepts/Coverage_Cyber",
    "http://example.org/concepts/Coverage_Auto",
]

surfaces, mappings, artefacts = plan_regeneration(
    changed_sources=changed_sources,
    changed_mappings=[],
    changed_profiles=[],
    graph=manifest_g
)
```

### Only a hierarchy changed (not members)

Closure-relation forms are affected, but index symbol forms are not (symbols depend on enumeration, not hierarchy).

```python
# Changed: skos:broader relations under Coverage_Auto hierarchy
# Impact: srf:matchesCoverageTypeAncestor closure needs refresh
# No impact: ScopeCoverageType_* class definitions (symbols stay the same)
```

### A surface's read-set is externally maintained

If the surface reads from a shared governance scheme or reference catalog:

```python
# Monitor for changes to that external source
# Example: NFPA codes reference catalog

from surface.invalidation import watch_external_source

watch_external_source(
    source_iri="http://nfpa.org/codes/PerlTypeScheme",
    manifest_path="ontology/surface/execution/peril-index/manifest.ttl",
    polling_interval_hours=24
)

# Automatically regenerate if digest changes
```

---

## Deferred: Deeper Stacking

When stack depth > 1 is enabled, extend this runbook with:

1. **Transitive artefact-hash freshness:** Surface A reads Surface B; B's output hash must appear in A's read set
2. **Stale-input rejection:** If an input surface is stale, the dependent surface cannot be used without regeneration
3. **Cycle detection:** DAG over the surface dependency graph; cycles block compilation
4. **Measured impact cost:** Track regeneration time and resource usage; alert if exceeds threshold

Current tools support depth 1 only. These extensions are in Phase 7+ roadmap.

---

## Troubleshooting

### Regeneration produces different output

**Possible causes:**
1. Profile changed (determinism policy changed)
2. Canonicalisation version mismatch
3. Compiler version mismatch
4. Non-deterministic input graph (unsorted or blank-node labeled)

**Diagnosis:**
```bash
# Check profile consistency
python -c "from tools.surface.model import Profile; print(Profile.identity())"

# Check input graph
python tools/surface/model.py --validate ontology/surface/examples/my-contract.ttl

# Check compiler version
python -m surface --version
python -m mork_compilers --version
```

### Parity checks fail after regeneration

**Possible causes:**
1. Source semantics changed (not just presentation)
2. Backend compiler changed behavior
3. New edge case in read-set handling

**Action:**
1. Review the parity test failure (tool outputs specific divergence)
2. Determine if it's a regression or an expected semantic change
3. Update golden reference if semantic change was intentional
4. If regression, revert regeneration and file a bug

### Memory or performance degradation

**Possible causes:**
1. Read set or output graph grew significantly
2. Canonicalisation cost increased
3. Compiler template processing slower

**Mitigation:**
- Add progress logging to regeneration process
- Break large regeneration into batches
- Profile with `tools/mork_profiling.py` before production

---

## See Also

- [Surface Revision Lifecycle](surface-revision-lifecycle.md) — State machine for surface versions
- [Phase 7 Status](../status/surface-mork-unified-projection.md#phase-7--provenance-and-invalidation-hardening) — Completion details
- [Outstanding Items](../status/surface-outstanding-items.md) — Known limitations and future work
- `tools/surface/invalidation.py` — API reference

---

**Last updated:** 2026-09-22  
**Related ADR:** [ADR-A27 (Invalidation and Minimal-Scope Regeneration Policy)](../../architecture/decisions/ADR-A27-invalidation-and-minimal-scope-regeneration-policy.md)
