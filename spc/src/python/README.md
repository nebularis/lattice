# SPC Design-Time Python Toolchain

## Project Structure

```
spc-toolchain/
├── pyproject.toml
├── src/
│   └── spc/
│       ├── __init__.py
│       ├── cli.py                          # Main CLI entry point
│       │
│       ├── processle/                      # Phase 0: ProcessLE parser
│       │   ├── __init__.py
│       │   ├── grammar.py                  # PEG grammar definition
│       │   ├── parser.py                   # Parser → AST
│       │   ├── ast_nodes.py                # AST node types
│       │   └── validator.py                # Syntactic validation
│       │
│       ├── encoder/                        # Phase 1a: AST → A-Box
│       │   ├── __init__.py
│       │   ├── abox_compiler.py            # Main compiler
│       │   ├── sort_encoder.py             # Sorts → RDF
│       │   ├── behavior_encoder.py         # Behaviors → RDF
│       │   ├── global_type_encoder.py      # Global types → RDF
│       │   ├── local_type_encoder.py       # Local types → RDF
│       │   ├── typing_encoder.py           # Typing judgments → RDF
│       │   ├── subtyping.py                # Gay-Hole algorithm
│       │   ├── refinement_encoder.py       # Refinement predicates → RDF
│       │   └── extension_encoder.py        # EXT annotations → RDF
│       │
│       ├── verify/                         # Phase 1b: Verification
│       │   ├── __init__.py
│       │   ├── jena_client.py              # Jena/Fuseki HTTP client
│       │   ├── owl_verifier.py             # Classification + consistency
│       │   ├── shacl_verifier.py           # SHACL validation
│       │   ├── external_checks.py          # Variable scoping, contractiveness
│       │   └── shapes/                     # SHACL shape files
│       │       ├── linearity.ttl
│       │       ├── coherence.ttl
│       │       ├── contractiveness.ttl
│       │       ├── projectability.ttl
│       │       ├── sender_receiver.ttl
│       │       └── extensions.ttl
│       │
│       ├── materialise/                    # Phase 2a: Projection
│       │   ├── __init__.py
│       │   ├── projector.py                # Projection materialisation
│       │   └── queries/                    # SPARQL templates
│       │       ├── project_sender.rq
│       │       ├── project_receiver.rq
│       │       ├── project_nonparticipant.rq
│       │       └── project_recursive.rq
│       │
│       ├── extract/                        # Phase 2b-c: Extraction
│       │   ├── __init__.py
│       │   ├── shape_extractor.py          # Refinement → SHACL shapes
│       │   └── extension_config_gen.py     # EXT ontology → JSON config
│       │
│       ├── ingress/                        # Phase 3: MORK/RML ingress
│       │   ├── __init__.py
│       │   ├── rml_executor.py             # RML execution wrapper
│       │   ├── ingress_config_gen.py       # MORK → ingress config JSON
│       │   └── egress_config_gen.py        # MORK → egress config JSON
│       │
│       ├── ontologies/                     # Bundled T-Box files
│       │   ├── spc_core.ttl                # The SPC T-Box (fixed)
│       │   ├── ext_timer.ttl
│       │   ├── ext_job.ttl
│       │   ├── ext_error.ttl
│       │   ├── ext_compensation.ttl
│       │   ├── ext_signal.ttl
│       │   └── ext_connector.ttl
│       │
│       └── util/
│           ├── __init__.py
│           ├── namespaces.py               # RDF namespace definitions
│           ├── iri.py                       # IRI minting utilities
│           └── json_ser.py                 # JSON serialisation helpers
│
├── tests/
│   ├── test_parser.py
│   ├── test_encoder.py
│   ├── test_subtyping.py
│   ├── test_verification.py
│   ├── test_projection.py
│   ├── test_extension_config.py
│   ├── test_ingress.py
│   └── fixtures/
│       ├── placement_negotiation.ple
│       ├── expected_abox.ttl
│       └── sample_payloads/
│           ├── whitespace_quote.json
│           └── carrier_terms.json
│
└── scripts/
    └── pipeline.sh                         # Full pipeline runner
```