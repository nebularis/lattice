# SPDX-License-Identifier: MPL-2.0
"""Whether a pass moves a ledger's revision once, or once for each of its postings.

An exhaustive model of the three transitions of Behaviour's ordered-draws.ttl. One
activation draws a seat while the bundle has one, draws an alert when that leaves
fewer than 2 seats, and moves to overage when the bundle is empty. It runs against
one other writer on the same two accounts, a credit of 3 seats or a second
activation, in every interleaving, with and without one crash of the first
activation at any point.

O1  every outcome is the outcome of the actors run one after another, in some order
O2  every outcome with a crash is an outcome without one

The run fails when a protocol's counts differ from EXPECTED. See README.md.
"""
import itertools
import sys


def store(bundle, quota, actors):
    bal = {"bundle": bundle, "quota": quota}
    return {"rev": 0, "bal": bal, "hist": {0: dict(bal)}, "rcpt": {},
            "state": {a: "within" for a in actors}, "fired": {}}


def write(S, posts):
    """The ledger's one writer, whole or nothing, at the latest revision."""
    b = dict(S["bal"])
    for account, delta in posts:
        b[account] += delta
    if min(b.values()) < 0:
        return None
    S["bal"] = b
    S["rev"] += 1
    S["hist"][S["rev"]] = dict(b)
    return S["rev"]


def evaluate(bal, state):
    """The example's sequential environment, over a working copy."""
    w, posts, fired = dict(bal), [], []
    if w["bundle"] >= 1:
        w["bundle"] -= 1
        posts.append(("bundle", -1))
        fired.append("seat")
    if w["bundle"] < 2 and w["quota"] >= 1:
        w["quota"] -= 1
        posts.append(("quota", -1))
        fired.append("alert")
    if w["bundle"] == 0 and state == "within":
        state = "overage"
        fired.append("overage")
    return posts, fired, state


def credit(S, me):
    yield
    write(S, [("bundle", 3)])
    S["fired"][me] = ["credit"]


def once_a_pass(guard_on_read):
    """A pass is evaluated from one revision and written as one request."""
    def actor(S, me):
        while True:
            yield  # read the ledger, or find the pass already written
            if me in S["rcpt"]:
                r, written = S["rcpt"][me] - 1, True
            else:
                r, written = S["rev"], False
            posts, fired, state = evaluate(S["hist"][r], S["state"][me])
            if posts and not written:
                yield  # the one write, with the revision the pass records
                if guard_on_read and S["rev"] != r:
                    continue
                r1 = write(S, posts)
                if r1 is None:
                    continue
                S["rcpt"][me] = r1
            yield  # Behaviour's records, outside the ledger
            S["fired"][me], S["state"][me] = fired, state
            return
    return actor


GUARDS = (("seat", "bundle", lambda b: b["bundle"] >= 1),
          ("alert", "quota", lambda b: b["bundle"] < 2))


def per_posting(pinned, receipts, after_refusal, start_recorded):
    """Each posting is its own write, with a pinned read, a refusal and receipts."""
    def actor(S, me):
        yield  # where the pass starts
        cur = S["rcpt"].setdefault((me, "start"), S["rev"]) if start_recorded else S["rev"]
        fired = []
        for name, account, guard in GUARDS:
            key = (me, name)
            if receipts and key in S["rcpt"]:
                ok, rev = S["rcpt"][key]
            else:
                if not guard(S["hist"][cur] if pinned else S["bal"]):
                    continue
                yield  # the posting's request, decided by the writer
                rev = write(S, [(account, -1)])
                ok = rev is not None
                rev = rev if ok else S["rev"]
                if receipts:
                    S["rcpt"][key] = (ok, rev)
                yield  # back with the evaluator
            if ok:
                fired.append(name)
                cur = rev
            elif after_refusal == "refusal":
                cur = rev
        state = S["state"][me]
        if (S["hist"][cur] if pinned else S["bal"])["bundle"] == 0 and state == "within":
            state = "overage"
            fired.append("overage")
        yield  # Behaviour's records, outside the ledger
        S["fired"][me], S["state"][me] = fired, state
    return actor


def outcome(S):
    return (S["bal"]["bundle"], S["bal"]["quota"],
            tuple(sorted((a, tuple(f), S["state"].get(a, "")) for a, f in S["fired"].items())))


def run(make, actors, crash, choices, view=None):
    S = make()
    gens = {a: f(S, a) for a, f in actors.items()}
    live, steps, crashed, counts, trace = set(gens), {a: 0 for a in gens}, False, [], []
    while live:
        options = [(a, "step") for a in sorted(live)]
        if crash in live and not crashed and steps[crash]:
            options.append((crash, "crash"))
        d = len(counts)
        counts.append(len(options))
        a, kind = options[choices[d] if d < len(choices) else 0]
        trace.append(a if kind == "step" else a + "!")
        if kind == "crash":
            gens[a], crashed = actors[a](S, a), True
            continue
        steps[a] += 1
        try:
            next(gens[a])
        except StopIteration:
            live.discard(a)
    return (view or outcome)(S), counts, " ".join(trace)


def outcomes(make, actors, crash=None, view=None):
    """Every schedule once, by counting through the choices each run met."""
    found, choices = {}, []
    while True:
        out, counts, trace = run(make, actors, crash, choices, view)
        found.setdefault(out, trace)
        path = choices + [0] * (len(counts) - len(choices))
        i = len(path) - 1
        while i >= 0 and path[i] + 1 >= counts[i]:
            i -= 1
        if i < 0:
            return found
        choices = path[:i] + [path[i] + 1]


def serial(bundle, quota, actors):
    ref = {a: (credit if f is credit else once_a_pass(True)) for a, f in actors.items()}
    found = set()
    for order in itertools.permutations(actors):
        S = store(bundle, quota, actors)
        for a in order:
            for _ in ref[a](S, a):
                pass
        found.add(outcome(S))
    return found


PROTOCOLS = {
    "A": ("once a pass, written on the revision it read", once_a_pass(True)),
    "A'": ("once a pass, written on whatever is latest", once_a_pass(False)),
    "B": ("each posting, latest reads, no receipts", per_posting(False, False, "stay", False)),
    "C": ("each posting, pinned reads, a refusal and receipts", per_posting(True, True, "stay", False)),
    "C+": ("C, and a refusal returns its revision", per_posting(True, True, "refusal", False)),
    "C++": ("C+, and the start revision is recorded", per_posting(True, True, "refusal", True)),
}

# cells where O1 fails with no crash, where it fails with one, where O2 fails,
# and the distinct outcomes no order gives, with no crash
EXPECTED = {"A": (0, 0, 0, 0), "A'": (1, 7, 6, 1), "B": (7, 12, 12, 9),
            "C": (7, 7, 2, 13), "C+": (7, 7, 2, 9), "C++": (7, 7, 0, 9)}

TABLE = [(2, 3, ["seat"]), (1, 2, ["seat", "alert"]), (0, 1, ["seat", "alert", "overage"])]


def the_examples_table():
    """Three activations of one licence, one after another."""
    S, state, rows = store(3, 3, ["1", "2", "3"]), "within", []
    for a in ("1", "2", "3"):
        S["state"][a] = state
        for _ in once_a_pass(True)(S, a):
            pass
        state = S["state"][a]
        rows.append((S["bal"]["bundle"], S["bal"]["quota"], S["fired"][a]))
    return rows


def main():
    assert the_examples_table() == TABLE, the_examples_table()
    print("the example's table reproduced")
    cells = [(b, q) for b in (0, 1, 2) for q in (1, 3)]
    wrong = []
    for name, (label, proto) in PROTOCOLS.items():
        plain_bad = crash_bad = o2_bad = 0
        distinct, w_plain, w_o2 = set(), None, None
        for (b, q), other in itertools.product(cells, ("credit", "second")):
            actors = {"P": proto, "X": credit if other == "credit" else proto}
            make = lambda b=b, q=q, actors=actors: store(b, q, actors)
            ok = serial(b, q, actors)
            plain = outcomes(make, actors)
            crashed = outcomes(make, actors, crash="P")
            p1 = [(o, t) for o, t in plain.items() if o not in ok]
            c1 = [(o, t) for o, t in crashed.items() if o not in ok]
            w2 = [(o, t) for o, t in crashed.items() if o not in plain]
            distinct |= {(b, q, other, o) for o, _ in p1}
            plain_bad += bool(p1)
            crash_bad += bool(c1)
            o2_bad += bool(w2)
            if p1 and not w_plain:
                w_plain = (b, q, other, *min(p1, key=lambda x: len(x[1])))
            if w2 and not w_o2:
                w_o2 = (b, q, other, *min(w2, key=lambda x: len(x[1])))
        got = (plain_bad, crash_bad, o2_bad, len(distinct))
        print(f"\n{name}, {label}\n  of 12 cells, O1 fails in {plain_bad} with no crash and {crash_bad} "
              f"with one, O2 fails in {o2_bad}. Distinct outcomes no order gives, with no crash, {len(distinct)}")
        if w_plain:
            print("  O1 witness, no crash, bundle %d quota %d with %s -> %s\n     schedule %s" % w_plain)
        if w_o2:
            print("  O2 witness, bundle %d quota %d with %s -> %s\n     schedule %s" % w_o2)
        if got != EXPECTED[name]:
            wrong.append((name, got, EXPECTED[name]))
    for name, got, want in wrong:
        print(f"WRONG {name}: got {got}, expected {want}")
    return 1 if wrong else 0


if __name__ == "__main__":
    sys.exit(main())
