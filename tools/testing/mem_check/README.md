<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# lattice-testing-mem-check

How much memory this machine has available, and how many test workers fit in it, for LATTICE's test suites
([ADR-A125](../../../docs/architecture/decisions/ADR-A125-test-support-tooling.md)). Standard library only.

A suite that runs its tests in parallel measures what one worker needs at its peak, and asks `mem_check.workers` for a count. It gets
as many workers as fit in what is available less a reserve of 1 GiB, up to the count it would use anyway and never fewer than two. A
short machine, for example 8 GB with an editor open, runs fewer workers, which takes longer and stays within memory.

```python
import mem_check

count = mem_check.workers(default=os.cpu_count() or 1, per_worker=700 * mem_check.MIB)
```

| Platform | Available means |
|---|---|
| macOS | the free, inactive, speculative and purgeable pages `vm_stat` reports |
| Linux | `MemAvailable` in `/proc/meminfo` |
| Windows | `ullAvailPhys` from `GlobalMemoryStatusEx` |

Where none can be read, `available_bytes()` is `None` and a suite keeps its own count. `MEM_CHECK_AVAILABLE_MIB` stands in for the
machine, for a test or to force the low path.

## How a suite uses it with pytest-xdist

pytest-xdist asks the hook `pytest_xdist_auto_num_workers` what `-n auto` means. A suite's `conftest.py` answers it, and leaves
`PYTEST_XDIST_AUTO_NUM_WORKERS` in charge when it is set:

```python
def pytest_xdist_auto_num_workers(config):
    if os.environ.get("PYTEST_XDIST_AUTO_NUM_WORKERS"):
        return None
    import mem_check
    return mem_check.workers(os.cpu_count() or 1, PER_WORKER)
```

`tools/persistence/tests/conftest.py` is the first suite to do so.

`mise run bootstrap` installs it (or `mise run bootstrap:testing-mem-check` alone), and `mise run check:testing-mem-check` runs its
tests.
