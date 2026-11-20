# SPDX-License-Identifier: MPL-2.0
"""Where a pass's position comes from, under one request for each pass.

The ledger holds its passes to one order. A pass at an earlier position never
records a greater revision. This model asks which rule for a pass's position
keeps that, on the actors and the schedules of pass_revision_model.py, with
each actor's stimulus given a position of its own.

O3  in every outcome, the passes' positions never fall as their revisions rise
O4  in every outcome, no pass is at a position before its stimulus's

The run fails when a rule's counts differ from EXPECTED. See README.md.
"""
import itertools
import sys

from pass_revision_model import evaluate, outcomes, store

RULES = {
    "stimulus": "the pass takes its stimulus's position",
    "read": "the later of its stimulus's and the latest pass's, read with the revision",
    "writer": "the later of its stimulus's and the latest pass's, given by the writer",
}


def ledger(bundle, quota, actors, times):
    S = store(bundle, quota, actors)
    S.update(t=dict(times), last=0, passes=[])
    return S


def write(S, posts, position, me):
    """The ledger's one writer, whole or nothing, recording the pass's position."""
    b = dict(S["bal"])
    for account, delta in posts:
        b[account] += delta
    if min(b.values()) < 0:
        return None
    S["bal"] = b
    S["rev"] += 1
    S["hist"][S["rev"]] = dict(b)
    S["last"] = position
    S["passes"].append((S["rev"], position, S["t"][me]))
    return S["rev"]


def positioned(rule, seen, S, me):
    t = S["t"][me]
    return {"stimulus": t, "read": max(t, seen), "writer": max(t, S["last"])}[rule]


def credit(rule):
    def actor(S, me):
        yield  # read and written in the writer's own turn
        write(S, [("bundle", 3)], positioned(rule, S["last"], S, me), me)
        S["fired"][me] = ["credit"]
    return actor


def activation(rule, guard_on_read):
    """pass_revision_model's once_a_pass, with a position on the request."""
    def actor(S, me):
        while True:
            yield  # read the ledger, or find the pass already written
            if me in S["rcpt"]:
                r, written = S["rcpt"][me] - 1, True
            else:
                r, written = S["rev"], False
            seen = S["last"]
            posts, fired, state = evaluate(S["hist"][r], S["state"][me])
            if posts and not written:
                yield  # the one write
                if guard_on_read and S["rev"] != r:
                    continue
                r1 = write(S, posts, positioned(rule, seen, S, me), me)
                if r1 is None:
                    continue
                S["rcpt"][me] = r1
            yield  # Behaviour's records, outside the ledger
            S["fired"][me], S["state"][me] = fired, state
            return
    return actor


def passes(S):
    return tuple(S["passes"])


def in_order(ps):
    return all(a[1] <= b[1] for a, b in zip(ps, ps[1:]))


def not_before_stimulus(ps):
    return all(position >= t for _, position, t in ps)


def one_after_another(make, actors):
    found = set()
    for order in itertools.permutations(actors):
        S = make()
        for a in order:
            for _ in actors[a](S, a):
                pass
        found.add(passes(S))
    return found


# cells where O3 fails with the actors one after another, with no crash and
# with one crash, and cells where O4 fails, of 36
EXPECTED = {
    ("A", "stimulus"): (20, 20, 20, 0),
    ("A", "read"): (0, 0, 0, 0),
    ("A", "writer"): (0, 0, 0, 0),
    ("A'", "stimulus"): (20, 20, 20, 0),
    ("A'", "read"): (0, 10, 10, 0),
    ("A'", "writer"): (0, 0, 0, 0),
}

TIMES = ({"P": 1, "X": 2}, {"P": 2, "X": 1}, {"P": 1, "X": 1})


def main():
    cells = [(b, q) for b in (0, 1, 2) for q in (1, 3)]
    wrong = []
    for (name, guard), rule in itertools.product((("A", True), ("A'", False)), RULES):
        serial_bad = plain_bad = crash_bad = early = 0
        witness = None
        for (b, q), other, times in itertools.product(cells, ("credit", "second"), TIMES):
            proto = activation(rule, guard)
            actors = {"P": proto, "X": credit(rule) if other == "credit" else proto}
            make = lambda b=b, q=q, actors=actors, times=times: ledger(b, q, actors, times)
            serial = one_after_another(make, actors)
            plain = outcomes(make, actors, view=passes)
            crashed = outcomes(make, actors, crash="P", view=passes)
            serial_bad += any(not in_order(ps) for ps in serial)
            bad = [(ps, t) for ps, t in plain.items() if not in_order(ps)]
            plain_bad += bool(bad)
            crash_bad += any(not in_order(ps) for ps in crashed)
            early += any(not not_before_stimulus(ps) for ps in list(plain) + list(crashed))
            if bad and not witness:
                witness = (b, q, other, times["P"], times["X"], *min(bad, key=lambda x: len(x[1])))
        got = (serial_bad, plain_bad, crash_bad, early)
        print(f"\n{name}, {RULES[rule]}\n  of 36 cells, O3 fails in {serial_bad} one after another, "
              f"{plain_bad} with no crash and {crash_bad} with one. O4 fails in {early}")
        if witness:
            print("  O3 witness, bundle %d quota %d with %s, stimulus positions P %d X %d\n"
                  "     passes as (revision, position, stimulus) %s\n     schedule %s" % witness)
        if got != EXPECTED[(name, rule)]:
            wrong.append((name, rule, got, EXPECTED[(name, rule)]))
    for name, rule, got, want in wrong:
        print(f"WRONG {name} {rule}: got {got}, expected {want}")
    return 1 if wrong else 0


if __name__ == "__main__":
    sys.exit(main())
