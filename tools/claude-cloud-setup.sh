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
# Network access: Custom, with "Also include default list of common package
# managers" ticked, plus these hosts:
#
#   mise.jdx.dev        mise itself
#   www.cl.cam.ac.uk    Isabelle, from the Cambridge mirror
#
# Rules the cloud imposes (code.claude.com/docs/en/cloud-environments):
#   - a setup script that exits non-zero stops the session from starting, so
#     this script always exits 0 and reports what failed instead
#   - a script that takes longer than about five minutes is not cached, and
#     then runs again for every new session
#   - GitHub goes through a proxy that serves only the session's own
#     repositories, so nothing here downloads from GitHub
#
# Sources: mise from mise.jdx.dev, Java 25 from Ubuntu's archive, Python 3.14
# from the deadsnakes PPA, Node 22 and Maven from the image, Isabelle2025-2
# from the Cambridge mirror. Erlang/Elixir (check:spc, which runs no tests yet,
# TD-22) and Playwright's browsers are left out.
#
# The container has no DNS of its own. Outbound HTTPS goes through the agent
# proxy named in HTTPS_PROXY, which accepts CONNECT only. Section 0 points pip,
# Yarn, Maven and apt at it. The proxy's port can change when a session
# resumes, so a shell that was set up earlier can refresh itself with
#
#   eval "$(bash tools/claude-cloud-setup.sh --proxy-only)"

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

ISABELLE=Isabelle2025-2
ISABELLE_URL="https://www.cl.cam.ac.uk/research/hvg/Isabelle/dist/${ISABELLE}_linux.tar.gz"
LOGS=/tmp/lattice-setup
mkdir -p "$LOGS"

log()  { printf '\n\033[1;34m==>\033[0m %s\n' "$*"; }
fail() { printf '\033[1;31mxx\033[0m %s\n' "$*" >&2; }

### 0. The agent proxy ########################################################
# Three things keep a tool from reaching the proxy by default:
#   - pip, Yarn and Maven Central are listed in NO_PROXY as direct, but nothing
#     resolves them directly here, so they are taken out of it.
#   - Maven ignores HTTPS_PROXY and reads only settings.xml.
#   - apt's Ubuntu sources are plain http, which the proxy refuses. They move to
#     https, with the proxy named for https.
# NO_PROXY is exported for this run only. Maven's and apt's settings are files,
# so they hold the port of the session that wrote them.

configure_proxy() {
  [ -n "${HTTPS_PROXY:-}" ] || return 0
  local hostport="${HTTPS_PROXY#*://}"
  hostport="${hostport%/}"

  local direct
  direct=$(printf '%s' "${NO_PROXY:-}" | tr ',' '\n' |
    grep -vxE 'pypi\.org|files\.pythonhosted\.org|registry\.npmjs\.org|repo\.maven\.apache\.org' |
    paste -sd, -)
  export NO_PROXY="$direct" no_proxy="$direct" npm_config_noproxy="$direct" GLOBAL_AGENT_NO_PROXY="$direct"

  # A settings.xml that someone else wrote is left alone.
  local m2="$HOME/.m2/settings.xml"
  if [ ! -e "$m2" ] || grep -q 'claude-cloud-setup' "$m2"; then
    mkdir -p "$HOME/.m2"
    cat > "$m2" <<EOF
<!-- Written by tools/claude-cloud-setup.sh from HTTPS_PROXY (claude-cloud-setup) -->
<settings>
  <proxies>
    <proxy>
      <id>agent-proxy</id>
      <active>true</active>
      <protocol>https</protocol>
      <host>${hostport%:*}</host>
      <port>${hostport##*:}</port>
      <nonProxyHosts>localhost|127.0.0.1</nonProxyHosts>
    </proxy>
  </proxies>
</settings>
EOF
  fi

  sed -i -E 's#http://((archive|security)\.ubuntu\.com)#https://\1#' \
    /etc/apt/sources.list.d/ubuntu.sources /etc/apt/sources.list 2>/dev/null
  printf 'Acquire::https::Proxy "%s";\n' "$HTTPS_PROXY" > /etc/apt/apt.conf.d/99agent-proxy
}

if [ "${1:-}" = "--proxy-only" ]; then
  configure_proxy >&2
  printf 'export NO_PROXY=%q no_proxy=%q npm_config_noproxy=%q GLOBAL_AGENT_NO_PROXY=%q\n' \
    "${NO_PROXY:-}" "${no_proxy:-}" "${npm_config_noproxy:-}" "${GLOBAL_AGENT_NO_PROXY:-}"
  exit 0
fi
configure_proxy

FAILED_STEPS=()
# Run a step, logging to its own file. Record a failure instead of stopping.
step() {
  local name="$1"; shift
  log "$name (${SECONDS}s)"
  "$@" > "$LOGS/$name.log" 2>&1 || { tail -20 "$LOGS/$name.log"; fail "$name failed"; FAILED_STEPS+=("$name"); return 1; }
}

### 1. Packages: Java 25, Python 3.14 ##########################################

install_packages() {
  export DEBIAN_FRONTEND=noninteractive
  command -v add-apt-repository >/dev/null || apt-get install -y software-properties-common
  # The image may point python3 at a newer Python than the one Ubuntu's
  # apt_pkg binding was built for, so run add-apt-repository with the matching one.
  local apt_py
  apt_py=$(ls /usr/lib/python3/dist-packages/apt_pkg.cpython-*.so 2>/dev/null | head -1 |
    sed -E 's/.*cpython-([0-9])([0-9]+)-.*/python\1.\2/')
  ${apt_py:-python3} /usr/bin/add-apt-repository -y ppa:deadsnakes/ppa &&
    apt-get update &&
    apt-get install -y --no-install-recommends openjdk-25-jdk-headless python3.14 python3.14-venv &&
    rm -rf /opt/python3.14 && python3.14 -m venv /opt/python3.14
}

### 2. Isabelle, native ########################################################

install_isabelle() {
  [ -x "/opt/$ISABELLE/bin/isabelle" ] ||
    curl -fsSL "$ISABELLE_URL" | tar -xz -C /opt || return 1
  ln -sf "/opt/$ISABELLE/bin/isabelle" /usr/local/bin/isabelle
}

### 3. mise ####################################################################

install_mise() {
  curl -fsSL https://mise.jdx.dev/mise-latest-linux-x64 -o /usr/local/bin/mise &&
    chmod +x /usr/local/bin/mise
}

log "Packages, Isabelle and mise, in parallel (${SECONDS}s)"
step "packages" install_packages & packages_pid=$!
step "isabelle" install_isabelle & isabelle_pid=$!
command -v mise >/dev/null 2>&1 || step "mise" install_mise
wait "$packages_pid" || FAILED_STEPS+=("packages")
wait "$isabelle_pid" || FAILED_STEPS+=("isabelle")

if ! command -v mise >/dev/null 2>&1; then
  fail "mise is not installed. The session starts without LATTICE's mise tasks."
  exit 0
fi

### 4. Link the toolchains into mise ###########################################
# mise.toml's pins are then met by what is installed, and mise downloads
# nothing. It must not try to build Erlang/Elixir here.

mkdir -p "$HOME/.config/mise"
printf '[settings]\ndisable_tools = ["erlang", "elixir"]\n' > "$HOME/.config/mise/config.toml"

link_tools() {
  mise trust "$REPO_ROOT" &&
    mise link --force java@25 /usr/lib/jvm/java-25-openjdk-amd64 &&
    mise link --force python@3.14 /opt/python3.14 &&
    mise link --force node@22 /opt/node22 &&
    mise link --force maven@3.9 "$(dirname "$(dirname "$(readlink -f "$(command -v mvn)")")")"
}
step "link toolchains" link_tools

for rc in /etc/profile.d/mise.sh "$HOME/.bashrc"; do
  grep -qF 'mise/shims' "$rc" 2>/dev/null || echo 'export PATH="$HOME/.local/share/mise/shims:$PATH"' >> "$rc"
done

### 5. Repository dependencies ################################################
# Cached with the toolchains while setup stays under about five minutes. If
# the summary shows it going over, move this step to a SessionStart hook.

export COREPACK_ENABLE_DOWNLOAD_PROMPT=0
step "bootstrap" mise run bootstrap
# Not part of bootstrap. The reasoner jar (ADR-A83) is what the tests that need
# a reasoner skip without, and the Oxigraph package is what ADR-A125's tests use.
step "reasoning testkit" mise run bootstrap:reasoning-testkit
step "testing oxigraph" mise run bootstrap:testing-oxigraph

### Summary ###################################################################

log "Versions"
mise exec -- java -version 2>&1 | head -1 || true
mise exec -- python --version 2>&1 || true
mise exec -- node --version 2>&1 || true
mise exec -- mvn --version 2>&1 | head -1 || true
isabelle version 2>&1 || true

log "Setup took ${SECONDS}s (cached only if under about 300s). Logs: $LOGS"
if [ "${#FAILED_STEPS[@]}" -gt 0 ]; then
  fail "Failed: ${FAILED_STEPS[*]}. The session still starts. Retry a step by hand."
fi
exit 0
