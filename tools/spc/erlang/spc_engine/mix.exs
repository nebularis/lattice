# apps/spc_engine/mix.exs
defmodule SpcEngine.MixProject do
  use Mix.Project

  def project do
    [
      app: :spc_engine,
      version: "0.1.0",
      build_path: "../../_build",
      deps_path: "../../deps",
      lockfile: "../../mix.lock",
      language: :erlang,
      erlc_paths: ["src"],
      erlc_options: [:debug_info, :warnings_as_errors],
      start_permanent: Mix.env() == :prod,
      deps: deps()
    ]
  end

  def application do
    [
      mod: {:spc_app, []},
      extra_applications: [:logger, :crypto, :ssl],
      registered: [
        :spc_protocol_registry,
        :spc_session_sup,
        :spc_extension_sup,
        :spc_timer_service,
        :spc_job_service,
        :spc_compensation_service,
        :spc_signal_service
      ]
    ]
  end

  defp deps do
    [
      {:amqp_client, "~> 3.12", hex: :rabbit_common_compat},
      # We use the native Erlang amqp_client directly.
      # If the hex package is unavailable, pull from rabbitmq-erlang-client github.
    ]
  end
end