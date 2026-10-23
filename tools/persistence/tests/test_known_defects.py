# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""Defects found by formal-methods track H that are not fixed yet, each
asserted as the behaviour it should have and marked as a strict expected
failure.

While the defect stands, the test is reported as xfail and the suite stays
green. When someone fixes the defect, the test starts to pass, strict mode
turns that into a failure, and the fixer removes the marker and the entry in
``docs/developer/plans/technical-debt.md``. Each reason names its register entry.
"""

# None at present. TD-23 was fixed on 2026-10-23 and its test moved to test_validator.py.
