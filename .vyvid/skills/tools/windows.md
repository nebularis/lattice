## Text encoding and newlines

STD-275 is the rule on reading. It was found in `tools/import_guard.py`'s `standalone_violations` (TD-91), which read an ontology file with a bare `Path.read_text()` and failed two tests on every Windows checkout for a reason that read as flaky until traced.
