#!/usr/bin/env bash
#
# Environment setup for Claude Code cloud sessions working on LATTICE.
#
# Mirrors "Developer Setup / Getting Started" in README.md: install the
# toolchains pinned in mise.toml, then delegate dependency installation to
# this repo's own `mise run bootstrap` task, so this script can't drift
# from what CONTRIBUTING.md/README.md document.
#
# Steps are best-effort and independent: a failure in one (e.g. the
# Erlang/Elixir toolchain, which compiles from source and is slow) is
# reported but doesn't stop the rest of the environment from being set up.
# The script exits non-zero only if something failed.

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

log()  { printf '\n\033[1;34m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m!!\033[0m %s\n' "$*" >&2; }
fail() { printf '\033[1;31mxx\033[0m %s\n' "$*" >&2; }

FAILED_STEPS=()

# Run a step; record failures instead of aborting, so later independent
# steps still get a chance to run.
step() {
  local name="$1"; shift
  log "$name"
  if ! "$@"; then
    fail "$name failed"
    FAILED_STEPS+=("$name")
    return 1
  fi
}

### 1. mise ####################################################################

if ! command -v mise >/dev/null 2>&1; then
  step "Install mise" bash -c 'curl -fsSL https://mise.run | sh'
  export PATH="$HOME/.local/bin:$PATH"
fi

if ! command -v mise >/dev/null 2>&1; then
  fail "mise is not on PATH after install; cannot continue"
  exit 1
fi

mise --version

# Make mise's shims available to this script and to any shells/tool calls
# later in this session.
eval "$(mise activate bash)"
for rc in "$HOME/.bashrc" "$HOME/.profile"; do
  touch "$rc" 2>/dev/null || continue
  grep -qF 'mise activate' "$rc" 2>/dev/null || echo 'eval "$(mise activate bash)"' >> "$rc"
done

step "Trust repo mise config" mise trust "$REPO_ROOT"

### 2. Fast toolchains (java, maven, node, python) #############################
# These use mise's precompiled backends, so they're quick and need no extra
# OS packages.

step "Install java/maven/node/python toolchains" mise install java maven node python

### 3. Repository dependency bootstrap ##########################################
# Installs root Python deps, workers, mork/mork_compilers/surface/persistence,
# the standalone minting library, and the Yarn workspace (see mise.toml
# [tasks.bootstrap]). None of this depends on Erlang/Elixir.

step "Bootstrap repository dependencies (mise run bootstrap)" mise run bootstrap

### 4. Playwright browsers (frontend e2e tests) #################################
# apps/mork-review-workbench and apps/surface-contract-studio use Playwright.
# Best-effort: needs sudo/apt for browser system deps in some environments.

step "Install Playwright browsers" bash -c '
  mise exec -- yarn workspace @lattice/mork-review-workbench exec playwright install --with-deps chromium &&
  mise exec -- yarn workspace @lattice/surface-contract-studio exec playwright install --with-deps chromium
'

### 5. Erlang/Elixir (optional: only needed for `mise run check:spc`) ##########
# mise builds Erlang from source via kerl, which needs OS headers. Slow
# (several minutes) and non-critical, so it runs last and never blocks the
# steps above.

install_erlang_build_deps() {
  command -v apt-get >/dev/null 2>&1 || { warn "apt-get not found, skipping OS package install"; return 0; }
  local sudo_cmd=""
  if [ "$(id -u)" -ne 0 ]; then
    command -v sudo >/dev/null 2>&1 && sudo_cmd="sudo"
  fi
  DEBIAN_FRONTEND=noninteractive $sudo_cmd apt-get update -y
  DEBIAN_FRONTEND=noninteractive $sudo_cmd apt-get install -y --no-install-recommends \
    build-essential autoconf m4 libncurses-dev libssl-dev unixodbc-dev unzip
}

step "Install OS build dependencies (for Erlang/kerl)" install_erlang_build_deps
step "Install erlang/elixir toolchains" mise install erlang elixir

### Summary ######################################################################

log "Toolchain versions"
mise exec -- python --version 2>&1 || true
mise exec -- node --version 2>&1 || true
mise exec -- java -version 2>&1 || true
mise exec -- mvn --version 2>&1 || true
mise exec -- elixir --version 2>&1 || true

if [ "${#FAILED_STEPS[@]}" -eq 0 ]; then
  log "Setup complete. Try: mise run check"
  exit 0
else
  warn "Setup finished with ${#FAILED_STEPS[@]} failed step(s):"
  for s in "${FAILED_STEPS[@]}"; do warn "  - $s"; done
  warn "See mise.toml for the individual tasks to retry by hand."
  exit 1
fi
