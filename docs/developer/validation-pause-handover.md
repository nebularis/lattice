<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pause Handover

Date: 2026-09-20  
Status: Paused for macOS upgrade  
Implementation merge under validation: `ba04e5611efa39ec8d5cf753e854f5fa3e09d007`  
Validation baseline revision: `25bc56b050d5dc7853d37c09b03ab1cb2f989532`

## Why validation is paused

The host is running macOS 14 / Darwin 23.6.0 on Apple arm64. Homebrew warned that this macOS version is no longer supported for the requested formula installation and began building a large dependency chain from source while installing `mise`, including LLVM and Rust.

The user has elected to upgrade macOS before continuing. Do not resume tool installation, package resolution, builds, tests, containers, or infrastructure validation until the OS upgrade is complete and the host toolchain has been rechecked.

## Scope decision

The current programme validates and finishes the merged Phase 0 through Phase 6 implementation only.

The canonical plan's later Phase 7 compiler-breadth and MORK-to-SPC bridge work is explicitly out of scope until Phases 0 through 6 are validated and accepted.

## Work completed before the pause

### Planning and repository audit

- Read the consolidated implementation handover and Phase 0–6 handoffs.
- Audited the authored toolchain, package manifests, Compose stack, Dev Container, Java reactor, workers, frontend applications, migrations, CI workflows, and test inventories.
- Created the full continuation plan in session memory during the implementation session.
- Identified likely validation and implementation gaps:
  - placeholder `yarn.lock`
  - no dedicated workers lock
  - documented Maven Wrapper absent
  - Dev Container installs only Java and Maven despite claiming a fuller canonical environment
  - Compose documentation mentions Keycloak but Compose does not define it
  - PostgreSQL transactional outbox persistence absent
  - Testcontainers integration absent
  - web applications are fixture-backed and lack validated HTTP integration
  - no dummy-data seeding or human-usability framework yet

### Validation baseline

Recorded:

- Current revision: `25bc56b050d5dc7853d37c09b03ab1cb2f989532`
- Implementation merge confirmed in history: `ba04e5611efa39ec8d5cf753e854f5fa3e09d007`
- Host: macOS Darwin 23.6.0, Apple arm64
- Pre-existing unrelated worktree change: `docs/_includes/theory/00-thesis.md`
- Python: 3.9.13, below canonical Python 3.11
- Java: OpenJDK 24.0.1, not pinned Java 21
- Node: 24.2.0, not pinned Node 22
- Maven: present through Homebrew, version not yet validated
- Corepack: present
- Initially missing: `mise`, `yarn`, `docker`, `oras`, `cosign`, `jq`

The pre-existing theory edit must not be reverted or modified as part of validation.

### Stabilisation changes made

- Added [validation-status.md](validation-status.md) as the evidence ledger.
- Changed `.github/workflows/platform.yml` to manual-only `workflow_dispatch` while validation is in progress.
- Changed `.github/workflows/phase8-conformance.yml` to manual-only `workflow_dispatch` while validation is in progress.

These workflows should not be re-enabled automatically until their package locks and command matrices pass in a clean environment.

## Interrupted operation

The only installation command run was:

```bash
brew install mise
```

Homebrew warned that macOS 14 was unsupported and began installing or building a large dependency chain. The last observed stage was an LLVM build during the `mise` dependency installation.

The installation result was not confirmed. After the OS upgrade, do not assume `mise` is installed or healthy. Check the Homebrew state explicitly.

## Safe resume point after upgrading macOS

Run these commands manually from the repository root and capture their output:

```bash
sw_vers
uname -m
xcode-select -p
brew doctor
brew update
brew list --versions mise
command -v mise
mise --version
```

If Homebrew reports an incomplete or broken `mise` installation, repair it before continuing:

```bash
brew reinstall mise
```

Then inspect the repository-declared toolchain without installing everything immediately:

```bash
mise doctor
mise config
mise ls
mise tasks
```

Only after those commands look healthy, install the pinned runtimes:

```bash
mise install
mise exec -- java -version
mise exec -- mvn -version
mise exec -- node --version
mise exec -- python --version
mise exec -- elixir --version
```

Expected major versions from `mise.toml`:

- Java 21
- Maven 3.9
- Node 22
- Python 3.11
- Erlang 27
- Elixir 1.17

Do not run `mise run bootstrap`, `mise run check`, or `mise run test` until the version inventory is reviewed and package-lock repair has been planned.

## Next execution steps

After the OS and toolchain checks:

1. Validate and repair package management:
   - root Python lock
   - workers lock
   - independent MORK and SPC Python installs
   - regenerate and review `yarn.lock`
   - add or repair Maven Wrapper
   - validate Mix dependencies only for Phase 0–6 compatibility
2. Run static contract and configuration checks.
3. Run ecosystem unit suites separately.
4. Repair bounded defects with regression tests.
5. Bring up disposable infrastructure and apply migrations.
6. Add Testcontainers and durable PostgreSQL outbox implementation.
7. Validate Phase 0–6 vertical slices in order.
8. Add local fixture and integrated application launch modes.
9. Add dummy-data and human-usability test framework.
10. Write user and developer Getting Started guides from commands proven to work.
11. Update the implementation handover with validation evidence and residual risks.

## Commands intentionally not yet run

- `mise install`
- `mise run bootstrap`
- `mise run check`
- `mise run test`
- Maven reactor builds
- Worker pytest suite
- Yarn installation, typecheck, build, or Playwright
- Docker Compose services
- Database migrations
- RabbitMQ, Fuseki, PostgreSQL, or OCI integration tests
- ORAS or Cosign flows
- Jekyll validation for the new onboarding documentation

No claims should be made that these commands or integrations pass.

## Relevant documents

- [Implementation handover](implementation-handover.md)
- [Toolchain guide](toolchain.md)
- [Offline handoff procedure](offline-phase-handoff.md)
- [Phase 0–1 handoff](phase-0-1-handoff.md)
- [Phase 2 handoff](phase-2-handoff.md)
- [Phase 3 handoff](phase-3-handoff.md)
- [Phase 4 handoff](phase-4-handoff.md)
- [Phase 5 handoff](phase-5-handoff.md)
- [Phase 6 handoff](phase-6-handoff.md)
- [Validation status](validation-status.md)
- Canonical implementation plan: `.github/prompts/plan-morkSurfaceImplementation.prompt.md`

## Resume instruction for the next agent

Start by reading this file and `validation-status.md`. Confirm the user's macOS upgrade is complete. Run only the manual host and `mise` checks listed above. Report the results before installing project dependencies or executing repository-wide test commands.
