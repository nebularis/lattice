#!/usr/bin/env bash
#
# Environment setup for Claude Code cloud sessions working on LATTICE.
#
# Paste this into the cloud environment's "Setup script" field, so that it runs
# the copy in whichever clone the session has:
#
#   s=$(ls -d /home/user/*/tools/claude-cloud-setup.sh "$PWD"/tools/claude-cloud-setup.sh 2>/dev/null | head -1)
#   [ -n "$s" ] && bash "$s" || true
#
# Rules the cloud imposes (code.claude.com/docs/en/cloud-environments):
#   - a setup script that exits non-zero stops the session from starting, so
#     this script always exits 0 and reports what failed instead
#   - a script that takes longer than about five minutes is not cached, and
#     then runs again for every new session, so it installs only what the
#     image lacks, in parallel
#   - the default "Trusted" network allows GitHub releases, PyPI and npm, but
#     not mise.run or mise's own metadata hosts, so nothing here reaches them
#
# The image already has Node 22, Maven and Python with uv. mise.toml pins Java
# 25 and Python 3.14, which come from GitHub-hosted builds and are linked into
# mise, as are the image's Node and Maven. Erlang/Elixir (check:spc, which runs
# no tests yet, TD-22) and Playwright's browsers (not on the allowlist) are
# left out. Install them by hand in a session that needs them.

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

log()  { printf '\n\033[1;34m==>\033[0m %s\n' "$*"; }
fail() { printf '\033[1;31mxx\033[0m %s\n' "$*" >&2; }

FAILED_STEPS=()
step() {
  local name="$1"; shift
  log "$name ($((SECONDS))s)"
  "$@" || { fail "$name failed"; FAILED_STEPS+=("$name"); return 1; }
}

# The download URL of a repository's latest release asset matching a pattern.
latest_asset() {
  curl -fsSL "https://api.github.com/repos/$1/releases/latest" |
    jq -r --arg p "$2" '[.assets[] | select(.name | test($p)) | .browser_download_url][0] // empty'
}

### 1. mise, from its GitHub release ##########################################

install_mise() {
  local url; url=$(latest_asset jdx/mise '^mise-v[0-9.]+-linux-x64$')
  [ -n "$url" ] && curl -fsSL "$url" -o /usr/local/bin/mise && chmod +x /usr/local/bin/mise
}
command -v mise >/dev/null 2>&1 || step "Install mise" install_mise
if ! command -v mise >/dev/null 2>&1; then
  fail "mise is not installed. The session starts without LATTICE's toolchain."
  exit 0
fi
mise --version

# Toolchains mise must not try to build or download here, and pip permission
# to install into the linked Python as root.
mkdir -p "$HOME/.config/mise"
cat > "$HOME/.config/mise/config.toml" <<'EOF'
[settings]
disable_tools = ["erlang", "elixir"]

[env]
PIP_BREAK_SYSTEM_PACKAGES = "1"
EOF
step "Trust the repository's mise config" mise trust "$REPO_ROOT"

### 2. Toolchains, in parallel ################################################

install_java() {
  local url; url=$(latest_asset adoptium/temurin25-binaries '^OpenJDK25U-jdk_x64_linux_hotspot_.*\.tar\.gz$')
  [ -n "$url" ] || return 1
  rm -rf /opt/jdk-25 && mkdir -p /opt/jdk-25 &&
    curl -fsSL "$url" | tar -xz --strip-components=1 -C /opt/jdk-25 &&
    mise link --force java@25 /opt/jdk-25
}

install_python() {
  uv python install 3.14 &&
    mise link --force python@3.14 "$(dirname "$(dirname "$(uv python find 3.14)")")"
}

link_image_tools() {
  mise link --force node@22 /opt/node22 &&
    mise link --force maven@3.9 "$(dirname "$(dirname "$(readlink -f "$(command -v mvn)")")")"
}

log "Install Java 25 and Python 3.14, link Node 22 and Maven ($((SECONDS))s)"
install_java > /tmp/lattice-java.log 2>&1 & java_pid=$!
install_python > /tmp/lattice-python.log 2>&1 & python_pid=$!
link_image_tools || { fail "Link the image's Node and Maven failed"; FAILED_STEPS+=("Link Node and Maven"); }
wait "$java_pid" || { cat /tmp/lattice-java.log; fail "Java 25 failed"; FAILED_STEPS+=("Java 25"); }
wait "$python_pid" || { cat /tmp/lattice-python.log; fail "Python 3.14 failed"; FAILED_STEPS+=("Python 3.14"); }

# Shims on PATH for later shells in the session.
for rc in /etc/profile.d/mise.sh "$HOME/.bashrc"; do
  grep -qF 'mise/shims' "$rc" 2>/dev/null || echo 'export PATH="$HOME/.local/share/mise/shims:$PATH"' >> "$rc"
done

### 3. Repository dependencies ################################################
# Inside the five minutes, these are cached with the toolchains. If the
# summary shows setup going over, move this step to a SessionStart hook.

step "Bootstrap repository dependencies (mise run bootstrap)" mise run bootstrap

### Summary ###################################################################

log "Toolchain versions"
mise exec -- java -version 2>&1 | head -1 || true
mise exec -- python --version 2>&1 || true
mise exec -- node --version 2>&1 || true
mise exec -- mvn --version 2>&1 | head -1 || true

log "Setup took ${SECONDS}s (cached only if under about 300s)"
if [ "${#FAILED_STEPS[@]}" -gt 0 ]; then
  fail "${#FAILED_STEPS[@]} step(s) failed: ${FAILED_STEPS[*]}"
  fail "The session still starts. Retry a step by hand from mise.toml."
fi
exit 0
