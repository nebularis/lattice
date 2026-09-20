"""Render curated MTP lenses and validate cassette coverage."""

from __future__ import annotations


def check(lenses: list[dict]) -> list[str]:
    return [f"lens.no-cassette:{lens.get('id', 'unknown')}" for lens in lenses if not lens.get("cassette")]


def render(lens: dict) -> str:
    return f"# {lens['id']}\n\nQuestion: {lens['question']}\n\nRules:\n" + "\n".join(f"- {rule}" for rule in lens.get("rules", [])) + "\n"