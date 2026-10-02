"""UTF-16 code unit offsets (plan WA6 section 2.5): Java and TypeScript strings already count this
way, Python strings count code points, so every offset crossing the boundary is converted here."""

from __future__ import annotations


def utf16_len(text: str) -> int:
    return len(text.encode("utf-16-le")) // 2


def utf16_index(text: str, code_point_index: int) -> int:
    return utf16_len(text[:code_point_index])
