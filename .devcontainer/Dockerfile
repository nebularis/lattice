FROM mcr.microsoft.com/devcontainers/base:ubuntu-24.04

RUN apt-get update \
    && apt-get install --yes --no-install-recommends openjdk-21-jdk maven \
    && rm -rf /var/lib/apt/lists/*

USER vscode
