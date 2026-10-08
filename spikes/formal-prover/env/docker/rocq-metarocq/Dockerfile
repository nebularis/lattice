# Rocq 9.1 with MetaRocq's template-rocq, for quoting Rocq terms into an inspectable AST
# (spikes/formal-prover/rocq uses this image for Quote.v). Base image pinned by digest
# (epic §4, Environments: "base images, toolchain versions and fetched repositories are
# pinned by digest or commit").
#
# Build with build-images.py, which stages an optional extra root CA as extra-ca.crt
# (an empty file off a network that does not need one).
FROM rocq/rocq-prover@sha256:9a1e969649a3cc3c6f310d5be5a842e2187384560337c6c0807aba9f8565efba

COPY extra-ca.crt /tmp/extra-ca.crt
RUN if [ -s /tmp/extra-ca.crt ]; then \
      sudo cp /tmp/extra-ca.crt /usr/local/share/ca-certificates/extra-ca.crt && \
      sudo update-ca-certificates; \
    fi

RUN opam update && \
    opam install -y rocq-metarocq-template && \
    opam clean -a -c -s --logs

WORKDIR /home/rocq/work
