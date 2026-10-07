# GHC's wasm32-wasi cross-compiler (ghc-wasm-meta), with wasmtime to run the output.
# GHC's WebAssembly backend has no Windows host build, so it runs here in Linux. Used only for
# measure M5 (other code-generation targets): Isabelle's Haskell export cross-compiled to wasm.
# Base image pinned by digest (epic §4, Environments).
#
# Build with build-images.py, which stages an optional corporate CA as corporate-ca.crt
# (an empty file off a network that does not need one).
FROM debian@sha256:2c037a04925515fdd6ea85ea14a682d0e79931f5e9f5d07b6dbfc6ba12f9e858

RUN apt-get update && \
    apt-get install -y --no-install-recommends ca-certificates curl jq unzip xz-utils zstd git python3 make && \
    rm -rf /var/lib/apt/lists/*

COPY corporate-ca.crt /tmp/corporate-ca.crt
RUN if [ -s /tmp/corporate-ca.crt ]; then \
      cp /tmp/corporate-ca.crt /usr/local/share/ca-certificates/corporate-ca.crt && \
      update-ca-certificates; \
    fi
# ghc-wasm-meta installs its own Node.js, which does not read the system trust store.
ENV NODE_EXTRA_CA_CERTS=/tmp/corporate-ca.crt

# ghc-wasm-meta's setup.sh runs "npm install" for Playwright and Puppeteer, used only to test
# JavaScript FFI output in browsers. The proxy blocks the npm registry (toolchain-feasibility
# spike, 2026-10-06), so that step is replaced with an empty node_modules directory. Compiling to
# wasm and running under wasmtime do not need it.
# ghc-wasm-meta is fetched from master. Pin a commit here if track D's recommendation is Isabelle.
ARG FLAVOUR=9.10
RUN mkdir /tmp/meta && cd /tmp/meta && \
    curl -fsSL https://gitlab.haskell.org/haskell-wasm/ghc-wasm-meta/-/archive/master/ghc-wasm-meta-master.tar.gz \
      | tar xz --strip-components=1 && \
    sed -i 's|PATH=\$PREFIX/nodejs/bin:\$PATH npm install|mkdir -p node_modules|' setup.sh && \
    FLAVOUR=$FLAVOUR ./setup.sh && \
    cd / && rm -rf /tmp/meta

# Run tools with: bash -c "source /root/.ghc-wasm/env && wasm32-wasi-ghc ..."
WORKDIR /work
