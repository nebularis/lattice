# SPDX-License-Identifier: MPL-2.0
"""Tests of the licence texts check (ADR-A155)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import check_licences  # noqa: E402


def _tree(tmp_path: Path, files: dict, texts: list) -> Path:
    for name, text in files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    (tmp_path / "LICENSES").mkdir()
    for identifier in texts:
        (tmp_path / "LICENSES" / f"{identifier}.txt").write_text("text\n", encoding="utf-8")
    return tmp_path


def _problems(root: Path) -> list:
    files = [p for p in root.rglob("*") if p.is_file()]
    return check_licences.problems(root, files, root / "LICENSES")


def test_headers_of_each_comment_form_and_reuse_annotations_are_read(tmp_path):
    root = _tree(tmp_path, {
        "a.md": "<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->\n# A\n",
        "b.py": "# SPDX-License-Identifier: MPL-2.0\n",
        "c.java": "/* SPDX-License-Identifier: MIT */\n",
        "REUSE.toml": 'version = 1\n[[annotations]]\npath = ["x"]\nSPDX-License-Identifier = "LicenseRef-Other OR MPL-2.0"\n',
    }, ["CC-BY-SA-4.0", "MPL-2.0", "MIT", "LicenseRef-Other"])
    assert _problems(root) == []


def test_an_identifier_with_no_text_is_reported(tmp_path):
    root = _tree(tmp_path, {"b.py": "# SPDX-License-Identifier: MPL-2.0\n", "c.py": "# SPDX-License-Identifier: Apache-2.0\n"}, ["MPL-2.0"])
    assert _problems(root) == ["Apache-2.0 is named by 1 file(s), such as c.py, and has no text at LICENSES/Apache-2.0.txt"]


def test_a_text_no_file_names_is_reported(tmp_path):
    root = _tree(tmp_path, {"b.py": "# SPDX-License-Identifier: MPL-2.0\n"}, ["MPL-2.0", "MIT"])
    assert _problems(root) == ["LICENSES/MIT.txt is the text of a licence no tracked file names"]


def test_a_mention_below_the_header_is_not_a_header(tmp_path):
    body = "# SPDX-License-Identifier: MPL-2.0\n" + "\n" * 20 + "a file states SPDX-License-Identifier: GPL-3.0 in its header\n"
    root = _tree(tmp_path, {"b.py": body}, ["MPL-2.0"])
    assert _problems(root) == []
