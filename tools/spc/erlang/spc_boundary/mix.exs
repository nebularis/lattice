# apps/spc_boundary/mix.exs
defmodule SpcBoundary.MixProject do
  use Mix.Project

  def project do
    [
      app: :spc_boundary,
      version: "0.1.0",
      build_path: "../../_build",
      deps_path: "../../deps",
      lockfile: "../../mix.lock",
      elixirc_paths: ["lib"],
      start_permanent: Mix.env() == :prod,
      deps: deps()
    ]
  end

  def application do
    [
      mod: {SpcBoundary.Application, []},
      extra_applications: [:logger]
    ]
  end

  defp deps do
    [
      {:spc_engine, in_umbrella: true},
      {:bandit, "~> 1.0"},
      {:plug, "~> 1.15"},
      {:jason, "~> 1.4"},
      {:finch, "~> 0.18"},
      {:saxy, "~> 1.5"},          # streaming XML parser for ACORD
      {:rdf, "~> 2.0"},           # rdf-ex, off critical path
      {:sparql_client, "~> 0.5"}, # sparql-ex client for Fuseki
      {:telemetry, "~> 1.2"},
      {:telemetry_metrics, "~> 0.6"},
      {:telemetry_poller, "~> 1.0"}
    ]
  end
end