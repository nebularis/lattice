<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Phase 4 Validation Handoff

The Phase 4 worker contract lowers `ontology/surface/examples/saas-subscription-arr-projection.ttl` into an immutable MORK staging graph only. Validate with:

```text
python -m pytest workers/tests/test_projection_contract.py workers/tests/test_projection_policy.py workers/tests/test_projection_lowering.py
python -m unittest surface.test_surface -v
yarn check
yarn build
yarn test
```

Run a RabbitMQ integration that verifies the result graph is inside the requested staging namespace and a Fuseki integration that materializes the ARR contract and profile by immutable hash.

The lower-job request must not contain active mapping targets, RDF payloads, credentials, browser tokens, or commands. The validation environment must materialize the ARR contract and profile graph by immutable hash, invoke `surface lower`, publish the staged mapping graph, and verify repeated lowering has stable identifiers and dependency order. The staged result must surface MCN status, dependencies, backend capability, and its review requirement to the Technical Inspector.

This restricted authoring environment did not run Python, Yarn, Playwright, RabbitMQ, Fuseki, or compiler tests. `yarn.lock` must be regenerated and reviewed in the network-enabled environment before CI can use the Studio workspace dependencies.