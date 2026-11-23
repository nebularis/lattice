# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""What a record of a change of terms adds to the read of a balance, held four ways, on Oxigraph, Jena and rdflib (ADR-A124, LG-32, LG-Q52).

The ledger layer lets an account come under a later version of its account definition. The record of that is a supersession, and what it is written on is LG-Q52 of
`docs/developer/sketches/ledger-definition-versions-in-force.md`. The layer declares no supersession term yet, so this benchmark declares its own under the prefix `b:`
(`https://example.org/ledger-supersession-read#`): `b:Supersession`, `b:supersedingVersion`, `b:account` and `b:owner`. Every other term is the layer's.

One owner and its ledger. The account tree has 15 definitions: an annual cap, an aggregate under it, 3 sections under the aggregate and 10 sublimits under the sections (4, 3
and 3). The first sublimit is keyed by site, so with S sites it has S accounts, each part of its section's account. Every other definition has one account, so S = 1000 gives
1,014 accounts. Each definition is versioned (a version node, a persistent identity, a stated amount, and a parent version except for the cap) and each account names the
version it opened under. N events fall on random leaf accounts, four in five a debit, from a fixed seed. Each event is one pass with a revision one more than the last and a
position equal to its index, and writes one posting carrying the running balance of its account (`ldg:runningBalance`). K changes of terms fall at evenly spaced revisions. Each
raises the stated amount of the aggregate and of the 13 definitions below it, which is 14 later versions, each naming the later version of its parent and linked from the version
before by `fnd:supersededBy`. A change is written in a pass of its own, which moves the revision by one, and is in force from the position after the event it follows.

The same history is held four ways.

* **per-account**. A change writes one record for each account reached (5 triples: type, account, pass, effective position, later version).
* **per-account-with-balance**. As per-account, and each record states the account's balance after it (6 triples), so the latest record or posting on an account gives its balance.
* **per-version**. A change writes one record for each later version (5 triples: type, owner, pass, effective position, later version).
* **per-pass**. A change writes one record (4 triples and one edge for each later version).

The reads, each timed over a fixed sample of accounts, at least 30 repetitions, median and 95th percentile.

* **V**. The stated amount in force for one account at a revision. From the records on the account (per-account), or from the account's definition to its identity, to the
  later versions of that identity that the owner's records name, taking the one written at the greatest revision, and the account's own version where there is none (per-version
  and per-pass).
* **R1**. A leaf's balance now, from its latest posting's running balance plus the stated amount in force now less the stated amount in force when the posting was written. Under
  per-account-with-balance, the balance on the latest of the account's postings and records.
* **R2**. The same as of a quarter, a half and three quarters of the stream's revisions.
* **R3**. An ancestor's balance now (a section, the aggregate and the cap): its stated amount in force now, less the debits and plus the credits of every posting in its subtree.
* **B**. The stated amount in force now for every account, in one query.

**Pass criterion.** A plain model computes every balance and stated amount from the event stream alone. Every read, under every variant, on every engine, at every sampled account
and point, equals the model's value, so all four variants agree. The stored triples, and the triples a change of terms writes, have the count the arithmetic gives. A wrong value
fails the run and names the variant, the engine, the account and the two values. **Time never fails it.** Timings go to `report.md` and `report.json` here, generated and git-ignored.

Run `mise run check:ledger-supersession-read`. `LEDGER_SUPERSESSION_QUICK=1` runs the smallest size only, `LEDGER_SUPERSESSION_MAX` caps the events, `LEDGER_SUPERSESSION_ENGINES`
(a comma list of oxigraph, jena, rdflib) picks engines and `LEDGER_SUPERSESSION_REPS` sets the repetitions (default 30). Oxigraph is persisted to a temporary directory that is
removed when the run ends, including on failure. Jena runs when its test kit jar is built (`mise run bootstrap:sparql-testkit`)."""

from __future__ import annotations

import bisect
import gc
import json
import math
import os
import platform
import random
import statistics
import sys
import tempfile
import time
import traceback
import zipfile
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

import pyoxigraph as ox
import rdflib

HERE = Path(__file__).resolve().parent
LDG = "https://www.nebularis.org/neuro-semantic/lattice/ledger#"
FND = "https://www.nebularis.org/neuro-semantic/lattice/foundation#"
QNT = "https://www.nebularis.org/neuro-semantic/lattice/quantification#"
B = "https://example.org/ledger-supersession-read#"
XSD = "http://www.w3.org/2001/XMLSchema#"
RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
RDFS_COMMENT = "http://www.w3.org/2000/01/rdf-schema#comment"

SIZES = (2_000, 20_000)
CHANGES = (0, 1, 10)
SITES = 1000
VARIANTS = ("per-account", "per-account-with-balance", "per-version", "per-pass")
PER_ACCOUNT = ("per-account", "per-account-with-balance")
ENGINES = ("oxigraph", "jena", "rdflib")
READS = ("V", "R1", "R2", "R3", "B")
REPS = 30
SEED = 20261123
STEP = 1_000_003  # what a change of terms adds to each stated amount
OWNER, LEDGER, SPACE, OWNER_KIND, POLICY, POLICY_IDENTITY, PROFILE = (f"urn:bench:{x}" for x in ("owner", "ledger", "space", "owner-kind", "policy", "policy-identity", "profile"))
EVENT_TRIPLES, PASS_TRIPLES = 9, 3  # a posting is 9 triples and its pass 3
SHARED_TRIPLES = 8  # the ledger (4) and the merge policy (4)


class WrongResult(AssertionError):
    """A value that is not the model's, or a triple count that is not the arithmetic's. The one way the check fails."""


def release_store() -> None:
    """Let go of an on-disk store before its folder is removed (see `benchmark/ledger-posting-cost/check.py`). A failing run's traceback keeps the finished frames alive, so clear them."""
    traceback.clear_frames(sys.exc_info()[2])
    gc.collect()


# ---- the tree and the stream ------------------------------------------------------------------------------------------------------------------------------------------

DEFS = [("cap", None), ("agg", "cap"), ("sec0", "agg"), ("sec1", "agg"), ("sec2", "agg"),
        ("sub0", "sec0"), ("sub1", "sec0"), ("sub2", "sec0"), ("sub3", "sec0"), ("sub4", "sec1"), ("sub5", "sec1"), ("sub6", "sec1"), ("sub7", "sec2"), ("sub8", "sec2"), ("sub9", "sec2")]
DEF_INDEX = {name: i for i, (name, _) in enumerate(DEFS)}
KEYED = "sub0"  # the definition keyed by site
BASE = {"cap": 10**12, "agg": 10**11, **{f"sec{s}": 10**10 + s * 10**7 for s in range(3)}, **{f"sub{k}": 10**9 + k * 1_234_567 for k in range(10)}}
REACHED_DEFS = len(DEFS) - 1  # a change reaches every definition but the cap


@dataclass(frozen=True)
class Account:
    iri: str
    definition: str
    parent: int | None  # index in the account list
    key: str | None = None


def build_accounts(sites: int = SITES) -> list[Account]:
    """The cap, the aggregate and the sections first, then each plain sublimit, then the sites, so a parent precedes its child."""
    accounts = [Account("urn:bench:acct/cap", "cap", None), Account("urn:bench:acct/agg", "agg", 0)]
    for s in range(3):
        accounts.append(Account(f"urn:bench:acct/sec{s}", f"sec{s}", 1))
    first = {f"sec{s}": 2 + s for s in range(3)}
    parent_def = dict(DEFS)
    for name, parent in DEFS[5:]:
        if name != KEYED:
            accounts.append(Account(f"urn:bench:acct/{name}", name, first[parent]))
    for site in range(sites):
        accounts.append(Account(f"urn:bench:acct/{KEYED}/site{site:04d}", KEYED, first[parent_def[KEYED]], f"site{site:04d}"))
    return accounts


def leaves_of(accounts: list[Account]) -> list[int]:
    parents = {a.parent for a in accounts}
    return [i for i in range(len(accounts)) if i not in parents]


def chain(accounts: list[Account], index: int) -> list[int]:
    """The account and every ancestor, the account first."""
    out = [index]
    while accounts[out[-1]].parent is not None:
        out.append(accounts[out[-1]].parent)
    return out


def change_ends(count: int, changes: int) -> list[int]:
    """The event each change of terms follows, evenly spaced inside the stream."""
    return [j * count // (changes + 1) for j in range(1, changes + 1)]


@dataclass
class Model:
    """Every balance and stated amount by the plainest arithmetic, from the event stream alone."""

    accounts: list[Account]
    count: int
    changes: int
    stream: list[tuple[int, bool, int]]  # (leaf, is a debit, amount) for events 1 to count
    ends: list[int]
    change_revs: list[int]  # the revision of each change's pass
    event_revs: list[int]  # the revision of event i, at index i - 1
    postings: dict[int, list[tuple[int, int]]]  # leaf -> (revision, running balance after)
    revs: dict[int, list[int]]  # leaf -> revisions of its postings
    cumulative: dict[int, list[int]]  # leaf -> signed sum of its postings up to each
    subtree: list[int]  # signed sum of every posting in the account's subtree, at the end
    snapshots: list[list[int]]  # subtree sums just after the event each change follows

    @property
    def now(self) -> int:
        return self.count + self.changes

    def stated(self, definition: str, revision: int) -> int:
        """The stated amount in force for a definition at a revision, from the changes written by then."""
        if definition == "cap":
            return BASE[definition]
        return BASE[definition] + STEP * bisect.bisect_right(self.change_revs, revision)

    def balance(self, index: int, revision: int) -> int:
        """A leaf's balance as of a revision."""
        revs = self.revs.get(index, [])
        cut = bisect.bisect_right(revs, revision)
        signed = self.cumulative[index][cut - 1] if cut else 0
        return self.stated(self.accounts[index].definition, revision) + signed

    def posting_at(self, index: int, revision: int) -> tuple[int, int] | None:
        """(revision, running balance) of the leaf's latest posting at or before the revision."""
        revs = self.revs.get(index, [])
        cut = bisect.bisect_right(revs, revision)
        return self.postings[index][cut - 1] if cut else None


def build_model(count: int, changes: int, accounts: list[Account]) -> Model:
    rng = random.Random(SEED)
    leaves = leaves_of(accounts)
    stream = [(rng.choice(leaves), rng.random() >= 0.2, rng.randint(1, 1000)) for _ in range(count)]
    ends = change_ends(count, changes)
    change_revs = [e + j for j, e in enumerate(ends, start=1)]
    m = Model(accounts, count, changes, stream, ends, change_revs, [], {}, {}, {}, [0] * len(accounts), [])
    after = {e: j for j, e in enumerate(ends, start=1)}
    done = 0
    for i, (leaf, debit, amount) in enumerate(stream, start=1):
        rev = i + done
        m.event_revs.append(rev)
        signed = -amount if debit else amount
        for a in chain(accounts, leaf):
            m.subtree[a] += signed
        cumulative = m.cumulative.setdefault(leaf, [])
        total = (cumulative[-1] if cumulative else 0) + signed
        cumulative.append(total)
        m.revs.setdefault(leaf, []).append(rev)
        m.postings.setdefault(leaf, []).append((rev, m.stated(accounts[leaf].definition, rev) + total))
        if i in after:
            done += 1
            m.snapshots.append(list(m.subtree))
    return m


# ---- the triples ------------------------------------------------------------------------------------------------------------------------------------------------------

def I(iri: str) -> tuple[str, str]:
    return ("i", iri)


def D(value: int) -> tuple[str, str]:
    return ("d", str(value))


def NN(value: int) -> tuple[str, str]:
    return ("n", str(value))


def version_iri(name: str, k: int) -> str:
    return f"urn:bench:def/{name}/v{k}"


def version_triples(name: str, k: int) -> list[tuple]:
    """Version k of a definition, 9 triples, one more for a parent, five more for the aggregate's comment and ceiling, and one for the link from the version before."""
    v, ident, q = version_iri(name, k), f"urn:bench:def/{name}", f"urn:bench:def/{name}/v{k}/stated"
    parent = dict(DEFS)[name]
    amount = BASE[name] + (STEP * (k - 1) if name != "cap" else 0)
    out = [(v, RDF_TYPE, I(LDG + "AccountDefinition")), (v, FND + "hasIdentity", I(ident)), (v, LDG + "statedAmount", I(q)),
           (q, RDF_TYPE, I(QNT + "Quantity")), (q, QNT + "onSpace", I(SPACE)), (q, QNT + "numericValue", D(amount)),
           (v, LDG + "unitOfAccount", I(SPACE)), (v, LDG + "admitsOwnerKind", I(OWNER_KIND)), (v, LDG + "mergePolicy", I(POLICY))]
    if parent:
        out.append((v, LDG + "partOf", I(version_iri(parent, k))))
    if name == "agg":
        c = f"urn:bench:def/{name}/v{k}/ceiling"
        out += [(v, RDFS_COMMENT, ("s", "The annual aggregate.")), (v, LDG + "creditCeiling", I(c)), (c, RDF_TYPE, I(QNT + "Quantity")), (c, QNT + "onSpace", I(SPACE)), (c, QNT + "numericValue", D(amount))]
    if k > 1:
        out.append((version_iri(name, k - 1), FND + "supersededBy", I(v)))
    return out


def pass_iri(revision: int) -> str:
    return f"urn:bench:pass/{revision}"


def pass_triples(revision: int, position: int) -> list[tuple]:
    p = pass_iri(revision)
    return [(p, RDF_TYPE, I(LDG + "Pass")), (p, LDG + "passPosition", NN(position)), (p, LDG + "passRevision", NN(revision))]


def acct_name(a: Account) -> str:
    return a.iri.rsplit("urn:bench:acct/", 1)[1]


def common_triples(m: Model) -> list[tuple]:
    """Everything every variant holds: the shared nodes, the first version of every definition, the accounts, and the passes and postings of the events."""
    out = [(LEDGER, RDF_TYPE, I(LDG + "Ledger")), (LEDGER, LDG + "forOwner", I(OWNER)), (LEDGER, LDG + "ledgerProfile", I(PROFILE)), (LEDGER, LDG + "revision", NN(m.now)),
           (POLICY, RDF_TYPE, I(LDG + "MergePolicy")), (POLICY, FND + "hasIdentity", I(POLICY_IDENTITY)), (POLICY, LDG + "mergeRule", I(LDG + "Refuse")),
           (POLICY_IDENTITY, RDF_TYPE, I(FND + "PersistentIdentity"))]
    for name, _ in DEFS:
        out.append((f"urn:bench:def/{name}", RDF_TYPE, I(FND + "PersistentIdentity")))
        out += version_triples(name, 1)
    for a in m.accounts:
        out += [(a.iri, RDF_TYPE, I(LDG + "Account")), (a.iri, LDG + "ofDefinition", I(version_iri(a.definition, 1))), (a.iri, LDG + "forOwner", I(OWNER))]
        if a.parent is not None:
            out.append((a.iri, LDG + "partOfAccount", I(m.accounts[a.parent].iri)))
        if a.key:
            out.append((a.iri, LDG + "accountKey", ("s", a.key)))
    for i, (leaf, debit, amount) in enumerate(m.stream, start=1):
        rev = m.event_revs[i - 1]
        x = f"urn:bench:posting/{rev}"
        out += pass_triples(rev, i)
        out += [(x, RDF_TYPE, I(LDG + "Posting")), (x, LDG + "onAccount", I(m.accounts[leaf].iri)), (x, LDG + "inPass", I(pass_iri(rev))), (x, LDG + "effectivePosition", NN(i)),
                (x, LDG + "recordedPosition", NN(i)), (x, LDG + "microPosition", NN(0)), (x, LDG + "direction", I(LDG + ("Debit" if debit else "Credit"))),
                (x, LDG + "amountValue", D(amount)), (x, LDG + "runningBalance", D(m.postings[leaf][bisect.bisect_left(m.revs[leaf], rev)][1]))]
    return out


def change_triples(m: Model, variant: str, j: int) -> tuple[list[tuple], list[tuple]]:
    """(the configuration and pass a change of terms writes, the records it writes), the same configuration and pass under every variant. j counts from 1."""
    rev, end, k = m.change_revs[j - 1], m.ends[j - 1], j + 1
    position = end + 1  # in force from the position after the event the change follows
    config = pass_triples(rev, position)
    for name, _ in DEFS[1:]:
        config += version_triples(name, k)
    p = I(pass_iri(rev))
    records = []
    if variant in PER_ACCOUNT:
        for index, a in enumerate(m.accounts):
            if a.definition == "cap":
                continue
            r = f"urn:bench:supersession/{j}/{acct_name(a)}"
            records += [(r, RDF_TYPE, I(B + "Supersession")), (r, B + "account", I(a.iri)), (r, LDG + "inPass", p), (r, LDG + "effectivePosition", NN(position)),
                        (r, B + "supersedingVersion", I(version_iri(a.definition, k)))]
            if variant == "per-account-with-balance":
                records.append((r, LDG + "runningBalance", D(m.stated(a.definition, rev) + m.snapshots[j - 1][index])))
    elif variant == "per-version":
        for name, _ in DEFS[1:]:
            r = f"urn:bench:supersession/{j}/{name}"
            records += [(r, RDF_TYPE, I(B + "Supersession")), (r, B + "owner", I(OWNER)), (r, LDG + "inPass", p), (r, LDG + "effectivePosition", NN(position)),
                        (r, B + "supersedingVersion", I(version_iri(name, k)))]
    else:
        r = f"urn:bench:supersession/{j}"
        records += [(r, RDF_TYPE, I(B + "Supersession")), (r, B + "owner", I(OWNER)), (r, LDG + "inPass", p), (r, LDG + "effectivePosition", NN(position))]
        records += [(r, B + "supersedingVersion", I(version_iri(name, k))) for name, _ in DEFS[1:]]
    return config, records


def accounts_reached(sites: int) -> int:
    return len(build_accounts(sites)) - 1


def expected_record_triples(variant: str, sites: int = SITES) -> int:
    """The triples one change of terms writes in its records, by the variant's arithmetic."""
    return {"per-account": 5 * accounts_reached(sites), "per-account-with-balance": 6 * accounts_reached(sites),
            "per-version": 5 * REACHED_DEFS, "per-pass": 4 + REACHED_DEFS}[variant]


def config_per_change() -> int:
    """The later versions: 11 triples each, and 16 for the aggregate, which also states a comment and a credit ceiling."""
    return (REACHED_DEFS - 1) * 11 + 16


def expected_change_triples(variant: str, sites: int = SITES) -> int:
    """The records, the configuration and the pass of one change of terms."""
    return expected_record_triples(variant, sites) + config_per_change() + PASS_TRIPLES


def expected_stored(variant: str, count: int, changes: int, sites: int = SITES) -> int:
    first_versions = 10 + 16 + (REACHED_DEFS - 1) * 11  # a definition's first version and its identity, 10 for the cap and 16 for the aggregate
    reached = accounts_reached(sites)
    accounts = 3 + 4 * reached + sites  # each account 3 triples, 1 more for a parent, 1 more for a site's key
    return SHARED_TRIPLES + first_versions + accounts + count * (PASS_TRIPLES + EVENT_TRIPLES) + changes * expected_change_triples(variant, sites)


# ---- the engines ------------------------------------------------------------------------------------------------------------------------------------------------------

def jena_version() -> str:
    import lattice_testing_jena as j

    with zipfile.ZipFile(j.jar()) as z:
        text = z.read("META-INF/maven/org.apache.jena/jena-arq/pom.properties").decode()
    return next(line.split("=", 1)[1] for line in text.splitlines() if line.startswith("version="))


def jena_available() -> bool:
    try:
        import lattice_testing_jena as j

        return j.available()
    except ImportError:
        return False


def available_engines() -> dict[str, str]:
    """The engines that can run here, with their versions, and why each other did not."""
    return {"oxigraph": ox.__version__, **({"jena": jena_version()} if jena_available() else {}), "rdflib": rdflib.__version__}


def datatype(kind: str) -> str:
    return XSD + {"d": "decimal", "n": "nonNegativeInteger"}[kind]


class OxigraphBackend:
    def __init__(self, directory: str):
        self.store = ox.Store(directory)

    def term(self, o):
        return ox.NamedNode(o[1]) if o[0] == "i" else ox.Literal(o[1]) if o[0] == "s" else ox.Literal(o[1], datatype=ox.NamedNode(datatype(o[0])))

    def quads(self, triples):
        return (ox.Quad(ox.NamedNode(s), ox.NamedNode(p), self.term(o), ox.DefaultGraph()) for s, p, o in triples)

    def load(self, triples) -> None:
        self.store.bulk_extend(self.quads(triples))
        self.store.flush()

    def write(self, triples) -> None:
        self.store.extend(self.quads(triples))
        self.store.flush()

    def select(self, text: str) -> list[tuple]:
        return [tuple(None if t is None else t.value for t in row) for row in self.store.query(text)]

    def count(self) -> int:
        return len(self.store)

    def close(self) -> None:
        self.store = None


class RdflibBackend:
    def __init__(self, directory: str):
        self.graph = rdflib.Graph()

    def term(self, o):
        return rdflib.URIRef(o[1]) if o[0] == "i" else rdflib.Literal(o[1]) if o[0] == "s" else rdflib.Literal(o[1], datatype=rdflib.URIRef(datatype(o[0])))

    def load(self, triples) -> None:
        self.graph.addN((rdflib.URIRef(s), rdflib.URIRef(p), self.term(o), self.graph) for s, p, o in triples)

    write = load

    def select(self, text: str) -> list[tuple]:
        return [tuple(None if t is None else str(t) for t in row) for row in self.graph.query(text)]

    def count(self) -> int:
        return len(self.graph)

    def close(self) -> None:
        self.graph = None


class JenaBackend:
    def __init__(self, directory: str):
        from lattice_testing_jena import JenaStore

        self.store = JenaStore()

    def term(self, o):
        return rdflib.URIRef(o[1]) if o[0] == "i" else rdflib.Literal(o[1]) if o[0] == "s" else rdflib.Literal(o[1], datatype=rdflib.URIRef(datatype(o[0])))

    def load(self, triples) -> None:
        batch = []
        for s, p, o in triples:
            batch.append((rdflib.URIRef(s), rdflib.URIRef(p), self.term(o), None))
            if len(batch) >= 20_000:
                self.store.add_all(batch)
                batch = []
        self.store.add_all(batch)

    write = load

    def select(self, text: str) -> list[tuple]:
        names, rows = self.store.solutions(text)
        return [tuple(None if n not in r else str(r[n]) for n in names) for r in rows]

    def count(self) -> int:
        (row,) = self.select("SELECT (COUNT(*) AS ?n) WHERE { ?s ?p ?o }")
        return int(row[0])

    def close(self) -> None:
        self.store.close()


BACKENDS = {"oxigraph": OxigraphBackend, "jena": JenaBackend, "rdflib": RdflibBackend}


# ---- the reads --------------------------------------------------------------------------------------------------------------------------------------------------------

PREFIX = f"PREFIX ldg: <{LDG}> PREFIX fnd: <{FND}> PREFIX qnt: <{QNT}> PREFIX b: <{B}> "


def integer(text: str) -> int:
    return int(Decimal(text))


def own_amount(db, account: str) -> int:
    """The stated amount of the version the account opened under. The account is the subject, so this is a seek."""
    (row,) = db.select(f"{PREFIX}SELECT ?amt WHERE {{ <{account}> ldg:ofDefinition ?d . ?d ldg:statedAmount ?q . ?q qnt:numericValue ?amt }}")
    return integer(row[0])


def stated_in_force(db, variant: str, account: str, revision: int) -> int:
    """V, the stated amount in force for an account at a revision, and the account's own version where no record of a later one was written by then."""
    if variant in PER_ACCOUNT:
        rows = db.select(f"{PREFIX}SELECT ?amt WHERE {{ ?r b:account <{account}> ; ldg:inPass ?p ; b:supersedingVersion ?v . ?p ldg:passRevision ?rev . FILTER(?rev <= {revision}) "
                         "?v ldg:statedAmount ?q . ?q qnt:numericValue ?amt } ORDER BY DESC(?rev) LIMIT 1")
    else:
        rows = db.select(f"{PREFIX}SELECT ?amt WHERE {{ <{account}> ldg:ofDefinition ?d . ?d fnd:hasIdentity ?id . ?v fnd:hasIdentity ?id . "
                         f"?r b:supersedingVersion ?v ; b:owner <{OWNER}> ; ldg:inPass ?p . ?p ldg:passRevision ?rev . FILTER(?rev <= {revision}) "
                         "?v ldg:statedAmount ?q . ?q qnt:numericValue ?amt } ORDER BY DESC(?rev) LIMIT 1")
    return integer(rows[0][0]) if rows else own_amount(db, account)


def balance_at(db, variant: str, account: str, revision: int) -> int:
    """R1 and R2, a leaf's balance as of a revision. The latest posting is found by the account as an object, since a posting's name is not computable from the account."""
    if variant == "per-account-with-balance":
        rows = db.select(f"{PREFIX}SELECT ?bal WHERE {{ {{ ?x ldg:onAccount <{account}> }} UNION {{ ?x b:account <{account}> }} ?x ldg:inPass ?p ; ldg:runningBalance ?bal . "
                         f"?p ldg:passRevision ?rev . FILTER(?rev <= {revision}) }} ORDER BY DESC(?rev) LIMIT 1")
        return integer(rows[0][0]) if rows else own_amount(db, account)
    rows = db.select(f"{PREFIX}SELECT ?bal ?rev WHERE {{ ?x ldg:onAccount <{account}> ; ldg:inPass ?p ; ldg:runningBalance ?bal . ?p ldg:passRevision ?rev . "
                     f"FILTER(?rev <= {revision}) }} ORDER BY DESC(?rev) LIMIT 1")
    if not rows:
        return stated_in_force(db, variant, account, revision)
    return integer(rows[0][0]) + stated_in_force(db, variant, account, revision) - stated_in_force(db, variant, account, integer(rows[0][1]))


def ancestor_balance(db, variant: str, account: str, revision: int) -> int:
    """R3, an ancestor's balance now: the stated amount in force, less the debits and plus the credits of every posting in its subtree."""
    (row,) = db.select(f"{PREFIX}SELECT (SUM(?s) AS ?sum) WHERE {{ ?acc ldg:partOfAccount* <{account}> . ?x ldg:onAccount ?acc ; ldg:direction ?d ; ldg:amountValue ?a . "
                       "BIND(IF(?d = ldg:Debit, -?a, ?a) AS ?s) }")
    return stated_in_force(db, variant, account, revision) + (integer(row[0]) if row[0] is not None else 0)


def bulk_in_force(db, variant: str, revision: int) -> dict[str, int]:
    """B, the stated amount in force at a revision for every account, in one query."""
    if variant in PER_ACCOUNT:
        text = (f"{PREFIX}SELECT ?a ?amt WHERE {{ ?a ldg:ofDefinition ?d . ?d ldg:statedAmount ?q1 . ?q1 qnt:numericValue ?amt1 . "
                f"OPTIONAL {{ {{ SELECT ?a (MAX(?rev0) AS ?m) WHERE {{ ?r0 b:account ?a ; ldg:inPass ?p0 . ?p0 ldg:passRevision ?rev0 . FILTER(?rev0 <= {revision}) }} GROUP BY ?a }} "
                "?r2 b:account ?a ; ldg:inPass ?p2 ; b:supersedingVersion ?v2 . ?p2 ldg:passRevision ?m . ?v2 ldg:statedAmount ?q2 . ?q2 qnt:numericValue ?amt2 } "
                "BIND(COALESCE(?amt2, ?amt1) AS ?amt) }")
    else:
        # The greatest revision of each identity is found once, in a subquery, and joined to the accounts whose identity has a record. The accounts whose identity has none are taken
        # in a second branch, by MINUS, which every engine evaluates once. NOT EXISTS for the second branch was 8 s on rdflib and 40 s on Oxigraph, and an OPTIONAL around the
        # subquery was 27 s on rdflib, which evaluates the optional part again for each account.
        records = f"?r b:supersedingVersion ?v ; b:owner <{OWNER}> ; ldg:inPass ?p . ?p ldg:passRevision ?rev . FILTER(?rev <= {revision})"
        text = (f"{PREFIX}SELECT ?a ?amt WHERE {{ {{ {{ SELECT ?id (MAX(?rev) AS ?m) WHERE {{ ?v fnd:hasIdentity ?id . {records} }} GROUP BY ?id }} "
                f"?v2 fnd:hasIdentity ?id . ?r2 b:supersedingVersion ?v2 ; b:owner <{OWNER}> ; ldg:inPass ?p2 . ?p2 ldg:passRevision ?m . ?v2 ldg:statedAmount ?q2 . ?q2 qnt:numericValue ?amt . "
                f"?d fnd:hasIdentity ?id . ?a ldg:ofDefinition ?d }} UNION {{ ?a ldg:ofDefinition ?d . ?d fnd:hasIdentity ?id ; ldg:statedAmount ?q1 . ?q1 qnt:numericValue ?amt . "
                f"MINUS {{ SELECT ?id WHERE {{ ?v fnd:hasIdentity ?id . {records} }} }} }} }}")
    return {row[0]: integer(row[1]) for row in db.select(text)}


# ---- the run ----------------------------------------------------------------------------------------------------------------------------------------------------------

def sample(m: Model) -> list[int]:
    """The leaves read: a site with a posting after the last change, one whose postings all came before it, one with none, the busiest site, and two plain sublimits."""
    last = m.change_revs[-1] if m.changes else 0
    sites = [i for i, a in enumerate(m.accounts) if a.key]
    latest = {i: m.revs[i][-1] for i in sites if i in m.revs}
    picks = [next((i for i in sites if latest.get(i, 0) > last), None),
             next((i for i in sites if i in latest and latest[i] <= last), None) if m.changes else next((i for i in sites if i in latest), None),
             next((i for i in sites if i not in latest), None),
             max(sites, key=lambda i: len(m.revs.get(i, []))),
             next(i for i, a in enumerate(m.accounts) if a.definition == "sub1"), next(i for i, a in enumerate(m.accounts) if a.definition == "sub9")]
    return list(dict.fromkeys(i for i in picks if i is not None))


def percentile(values: list[float], share: float) -> float:
    ordered = sorted(values)
    return ordered[max(math.ceil(share * len(ordered)) - 1, 0)]


@dataclass
class Result:
    engine: str
    variant: str
    events: int
    changes: int
    stored: int
    change_record_triples: int  # what the records of one change write, 0 with no change
    change_total_triples: int  # the records, the configuration and the pass
    write_ms: float | None
    timings: dict[str, dict[str, float]] = field(default_factory=dict)  # read -> {median_ms, p95_ms, n}


def fail(variant: str, engine: str, what: str, got, wanted) -> None:
    raise WrongResult(f"{variant} on {engine}: {what} reads {got}, the model gives {wanted}")


def run_config(engine: str, variant: str, m: Model, common: list[tuple], chunks: list[tuple[list, list]], reps: int, directory: str | None = None) -> Result:
    """Writes the history, writes the last change of terms as a timed write of its own, checks the counts, then reads and checks every sampled value `reps` times."""
    sites = sum(1 for a in m.accounts if a.key)
    stored_expected = expected_stored(variant, m.count, m.changes, sites)
    with tempfile.TemporaryDirectory(prefix="ledger-supersession-read-", dir=directory) as tmp:
        db = BACKENDS[engine](tmp)
        try:
            earlier = list(common)
            for config, records in chunks[:-1]:
                earlier += config + records
            db.load(earlier)
            write_ms = None
            if chunks:
                config, records = chunks[-1]
                if len(records) != expected_record_triples(variant, sites) or len(config) + len(records) != expected_change_triples(variant, sites):
                    raise WrongResult(f"{variant} {m.count} {m.changes}: a change wrote {len(records)} record triples and {len(config) + len(records)} in all, "
                                      f"expected {expected_record_triples(variant, sites)} and {expected_change_triples(variant, sites)}")
                begin = time.perf_counter()
                db.write(config + records)
                write_ms = 1000 * (time.perf_counter() - begin)
            stored = db.count()
            if stored != stored_expected:
                raise WrongResult(f"{variant} on {engine}, {m.count} events, {m.changes} changes: stored {stored} triples, expected {stored_expected}")
            r = Result(engine, variant, m.count, m.changes, stored, expected_record_triples(variant, sites) if m.changes else 0,
                       expected_change_triples(variant, sites) if m.changes else 0, write_ms)
            leaves = sample(m)
            ancestors = [i for i, a in enumerate(m.accounts) if a.definition in ("sec0", "agg", "cap")]
            v_accounts = leaves + ancestors
            points = [m.now * q // 4 for q in (1, 2, 3)]
            now = m.now
            pools: dict[str, list[float]] = {name: [] for name in READS}

            def timed(name: str, call, wanted, what: str) -> None:
                begin = time.perf_counter()
                got = call()
                pools[name].append(1000 * (time.perf_counter() - begin))
                if got != wanted:
                    fail(variant, engine, what, got, wanted)

            for rep in range(reps + 1):  # the first repetition is a warm-up and is checked but not kept
                for i in v_accounts:
                    a = m.accounts[i]
                    timed("V", lambda a=a: stated_in_force(db, variant, a.iri, now), m.stated(a.definition, now), f"V of {acct_name(a)} now")
                for i in leaves:
                    a = m.accounts[i]
                    timed("R1", lambda a=a: balance_at(db, variant, a.iri, now), m.balance(i, now), f"R1 of {acct_name(a)} now")
                    for point in points:
                        timed("R2", lambda a=a, p=point: balance_at(db, variant, a.iri, p), m.balance(i, point), f"R2 of {acct_name(a)} as of revision {point}")
                for i in ancestors:
                    a = m.accounts[i]
                    timed("R3", lambda a=a: ancestor_balance(db, variant, a.iri, now), m.stated(a.definition, now) + m.subtree[i], f"R3 of {acct_name(a)} now")
                wanted = {a.iri: m.stated(a.definition, now) for a in m.accounts}
                begin = time.perf_counter()
                got = bulk_in_force(db, variant, now)
                pools["B"].append(1000 * (time.perf_counter() - begin))
                if got != wanted:
                    bad = next(k for k in wanted if got.get(k) != wanted[k])
                    fail(variant, engine, f"B of {bad}", got.get(bad), wanted[bad])
                if rep == 0:
                    pools = {name: [] for name in READS}
            r.timings = {name: {"median_ms": statistics.median(v), "p95_ms": percentile(v, 0.95), "n": len(v)} for name, v in pools.items()}
        finally:
            db = None
            release_store()
    return r


def run(engines: list[str], sizes=SIZES, changes=CHANGES, reps: int = REPS, sites: int = SITES) -> list[Result]:
    out = []
    for count in sizes:
        accounts = build_accounts(sites)
        for k in changes:
            m = build_model(count, k, accounts)
            common = common_triples(m)
            by_variant = {v: [change_triples(m, v, j) for j in range(1, k + 1)] for v in VARIANTS}
            for engine in engines:
                for variant in VARIANTS:
                    r = run_config(engine, variant, m, common, by_variant[variant], reps)
                    out.append(r)
                    t = r.timings
                    print(f"{engine:8} {variant:24} events {count:6} changes {k:2}  stored {r.stored:8}  change {r.change_record_triples:5}  write "
                          f"{'-' if r.write_ms is None else f'{r.write_ms:8.1f}'} ms  " + "  ".join(f"{n} {t[n]['median_ms']:8.3f}" for n in READS), flush=True)
    return out


# ---- the report -------------------------------------------------------------------------------------------------------------------------------------------------------

def environment(engines: dict[str, str], sites: int, reps: int) -> dict:
    return {"date": time.strftime("%Y-%m-%d"), "python": platform.python_version(), "machine": f"{platform.system()} {platform.machine()}", "engines": engines,
            "sites": sites, "accounts": len(build_accounts(sites)), "repetitions": reps, "seed": SEED, "step": STEP}


def write_report(results: list[Result], env: dict, directory: Path = HERE) -> None:
    (directory / "report.json").write_text(json.dumps({"environment": env, "results": [r.__dict__ for r in results]}, indent=2), encoding="utf-8")
    lines = ["# Ledger supersession read (generated, not committed)", "", "```", json.dumps(env), "```", ""]
    index = {(r.engine, r.variant, r.events, r.changes): r for r in results}
    for engine in dict.fromkeys(r.engine for r in results):
        for count in dict.fromkeys(r.events for r in results):
            lines += [f"## {engine}, {count} events", "", "Median and 95th percentile of each read, in milliseconds.", "",
                      "| variant | K | stored | change records | change total | write ms |" + "".join(f" {n} p50 | {n} p95 |" for n in READS), "|---|---|---|---|---|---|" + "---|---|" * len(READS)]
            for variant in VARIANTS:
                for r in (x for x in results if (x.engine, x.variant, x.events) == (engine, variant, count)):
                    cells = "".join(f" {r.timings[n]['median_ms']:.3f} | {r.timings[n]['p95_ms']:.3f} |" for n in READS)
                    lines.append(f"| {variant} | {r.changes} | {r.stored} | {r.change_record_triples} | {r.change_total_triples} | {'-' if r.write_ms is None else f'{r.write_ms:.1f}'} |{cells}")
            lines += ["", f"Median of each read under per-pass, against per-pass at K = 0 and against per-account at the same K.", "",
                      "| K | " + " | ".join(f"{n} vs K=0 | {n} vs per-account" for n in READS) + " |", "|---|" + "---|---|" * len(READS)]
            for k in (x for x in dict.fromkeys(r.changes for r in results) if x):
                cells = []
                for n in READS:
                    pp, p0, pa = (index.get((engine, v, count, kk)) for v, kk in (("per-pass", k), ("per-pass", 0), ("per-account", k)))
                    for other in (p0, pa):
                        cells.append("-" if not (pp and other) else f"{pp.timings[n]['median_ms'] / other.timings[n]['median_ms']:.2f}")
                lines.append(f"| {k} | " + " | ".join(cells) + " |")
            lines.append("")
    (directory / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    found = available_engines()
    wanted = [e for e in os.environ.get("LEDGER_SUPERSESSION_ENGINES", ",".join(ENGINES)).split(",") if e]
    engines = [e for e in wanted if e in found]
    for e in wanted:
        if e not in found:
            print(f"{e} not run: its test kit is not built or there is no java")
    cap = int(os.environ.get("LEDGER_SUPERSESSION_MAX", SIZES[-1]))
    sizes = [s for s in SIZES if s <= cap] or [cap]
    if os.environ.get("LEDGER_SUPERSESSION_QUICK"):
        sizes = sizes[:1]
    reps = int(os.environ.get("LEDGER_SUPERSESSION_REPS", REPS))
    try:
        results = run(engines, sizes, CHANGES, reps)
    except WrongResult as error:
        print(f"WRONG RESULT: {error}", file=sys.stderr)
        return 1
    write_report(results, environment({e: found[e] for e in engines}, SITES, reps))
    print(f"report written to {HERE / 'report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
