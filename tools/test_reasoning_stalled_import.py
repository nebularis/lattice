# SPDX-License-Identifier: MPL-2.0

"""A reasoner call neither fetches an import nor hangs on one (TD-31). The import points at a
local listener that accepts a connection and never answers, which stalls a TLS handshake for
as long as the connection is held. Needs a testkit jar built after the fix."""

from __future__ import annotations

import socket
import sys
import threading
from pathlib import Path

import pytest
from rdflib import Graph

sys.path.insert(0, str(Path(__file__).resolve().parent / "mork_compilers" / "src"))

from mork_compilers import reasoning  # noqa: E402


@pytest.mark.skipif(not reasoning.available(), reason="reasoning-testkit jar not built")
def test_a_stalled_import_is_not_fetched(monkeypatch) -> None:
    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen()
    held: list[socket.socket] = []
    stop = threading.Event()

    def hold() -> None:
        server.settimeout(0.2)
        while not stop.is_set():
            try:
                held.append(server.accept()[0])
            except OSError:
                pass

    threading.Thread(target=hold, daemon=True).start()
    monkeypatch.setattr(reasoning, "TIMEOUT", 60)
    try:
        graph = Graph().parse(format="turtle", data=(
            "@prefix owl: <http://www.w3.org/2002/07/owl#> .\n"
            f"<https://example.org/stalled> a owl:Ontology ; owl:imports <https://127.0.0.1:{server.getsockname()[1]}/x> .\n"))
        assert reasoning.run("consistent", graphs=[graph]) is True
        assert held == [], "the testkit connected to the import"
    finally:
        stop.set()
        server.close()
        for connection in held:
            connection.close()
