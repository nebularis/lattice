#!/usr/bin/env bash
#
# Environment setup for Claude Code cloud sessions working on LATTICE.
#
# Paste this into the cloud environment's "Setup script" field. It states what the
# person setting the environment up trusts, then runs the copy of this script in
# whichever clone the session has:
#
#   mkdir -p ~/.config/vyvid
#   { printf '[framework]\nkb = "~/vyvid-kb"\nglue = "stop"\ntrusted_repositories = ["github.com/nebularis/lattice"]\n'
#     for d in lifecycle tools python triple-stores rdf-modelling; do
#       printf '\n[[domains]]\nname = "%s"\nremote = "https://github.com/nebularis/vyvid-%s.git"\ntrust = "own"\ngit = { pull = "manual", commit = "manual", push = "manual" }\n' "$d" "$d"
#     done; } > ~/.config/vyvid/config.toml
#   s=$(ls -d /home/user/*/tools/claude-cloud-setup.sh "$PWD"/tools/claude-cloud-setup.sh 2>/dev/null | head -1)
#   [ -n "$s" ] && bash "$s" || true
#
# The grant is pasted rather than kept here so the repository does not vouch for
# itself. No terminal exists for `vyd trust`, and a hash would go stale on any
# branch that changes vyvid.toml (ADR-A152).
#
# Network access: Custom, with "Also include default list of common package
# managers" ticked, plus these hosts:
#
#   mise.jdx.dev        mise itself
#   isabelle.in.tum.de  Isabelle, from the pinned release's own archive
#   huggingface.co      the knowledge index's embedding model
#   *.cdn.hf.co         where huggingface.co redirects for the model. This script
#                       and a session are sent to different hosts, so a wildcard
#
# Rules the cloud imposes (code.claude.com/docs/en/cloud-environments):
#   - a setup script that exits non-zero stops the session from starting, so
#     this script always exits 0 and reports what failed instead
#   - a script that takes longer than about five minutes is not cached, and
#     then runs again for every new session
#   - a later session skips this script and starts from its snapshot, with a
#     fresh checkout that can be newer than the one seen here
#   - GitHub goes through its own proxy, whatever the list above says. A public
#     repository can be cloned, and an archive of one not attached to the session
#     is refused, so Вивід and its domains come by git
#
# Sources: mise from mise.jdx.dev, Java 25 from Ubuntu's archive, Python 3.14
# from the deadsnakes PPA, Node 22 and Maven from the image, Isabelle2025-2
# from its own release archive, Вивід and its domains from GitHub by git, its
# embedding model from huggingface.co. Erlang/Elixir (check:spc, which runs no tests yet,
# TD-22) and Playwright's browsers are left out.
#
# A session's outbound HTTPS goes through the agent proxy named in HTTPS_PROXY,
# which accepts CONNECT only. Section 0 points pip, Yarn, Maven and apt at it.
# While this script runs in setup HTTPS_PROXY is unset and names resolve only for
# allowed hosts, so section 0 does nothing then. The proxy's port can change when
# a session resumes, so a shell that was set up earlier can refresh itself with
#
#   eval "$(bash tools/claude-cloud-setup.sh --proxy-only)"

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

ISABELLE=Isabelle2025-2
ISABELLE_URL="https://isabelle.in.tum.de/website-${ISABELLE}/dist/${ISABELLE}_linux.tar.gz"
LOGS="${LATTICE_SETUP_LOGS:-/tmp/lattice-setup}"
DEFERRED="$HOME/.lattice-setup-deferred"
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

### Sessions ##################################################################
# --session is what the SessionStart hook runs in a cloud session, and what to run
# by hand in a thread that runs no hook. It keeps vyd at the branch's pin. Where
# setup left bootstrap tasks undone, it starts them in the background and says so,
# and it does nothing more otherwise. --finish-deferred is that background run. It
# leaves in $DEFERRED only what failed. Neither builds the index, since two builds
# at once write into the same folder.

if [ "${1:-}" = "--finish-deferred" ]; then
  export COREPACK_ENABLE_DOWNLOAD_PROMPT=0
  failed=""
  # The list is read whole first, so a write to the file during the run cannot
  # shift what is read next, and a task gets no standard input to read it from.
  for task in $(cat "$DEFERRED"); do
    mise run "$task" < /dev/null || failed="$failed$task"$'\n'
  done
  if [ -n "$failed" ]; then printf '%s' "$failed" > "$DEFERRED"; else rm -f "$DEFERRED"; fi
  exit 0
fi

if [ "${1:-}" = "--session" ]; then
  export PATH="$HOME/.local/bin:$HOME/.local/share/mise/shims:$PATH"
  command -v mise >/dev/null 2>&1 || exit 0
  configure_proxy >/dev/null 2>&1
  mise run bootstrap:vyvid > "$LOGS/session-vyvid.log" 2>&1
  if [ -s "$DEFERRED" ]; then
    if ! { [ -f "$LOGS/deferred.pid" ] && kill -0 "$(cat "$LOGS/deferred.pid")" 2>/dev/null; }; then
      nohup bash "${BASH_SOURCE[0]}" --finish-deferred > "$LOGS/deferred.log" 2>&1 &
      echo $! > "$LOGS/deferred.pid"
    fi
    echo "Cloud setup ran out of time, so these are installing in the background: $(tr '\n' ' ' < "$DEFERRED")The index is ready. A test or check that needs them must wait until $DEFERRED has gone. The log is $LOGS/deferred.log."
  fi
  exit 0
fi

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

### 5. Вивід and its domains ##################################################
# Before bootstrap, whose knowledge step builds the index and needs the domains.
# The domains and their trust are in ~/.config/vyvid/config.toml, which the pasted
# lines write. Without it the clone has nothing to do, and the index is built from
# the project alone.

export PATH="$HOME/.local/bin:$PATH"

install_vyvid() {
  mise run bootstrap:vyvid &&
    vyd kb clone &&
    vyd install --client claude-code
}
step "vyvid" install_vyvid

### 6. The index, then the rest if time allows ################################
# Setup past about five minutes is not cached and runs again for every session.
# The index always builds, since an agent needs it from its first question, and it
# embeds in about a minute that every later session is then spared. The dependencies
# run beside it, since it is mostly CPU and they are mostly network, and are cached
# while they fit. A step is never killed, so it starts only before a limit that
# leaves it room to finish. What did not start goes in $DEFERRED, and a session's
# hook finishes it, so a slow network costs the sessions of that snapshot only.

export COREPACK_ENABLE_DOWNLOAD_PROMPT=0
rm -f "$DEFERRED"

later() {
  local limit="$1" name="$2" task="$3"
  if [ "$SECONDS" -lt "$limit" ]; then
    step "$name" mise run "$task"
  else
    log "$name left for the session (${SECONDS}s)"
    echo "$task" >> "$DEFERRED"
  fi
}

# Before the two below, since one pip at a time writes this checkout's .venv.
step "index packages" mise run bootstrap:index-packages
step "index" mise run build:knowledge & index_pid=$!
later 150 "dependencies" bootstrap:dependencies
wait "$index_pid" || FAILED_STEPS+=("index")
# Not part of bootstrap. The reasoner jar (ADR-A83) is what the tests that need
# a reasoner skip without.
later 250 "reasoning testkit" bootstrap:reasoning-testkit

### Summary ###################################################################

log "Versions"
mise exec -- java -version 2>&1 | head -1 || true
mise exec -- python --version 2>&1 || true
mise exec -- node --version 2>&1 || true
mise exec -- mvn --version 2>&1 | head -1 || true
isabelle version 2>&1 || true
vyd --version 2>&1 || true
vyd config 2>&1 | grep -E '^(configuration trust|trusted repositories|project lattice)' || true

log "Setup took ${SECONDS}s (cached only if under about 300s). Logs: $LOGS"
[ -s "$DEFERRED" ] && log "Left for the session: $(tr '\n' ' ' < "$DEFERRED")"
if [ "${#FAILED_STEPS[@]}" -gt 0 ]; then
  fail "Failed: ${FAILED_STEPS[*]}. The session still starts. Retry a step by hand."
fi
exit 0
