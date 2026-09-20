"""Small deterministic text-template helpers."""

from __future__ import annotations


def render(title: str, sections: list[tuple[str, str]]) -> str:
    output = [f"# {title}", ""]
    for heading, text in sections:
        output.extend((f"## {heading}", text.strip(), ""))
    return "\n".join(output).rstrip() + "\n"