# src/spc/verify/jena_client.py
"""
HTTP client for Apache Jena Fuseki.
Used by the verification pipeline and the projection materialiser.
"""

from __future__ import annotations
import requests
from pathlib import Path
from typing import Optional


class JenaClient:
    """Client for Jena Fuseki SPARQL endpoint."""

    def __init__(self, fuseki_url: str = "http://localhost:3030",
                 dataset: str = "spc"):
        self.fuseki_url = fuseki_url.rstrip("/")
        self.dataset = dataset
        self.query_url = f"{self.fuseki_url}/{dataset}/query"
        self.update_url = f"{self.fuseki_url}/{dataset}/update"
        self.data_url = f"{self.fuseki_url}/{dataset}/data"
        self.shacl_url = f"{self.fuseki_url}/{dataset}/shacl"

    def upload_graph(self, turtle_path: Path,
                     graph_name: Optional[str] = None) -> None:
        """Upload a Turtle file to the dataset."""
        headers = {"Content-Type": "text/turtle"}
        url = self.data_url
        if graph_name:
            url += f"?graph={graph_name}"
        with open(turtle_path, "rb") as f:
            resp = requests.post(url, data=f, headers=headers)
        resp.raise_for_status()

    def upload_turtle_string(self, turtle: str,
                              graph_name: Optional[str] = None) -> None:
        """Upload Turtle content directly."""
        headers = {"Content-Type": "text/turtle"}
        url = self.data_url
        if graph_name:
            url += f"?graph={graph_name}"
        resp = requests.post(url, data=turtle.encode(), headers=headers)
        resp.raise_for_status()

    def sparql_query(self, query: str,
                     accept: str = "application/sparql-results+json") -> dict:
        """Execute a SPARQL SELECT/ASK query."""
        resp = requests.post(
            self.query_url,
            data=query.encode(),
            headers={
                "Content-Type": "application/sparql-query",
                "Accept": accept,
            },
        )
        resp.raise_for_status()
        return resp.json()

    def sparql_construct(self, query: str,
                          accept: str = "text/turtle") -> str:
        """Execute a SPARQL CONSTRUCT query."""
        resp = requests.post(
            self.query_url,
            data=query.encode(),
            headers={
                "Content-Type": "application/sparql-query",
                "Accept": accept,
            },
        )
        resp.raise_for_status()
        return resp.text

    def sparql_update(self, update: str) -> None:
        """Execute a SPARQL UPDATE."""
        resp = requests.post(
            self.update_url,
            data=update.encode(),
            headers={"Content-Type": "application/sparql-update"},
        )
        resp.raise_for_status()

    def validate_shacl(self, shapes_graph: Optional[str] = None) -> dict:
        """
        Run SHACL validation. Requires Fuseki configured with SHACL
        support or a separate SHACL validation service.
        """
        # Fuseki doesn't have built-in SHACL validation in the standard
        # distribution. We use a SPARQL-based approach or call the
        # Jena SHACL command-line tool.
        # For the pipeline, we use the jena-shacl CLI wrapper.
        raise NotImplementedError(
            "Use shacl_verifier.py for SHACL validation via CLI")

    def drop_dataset(self) -> None:
        """Drop all data in the dataset."""
        self.sparql_update("DROP ALL")

    def count_triples(self) -> int:
        """Count triples in the default graph."""
        result = self.sparql_query(
            "SELECT (COUNT(*) AS ?count) WHERE { ?s ?p ?o }")
        bindings = result["results"]["bindings"]
        return int(bindings[0]["count"]["value"]) if bindings else 0