<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# lattice-testing-requires

A pytest marker for the Python packages a test needs (STD-323). A test whose package cannot be imported is skipped, and its reason names the package. Some environments can never install a package, such as one behind a mirror that refuses it, and their tests still run everything else.

```python
@pytest.mark.requires("anthropic")
def test_the_anthropic_provider_is_chosen_by_the_environment():
    ...
```

A skip names a package, never an operating system, so a test that runs on Linux runs on Windows and macOS too wherever its package can be installed. A run that skipped any test ends with a line naming each missing package and how many tests it held back.

`LATTICE_REQUIRE_ALL=1` fails each such test instead of skipping it, for a run that must show every test ran.

The plugin loads itself in every pytest run of an environment where this package is installed, through its `pytest11` entry point, so a suite needs no `conftest.py` for it. `mise run bootstrap` installs it.

Only the packages a test imports itself, or through the code under test, belong in its marker. A fake standing in for a package the test is not about stays a fake, and a test never fakes the package it needs.
