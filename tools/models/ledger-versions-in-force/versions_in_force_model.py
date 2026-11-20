# SPDX-License-Identifier: MPL-2.0
"""Which postings count against which version of an account's terms (LG-Q49).

One account, whose first version states 10. A history is a list of steps in
the order they are recorded: a draw or a credit of an amount at an effective
position, or a later version with its stated amount and the position it is in
force from. Each rule decides every draw of every history, and two invariants
are read after every step.

Run it with `mise exec -- python tools/models/ledger-versions-in-force/versions_in_force_model.py`.
It exits 0 where every verdict is the one recorded below.
"""

import sys

FIRST = (0, 10)


def net(events, before=None):
    """Draws less credits, of everything recorded or of what took effect before a position."""
    return sum(a for a, e in events if before is None or e < before)


def ended(versions):
    """Each superseded version's stated amount, with the position its successor is in force from."""
    return [(s, f_next) for (_, s), (f_next, _) in zip(versions, versions[1:])]


def r1(versions, events, x, e):
    "the version held when the draw is recorded"
    return net(events) + x <= versions[-1][1]


def r2(versions, events, x, e):
    "the version in force at the draw's effective position, less everything recorded"
    return net(events) + x <= [s for f, s in versions if f <= e][-1]


def r3(versions, events, x, e):
    "each version bounds what took effect before its successor, and the latest bounds everything"
    return r1(versions, events, x, e) and all(
        net(events, f_next) + x <= s for s, f_next in ended(versions) if e < f_next
    )


def r4(versions, events, x, e):
    "the version in force at the draw's effective position, less only what took effect before it"
    return net(events, e + 1) + x <= [s for f, s in versions if f <= e][-1]


RULES = {"R1": r1, "R2": r2, "R3": r3, "R4": r4}


def within_latest(versions, events):
    """I1. Everything recorded is within the latest version's stated amount."""
    return net(events) <= versions[-1][1]


def within_each_ended(versions, events):
    """I2. What took effect before a version's successor is within that version's stated amount."""
    return all(net(events, f_next) <= s for s, f_next in ended(versions))


def play(rule, history):
    """The verdict on each draw, and whether each invariant held after every step."""
    versions, events, verdicts, i1, i2 = [FIRST], [], "", True, True
    for kind, amount, position in history:
        if kind == "version":
            versions.append((position, amount))
        elif kind == "credit":
            # ponytail: no ceiling and no kind, a credit is applied in full.
            # Add both when LG-29 brings a credit cut under a superseded version.
            events.append((-amount, position))
        elif rule(versions, events, amount, position):
            events.append((amount, position))
            verdicts += "G"
        else:
            verdicts += "R"
        i1 = i1 and within_latest(versions, events)
        i2 = i2 and within_each_ended(versions, events)
    return verdicts, i1, i2


def draw(x, e):
    return ("draw", x, e)


def credit(x, e):
    return ("credit", x, e)


def version(stated, in_force_from):
    return ("version", stated, in_force_from)


# name: (history, what we read the drafting to give, {rule: (verdicts, I1, I2)})
HISTORIES = {
    "E0 no later version, a backdated draw": (
        [draw(4, 50), draw(6, 120), draw(2, 90)],
        "GGR",
        {"R1": ("GGR", True, True), "R2": ("GGR", True, True), "R3": ("GGR", True, True), "R4": ("GGG", False, True)},
    ),
    "E1 raised, every draw forward": (
        [draw(10, 50), version(15, 100), draw(3, 120)],
        "GG",
        {"R1": ("GG", True, True), "R2": ("GG", True, True), "R3": ("GG", True, True), "R4": ("GG", True, True)},
    ),
    "E2 raised, a backdated draw on a spent version": (
        [draw(10, 50), version(15, 100), draw(2, 90)],
        "GR",
        {"R1": ("GG", True, False), "R2": ("GR", True, True), "R3": ("GR", True, True), "R4": ("GR", True, True)},
    ),
    "E3 raised, a backdated draw after a forward one": (
        [draw(4, 50), version(15, 100), draw(9, 120), draw(2, 90)],
        "GGG",
        {"R1": ("GGG", True, True), "R2": ("GGR", True, True), "R3": ("GGG", True, True), "R4": ("GGG", True, True)},
    ),
    "E4 raised by a version recorded late": (
        [draw(10, 50), draw(3, 120), version(15, 100), draw(3, 120)],
        "GRG",
        {"R1": ("GRG", True, True), "R2": ("GRG", True, True), "R3": ("GRG", True, True), "R4": ("GRG", True, True)},
    ),
    "E5 lowered, every draw forward": (
        [draw(4, 50), version(6, 100), draw(3, 120), draw(2, 120)],
        "GRG",
        {"R1": ("GRG", True, True), "R2": ("GRG", True, True), "R3": ("GRG", True, True), "R4": ("GRG", True, True)},
    ),
    "E6 lowered, a backdated draw": (
        [draw(3, 50), version(6, 100), draw(2, 120), draw(4, 90)],
        "GGR",
        {"R1": ("GGR", True, True), "R2": ("GGG", False, True), "R3": ("GGR", True, True), "R4": ("GGG", False, True)},
    ),
    "E7 a credit effective before the version ended": (
        [draw(10, 50), credit(10, 80), version(15, 100), draw(2, 90)],
        "GG",
        {"R1": ("GG", True, True), "R2": ("GG", True, True), "R3": ("GG", True, True), "R4": ("GG", True, True)},
    ),
    "E8 a credit effective after the version ended": (
        [draw(10, 50), version(15, 100), credit(10, 120), draw(2, 90)],
        "GR",
        {"R1": ("GG", True, False), "R2": ("GG", True, False), "R3": ("GR", True, True), "R4": ("GR", True, True)},
    ),
    "E9 three versions": (
        [draw(10, 50), version(15, 100), draw(5, 150), version(20, 200), draw(2, 90), draw(2, 160), draw(2, 210)],
        "GGRRG",
        {"R1": ("GGGGR", True, False), "R2": ("GGRRG", True, True), "R3": ("GGRRG", True, True), "R4": ("GGRRG", True, True)},
    ),
    "E10 lowered below what is drawn": (
        [draw(8, 50), version(6, 100), draw(1, 120)],
        "GR",
        {"R1": ("GR", False, True), "R2": ("GR", False, True), "R3": ("GR", False, True), "R4": ("GR", False, True)},
    ),
}


def main():
    wrong = 0
    print(f"{'history':50} {'drafting':9}" + "".join(f"{name:14}" for name in RULES))
    for name, (history, drafting, expected) in HISTORIES.items():
        row = f"{name:50} {drafting:9}"
        for rule_name, rule in RULES.items():
            got = play(rule, history)
            wrong += got != expected[rule_name]
            verdicts, i1, i2 = got
            row += f"{verdicts + ('' if i1 else ' !I1') + ('' if i2 else ' !I2'):14}"
        print(row)
    for rule_name in RULES:
        differs = [n.split()[0] for n, (_, d, x) in HISTORIES.items() if x[rule_name][0] != d]
        broken = [n.split()[0] for n, (_, _, x) in HISTORIES.items() if not (x[rule_name][1] and x[rule_name][2])]
        print(f"{rule_name}: differs from the drafting in {differs or 'none'}, an invariant broken in {broken or 'none'}")
    print("WRONG" if wrong else "every verdict is the one recorded")
    return 1 if wrong else 0


if __name__ == "__main__":
    sys.exit(main())
