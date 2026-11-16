# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""Two probes of the credit kinds benchmark (LG-22), each run on demand and neither changing a default (ADR-A124). A probe fails on a wrong result and never on time.

**The period probe.** LG-19 found the plain root read on rdflib 1.4 to 1.6 times slower at 5% credits and 20,000 postings, where the corpus has more period graphs than it had and folds 4% more rows. The hypothesis
is that rdflib's read grows with the number of named graphs it visits and not only with the rows it folds. The probe reads the plain root fold from the start of history on the one-level corpus with the period
length at each of several values, the postings identical in every case, each read repeated, on rdflib and on Oxigraph as a control. A period length is passed to the probe and `EVERY_POSITIONS` is put back after it.

**The cut probe.** LG-19 found the sum less the cuts on Jena through the test kit at 1.85 times the kind-filtered read at 5% credits and 20,000 postings, from a few single reads of milliseconds, read once. The probe
repeats the two reads many times after warm-up reads, from the start of history and from a checkpoint, and counts the cuts of the corpus before and after LG-19.

Run `mise run check:ledger-credit-kinds-probes`. `LEDGER_PROBES_QUICK=1` runs a small size, `LEDGER_PROBES_REPORT_DIR` writes `probes-report.md` and `probes-report.json` elsewhere, both git-ignored."""

from __future__ import annotations

import json
import os
import random
import statistics
import sys
import tempfile
import time
from pathlib import Path

import check as ck

HERE = Path(__file__).resolve().parent
LENGTHS, REPEATS = (100, 200, 320, 640), 5
CUT_REPEATS, CUT_WARMUPS = 30, 5


def legacy_stream(count: int, credit_share: float, two_level: bool) -> list[ck.Posting]:
    """The generator as it was before LG-19, kept as a reference. It posts every debit it draws, whatever the accounts on its path hold."""
    rng, kind_rng, place_rng = random.Random(ck.SEED), random.Random(ck.SEED + 1), random.Random(ck.SEED + 2)
    out, step, pos = [], [a.stated for a in ck.TREE], 0
    while len(out) < count:
        pos += 1
        for micro in range(min(rng.randint(1, 3), count - len(out))):
            debit = rng.random() >= credit_share
            contract = rng.choice(ck.CONTRACTS)
            amount = rng.randint(1, ck.DEBIT_MAX if debit else ck.CREDIT_MAX)
            kind = None if debit else ck.L + rng.choice(ck.KINDS)
            if debit:
                ck.settle_debit(step, contract, amount)
                out.append(ck.Posting(pos, micro, contract, True, amount, None, 0 if two_level else amount))
                continue
            if kind_rng.random() < ck.KINDLESS_SHARE and ck.unrestricted(contract):
                kind = None
            at = contract
            if two_level:
                candidates = [i for i in ck.chain(contract)[1:3] if ck.accepts_kind(ck.TREE[i], kind)]
                at = place_rng.choice(candidates) if candidates and place_rng.random() < ck.UPPER_SHARE else contract
            applied, cuts = ck.settle_credit(step, at, amount, kind)
            out.append(ck.Posting(pos, micro, at, False, amount, kind, applied, cuts if two_level else ()))
    return out


def spread(times: list[float]) -> dict:
    ms = [1000 * t for t in times]
    return {"median_ms": statistics.median(ms), "min_ms": min(ms), "max_ms": max(ms), "repeats": len(ms)}


def period_probe(count: int = 20_000, share: float = 0.05, lengths=LENGTHS, repeats: int = REPEATS, names=("rdflib", "oxigraph")) -> list[dict]:
    """The plain root read from the start of history on the one-level corpus at each period length. Reports, for each, the period graphs, the rows folded and the median, least and greatest time."""
    out = []
    for length in lengths:
        with ck.using_period(length):
            corpus = ck.build_corpus(count, share)
            facts = ck.corpus_facts(count, share, ck.CORPUS_ONE)
            point = corpus.points[-1]
            want = (corpus.model.balance[("plain", 0, point)], corpus.model.rows[("plain", 0, point)])
            for name in names:
                with tempfile.TemporaryDirectory(prefix="ledger-probe-") as tmp:
                    backend = ck.BACKEND_CLASS[name](tmp)
                    try:
                        backend.load(ck.quads(corpus.postings, corpus.cps))
                        times, got = [], None
                        for _ in range(repeats + 1):
                            begin = time.perf_counter()
                            got = ck.read("plain", backend, 0, point)
                            times.append(time.perf_counter() - begin)
                        if got != want:
                            raise ck.WrongResult(f"{name} period {length}: the plain root read is {got}, the model gives {want}")
                        out.append({"backend": name, "period": length, "passes": facts["passes"], "periods": facts["periods"], "period_graphs": facts["period_graphs"], "rows": got[1], **spread(times[1:])})
                    finally:
                        backend.close()
                        backend = None
                        ck.release_store()
    return out


def cut_probe(count: int = 20_000, share: float = 0.05, repeats: int = CUT_REPEATS, warmups: int = CUT_WARMUPS, name: str = "jena") -> dict:
    """The kind-filtered read in the form of the postings part of the sum with cuts (`UNION_FOLD`) and the sum with cuts, each over the 27 ancestor reads (9 ancestors at the 3 read points) and at the root
    alone, from the start of history and from the checkpoint, `repeats` times after `warmups` reads. Also the cuts of the corpus now and before LG-19."""
    corpus = ck.build_cut_corpus(count, share)
    points = corpus.points
    cuts = {"after LG-19": sum(len(p.cuts) for p in corpus.postings), "before LG-19": sum(len(p.cuts) for p in legacy_stream(count, share, True))}
    credits = {"after LG-19": sum(not p.debit for p in corpus.postings), "before LG-19": sum(not p.debit for p in legacy_stream(count, share, True))}
    reads = {"kind-filtered-union": lambda b, i, pt, cp: ck.read_union(b, i, pt, cp), "sum-with-cuts": lambda b, i, pt, cp: ck.read_with_cuts(b, i, pt, cp)}
    result = {"backend": name, "postings": count, "share": share, "credits": credits, "cuts": cuts, "modes": {}}
    with tempfile.TemporaryDirectory(prefix="ledger-probe-") as tmp:
        backend = ck.BACKEND_CLASS[name](tmp)
        backend.upper = True
        try:
            backend.load(ck.quads(corpus.postings, corpus.cps))
            for mode, cp in (("from the start", False), ("from a checkpoint", True)):
                cell = {}
                for fold, fn in reads.items():
                    for _ in range(warmups):
                        for i in ck.ANCESTORS:
                            for pt in points:
                                fn(backend, i, pt, cp)
                    totals, roots = [], []
                    for _ in range(repeats):
                        begin, root = time.perf_counter(), 0.0
                        for i in ck.ANCESTORS:
                            for pt in points:
                                one = time.perf_counter()
                                fn(backend, i, pt, cp)
                                if i == 0:
                                    root += time.perf_counter() - one
                        totals.append(time.perf_counter() - begin)
                        roots.append(root / len(points))
                    cell[fold] = {"all 27 reads": spread(totals), "root": spread(roots)}
                for part in ("all 27 reads", "root"):
                    cell[f"sum-with-cuts / kind-filtered-union, {part}"] = cell["sum-with-cuts"][part]["median_ms"] / cell["kind-filtered-union"][part]["median_ms"]
                result["modes"][mode] = cell
        finally:
            backend.close()
            backend = None
            ck.release_store()
    return result


def render(data: dict) -> list[str]:
    out = ["# Two probes of the credit kinds benchmark (LG-22)", "", "Environment: " + ", ".join(f"{k} {v}" for k, v in data["environment"].items() if v), ""]
    out += ck.corpus_section([(ck.CORPUS_ONE, data["period"][0]["rows"] and data["count"], data["share"])] + [(ck.CORPUS_TWO, data["count"], data["share"])])
    out += ["## The period probe", "", f"The plain root read from the start of history on the one-level corpus of {data['count']:,} postings, drawn {data['share']:.0%}, the postings the same at every length. Period graphs is the named graphs the postings fall in, "
            "rows the postings the read folded, and the time the median of the reads, with the least and the greatest.", ""]
    head = ["backend", "period passes", "periods", "period graphs", "rows folded", "median ms", "least ms", "greatest ms", "reads"]
    out += _table(head, [[r["backend"], r["period"], r["periods"], r["period_graphs"], r["rows"], f"{r['median_ms']:.1f}", f"{r['min_ms']:.1f}", f"{r['max_ms']:.1f}", r["repeats"]] for r in data["period"]])
    c = data["cuts"]
    out += ["", "## The cut probe", "", f"{c['backend']} through the test kit, the two-level corpus of {c['postings']:,} postings drawn {c['share']:.0%}. The cuts of the corpus, and its credits, after LG-19 and before it, from a generator kept as a reference: "
            f"{c['cuts']['after LG-19']:,} cuts in {c['credits']['after LG-19']:,} credits after, {c['cuts']['before LG-19']:,} in {c['credits']['before LG-19']:,} before.", ""]
    rows = []
    for mode, cell in c["modes"].items():
        for part in ("all 27 reads", "root"):
            a, b = cell["kind-filtered-union"][part], cell["sum-with-cuts"][part]
            rows.append([mode, part, f"{a['median_ms']:.2f} / {a['min_ms']:.2f} / {a['max_ms']:.2f}", f"{b['median_ms']:.2f} / {b['min_ms']:.2f} / {b['max_ms']:.2f}", f"{cell[f'sum-with-cuts / kind-filtered-union, {part}']:.2f}"])
    out += _table(["read", "of", "kind-filtered-union median / least / greatest ms", "sum-with-cuts median / least / greatest ms", "ratio of the medians"], rows)
    return out + [""]


def _table(head: list[str], rows: list[list]) -> list[str]:
    return ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)] + ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]


def main() -> int:
    fast = bool(os.environ.get("LEDGER_PROBES_QUICK"))
    count, share = (1_000, 0.05) if fast else (20_000, 0.05)
    try:
        data = {"environment": {**ck.environment(), "cpus": str(os.cpu_count()), "quick": "yes" if fast else ""}, "count": count, "share": share}
        data["period"] = period_probe(count, share, (100, 200) if fast else LENGTHS, 2 if fast else REPEATS, tuple(n for n in ("rdflib", "oxigraph")))
        print("period probe done", flush=True)
        if ck.jena_available():
            data["cuts"] = cut_probe(count, share, 3 if fast else CUT_REPEATS, 1 if fast else CUT_WARMUPS)
            print("cut probe done", flush=True)
        else:
            data["cuts"] = None
    except ck.WrongResult as error:
        print(f"WRONG RESULT: {error}", file=sys.stderr)
        return 1
    directory = Path(os.environ.get("LEDGER_PROBES_REPORT_DIR") or HERE)
    (directory / "probes-report.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    (directory / "probes-report.md").write_text("\n".join(render(data)), encoding="utf-8")
    print(f"report written to {directory}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
