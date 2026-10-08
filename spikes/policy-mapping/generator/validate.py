import sys
sys.path.insert(0, "tools")
from pathlib import Path
from rdflib.namespace import SH
import test_parameter_bindings as t
from pyshacl import validate
O = Path(".local/policy-mapping")
for label, files in (("stated+bound", ["nonprofit-portfolio.ttl", "bound-meaning.ttl"]),):
    data = t._graph(*[O / f for f in files])
    _, report, text = validate(t.MODEL + data, shacl_graph=t.EVERY_SHAPE, inference="none", advanced=True)
    for sev in (SH.Violation, SH.Warning, SH.Info):
        rs = list(report.subjects(SH.resultSeverity, sev))
        print(f"== {label}: {sev.split('#')[1]} {len(rs)}")
        seen = {}
        for r in rs:
            m = str(report.value(r, SH.resultMessage)); f = str(report.value(r, SH.focusNode)).rsplit('/',1)[-1]
            seen.setdefault(m, []).append(f)
        for m, fs in seen.items():
            print(f"  [{len(fs)}] {m}\n      e.g. {', '.join(sorted(fs)[:6])}")
