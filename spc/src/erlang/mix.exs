# mix.exs
defmodule SpcRuntime.MixProject do
  use Mix.Project

  def project do
    [
      apps_path: "apps",
      version: "0.1.0",
      start_permanent: Mix.env() == :prod,
      deps: deps(),
      releases: releases()
    ]
  end

  defp deps do
    []
  end

  defp releases do
    [
      spc_runtime: [
        applications: [
          spc_engine: :permanent,
          spc_boundary: :permanent
        ]
      ]
    ]
  end
end