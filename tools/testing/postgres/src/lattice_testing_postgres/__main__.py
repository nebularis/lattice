# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""Unpack the pinned server once and say which version it is, for ``mise run bootstrap:testing-postgres``."""

from lattice_testing_postgres import DISTRIBUTION, binaries, pinned_version

print(f"PostgreSQL {pinned_version()} from {DISTRIBUTION}, unpacked in {binaries()}")
