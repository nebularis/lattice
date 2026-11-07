## Text encoding and newlines

STD-275 is the rule on reading. It was found in `tools/import_guard.py`'s `standalone_violations` (TD-91), which read an ontology file with a bare `Path.read_text()` and failed two tests on every Windows checkout for a reason that read as flaky until traced.

## Directory links

`mise run skills:link` makes each skill a symbolic link, else a junction, else a copy, and prints which. [Directory links on Windows](../../../docs/developer/windows-links.md) explains junctions, what can refuse one, and how to remove one safely. `tools/clean.py` unlinks a link or junction and never removes its target.
