# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""A fixture with its patch log taken away, for the tests of the receipt-only writes. Since H2.6d a profile that declares `dal:PatchLog`
selects the patch-log variants of create, replace and tombstone, and `dal:ReceiptOnly` is refused for a composite family. The receipt-only
templates of a composite family are then reached with `dal:SnapshotPerRevision`, which no template honours and which compiles with a warning. The
tests of the sweep, the lifecycle and the guard do not depend on the receipt model, so they run on the example with that one dimension changed."""

from __future__ import annotations

from persistence import witness
from persistence.namespaces import DAL


def receipt_only(path):
    """``path`` loaded as ``witness._load_fixture`` loads it, with every ``dal:PatchLog`` replaced by ``dal:SnapshotPerRevision``."""
    graph = witness._load_fixture(path)
    for subject in list(graph.subjects(DAL.receiptModel, DAL.PatchLog)):
        graph.set((subject, DAL.receiptModel, DAL.SnapshotPerRevision))
    return graph
