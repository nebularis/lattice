# SPDX-License-Identifier: MPL-2.0

"""tools/full_sweep.py reads pytest's summary and failing tests from a check's output."""

from full_sweep import outcome


def test_reads_the_last_summary_and_each_failing_test() -> None:
    output = "\n".join([
        "[check:ontology-catalog] $ python -m pytest tools/test_a.py -q",
        "FAILED tools/test_a.py::test_one - AssertionError",
        "\x1b[31mERROR tools/test_b.py::test_two\x1b[0m",
        "FAILED tools/test_a.py::test_one - AssertionError",
        "1 failed, 1 error, 656 passed, 3 warnings in 113.47s (0:01:53)",
    ])
    assert outcome(output) == ("1 failed, 1 error, 656 passed",
                               ["tools/test_a.py::test_one", "tools/test_b.py::test_two"])


def test_a_check_with_no_tests_has_no_counts() -> None:
    assert outcome("40 in-scope ontology document(s) checked against main: no unbumped changes") == ("", [])


def test_reads_a_verbose_summary_line() -> None:
    assert outcome("====== 16 passed in 0.70s ======")[0] == "16 passed"
