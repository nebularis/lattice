# SPDX-License-Identifier: MPL-2.0
# The Configuration Studio's worker, for the test harness (tools/testing/studio_harness). The build context holds the parts of the
# repository the worker reads, which the harness copies, and the installs below are the ones `mise run bootstrap` makes for it.
FROM python:3.14-slim
ENV LATTICE_ROOT=/repo PIP_NO_CACHE_DIR=1 PYTHONUNBUFFERED=1
WORKDIR /repo
COPY pyproject.toml requirements-lock.txt repository-catalogue.md ./
COPY workers workers
COPY tools tools
COPY packages packages
COPY ontology ontology
COPY contracts contracts
RUN pip install -c requirements-lock.txt ".[reasoning]" -e "./workers[studio]" -e ./tools/mork -e ./tools/mork_compilers -e ./tools/surface \
    -e ./tools/mork_rdf -e ./tools/mork_transforms -e ./packages/persistence/python -e ./tools/vocabulary -e ./tools/reference/eligibility -e ./packages/minting/python
RUN adduser --disabled-password --no-create-home studio
USER studio
ENTRYPOINT ["python", "-m", "lattice_workers.config_studio_main"]
