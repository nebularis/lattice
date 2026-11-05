# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""Tests of how an architectural quantum is derived from coupling, on inputs small enough to read."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import quanta  # noqa: E402

KINDS = {"foundation": "substrate", "ledger": "substrate", "mork": "standalone", "capacity": "applied"}
RELEASE = {"foundation", "ledger", "mork"}


def parts(found, identifier):
    return next(q.parts for q in found if q.identifier == identifier)


def test_the_substrate_is_one_quantum_and_a_one_way_dependent_is_its_own():
    found, _ = quanta.data_quanta(KINDS, {("ledger", "foundation"), ("mork", "foundation")}, RELEASE, {})
    assert parts(found, "data/substrate") == ["foundation", "ledger"]
    assert parts(found, "data/mork") == ["mork"]
    assert parts(found, "data/capacity") == ["capacity"]


def test_a_quantum_grows_as_a_dependency_is_added():
    """The substrate depending on a standalone module takes that module into its quantum, since a
    change to it would now reach the substrate."""
    found, straddling = quanta.data_quanta(KINDS, {("ledger", "mork")}, RELEASE, {})
    assert parts(found, "data/substrate") == ["foundation", "ledger", "mork"]
    assert not any(q.identifier == "data/mork" for q in found)
    assert straddling == []


def test_a_release_member_outside_the_substrate_quantum_is_reported():
    """A shared release number is coupling by policy rather than by dependency."""
    _, straddling = quanta.data_quanta(KINDS, {("mork", "foundation")}, RELEASE, {})
    assert straddling == ["mork"]


def compose(**services):
    return {"services": services}


BROKER = {"image": "rabbitmq:3.13"}
STORE = {"image": "stain/jena-fuseki:5.1.0"}


def test_a_shared_store_defeats_a_broker():
    """Two services that talk only through a broker would be separate quanta, but both reading and
    writing one store couples them, and the broker does not undo that."""
    found = quanta.software_quanta("d", compose(
        bus=BROKER, store=STORE,
        service={"environment": {"AMQP": "amqp://bus:5672", "SPARQL": "http://store:3030"}},
        worker={"environment": {"AMQP": "amqp://bus:5672", "SPARQL": "http://store:3030"}},
    ), "deployment/d/docker-compose.yml")
    assert [q.parts for q in found] == [["service", "store", "worker"]]
    assert "broker" in found[0].claim


def test_a_broker_separates_components_nothing_else_couples():
    """The same code deployed with a store each is two quanta, which is why a runtime quantum is a
    property of the deployment rather than of the software."""
    found = quanta.software_quanta("d", compose(
        bus=BROKER,
        service_store=STORE, worker_store={"image": "postgres:16"},
        service={"environment": {"AMQP": "amqp://bus:5672", "DB": "http://service_store:3030"}},
        worker={"environment": {"AMQP": "amqp://bus:5672", "DB": "postgres://worker_store/x"}},
    ), "deployment/d/docker-compose.yml")
    assert sorted(q.parts for q in found) == [["service", "service_store"], ["worker", "worker_store"]]
    assert not any("bus" in q.parts for q in found)


def test_a_synchronous_call_binds_caller_and_callee():
    found = quanta.software_quanta("d", compose(proxy={"depends_on": ["api"]}, api={}), "p")
    assert [q.parts for q in found] == [["api", "proxy"]]


def test_coupling_is_read_from_what_configuration_points_at_not_only_depends_on():
    """The authoring worker reaches its store by a URL and declares no dependency on it."""
    found = quanta.software_quanta("d", compose(
        store=STORE, worker={"depends_on": [], "environment": ["SPARQL=http://store:3030"]},
    ), "p")
    assert [q.parts for q in found] == [["store", "worker"]]
