# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""Makes every temporary folder in these tests refuse to be removed while a store in it is open, as Windows does, so a run that fails
on purpose is checked on every platform and not only there. A folder's removal first tries to open the store a second time. RocksDB
holds a lock on an open store, so the second open fails, and the folder's removal fails with it, until the run has let go of the store."""

from __future__ import annotations

import gc
import tempfile

import pyoxigraph as ox
import pytest


class _OpenStoreRefusesRemoval(tempfile.TemporaryDirectory):
    def cleanup(self) -> None:
        try:
            ox.Store(self.name)
        except OSError as error:
            raise AssertionError(f"a store was still open when its folder was removed: {error}") from error
        gc.collect()  # the second store, opened only to prove the first was gone
        super().cleanup()


@pytest.fixture(autouse=True)
def _folders_are_not_removed_under_an_open_store(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tempfile, "TemporaryDirectory", _OpenStoreRefusesRemoval)
