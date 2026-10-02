"""A Fuseki Graph Store Protocol client, `urllib.request` only (plan WA7 section "fuseki_gsp.py")."""

from __future__ import annotations

import base64
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional

import rdflib


class GraphNotFound(Exception):
    """Raised when the Graph Store Protocol endpoint has no graph at the requested IRI."""


class FusekiGraphStore:
    """Reads and writes named graphs on one Fuseki dataset via the Graph Store Protocol."""

    def __init__(
        self,
        base_url: str,
        dataset: str,
        user: Optional[str] = None,
        password: Optional[str] = None,
        timeout: int = 10,
    ) -> None:
        self._base_url = base_url[:-1] if base_url.endswith("/") else base_url
        self._dataset = dataset
        self._user = user
        self._password = password
        self._timeout = timeout

    def get_graph(self, graph_iri: str) -> rdflib.Graph:
        request = urllib.request.Request(self._data_url(graph_iri), headers=self._headers({"Accept": "text/turtle"}))
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                body = response.read()
        except urllib.error.HTTPError as error:
            if error.code == 404:
                raise GraphNotFound(graph_iri) from error
            raise
        graph = rdflib.Graph()
        graph.parse(data=body, format="turtle")
        return graph

    def put_graph(self, graph_iri: str, graph: rdflib.Graph) -> None:
        body = graph.serialize(format="turtle").encode("utf-8")
        request = urllib.request.Request(
            self._data_url(graph_iri),
            data=body,
            method="PUT",
            headers=self._headers({"Content-Type": "text/turtle"}),
        )
        with urllib.request.urlopen(request, timeout=self._timeout) as response:
            response.read()

    def _data_url(self, graph_iri: str) -> str:
        query = urllib.parse.urlencode({"graph": graph_iri})
        return f"{self._base_url}/{self._dataset}/data?{query}"

    def _headers(self, headers: dict) -> dict:
        if self._user is not None:
            credentials = f"{self._user}:{self._password or ''}".encode("utf-8")
            headers = {**headers, "Authorization": "Basic " + base64.b64encode(credentials).decode("ascii")}
        return headers
