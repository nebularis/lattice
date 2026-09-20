# apps/spc_boundary/lib/spc_boundary/http_connector.ex
defmodule SpcBoundary.HttpConnector do
  @moduledoc """
  Configuration-driven HTTP client for SPC connector bindings.

  Each connector is defined by configuration generated from the
  Connector ontology (EXT-Connector). The configuration specifies:
  - Base URL
  - Supported methods
  - Authentication (bearer, basic, client_cert, oauth2)
  - Timeout
  - TLS/certificate references
  - Retry policy (delegated to spc_job_service)

  This module does NOT perform retries itself — it executes a single
  HTTP request and returns the result. The job service wraps this in
  retry logic when configured.

  Called from Erlang as:
    'Elixir.SpcBoundary.HttpConnector':request(ConnectorName, Method, Path, Body, Opts)
  """

  require Logger

  @type connector_name :: atom()
  @type method :: :get | :post | :put | :patch | :delete
  @type response :: {:ok, status :: integer(), headers :: list(), body :: binary()}
                  | {:error, term()}

  # ------------------------------------------------------------------
  # Public API
  # ------------------------------------------------------------------

  @doc """
  Execute an HTTP request against a named connector.
  The connector configuration is loaded from persistent_term.
  """
  @spec request(connector_name(), method(), binary(), binary() | nil, map()) :: response()
  def request(connector_name, method, path, body, opts \\ %{}) do
    case get_connector_config(connector_name) do
      nil ->
        {:error, {:unknown_connector, connector_name}}

      config ->
        do_request(config, method, path, body, opts)
    end
  end

  @doc """
  Execute an egress request: query Fuseki for data, format it, and POST/PUT
  to the connector endpoint. This combines the egress query + format + send
  into a single operation.

  - query_template: name of the pre-compiled SPARQL template
  - query_params: parameter bindings for the template
  - connector_name: target connector
  - method: HTTP method
  - path: URL path suffix
  """
  @spec egress_request(atom(), map(), connector_name(), method(), binary()) :: response()
  def egress_request(query_template, query_params, connector_name, method, path) do
    with {:ok, rdf_result} <- SpcBoundary.FusekiClient.execute_template(
                                query_template, query_params),
         {:ok, formatted} <- SpcBoundary.EgressFormatter.format(
                                query_template, rdf_result),
         result <- request(connector_name, method, path, formatted) do
      result
    end
  end

  # ------------------------------------------------------------------
  # Internal: request execution
  # ------------------------------------------------------------------

  defp do_request(config, method, path, body, opts) do
    base_url = Map.fetch!(config, "base_url")
    url = URI.merge(base_url, path) |> URI.to_string()
    timeout_ms = Map.get(config, "timeout_ms", 30_000)

    headers = build_headers(config, opts)
    finch_method = method_atom(method)

    request = Finch.build(finch_method, url, headers, body)

    case Finch.request(request, SpcBoundary.Finch,
                        receive_timeout: timeout_ms,
                        pool_timeout: 5_000) do
      {:ok, %Finch.Response{status: status, headers: resp_headers, body: resp_body}} ->
        {:ok, status, resp_headers, resp_body}

      {:error, %Mint.TransportError{reason: reason}} ->
        {:error, {:transport, reason}}

      {:error, %Mint.HTTPError{reason: reason}} ->
        {:error, {:http_error, reason}}

      {:error, reason} ->
        {:error, {:request_failed, reason}}
    end
  end

  defp build_headers(config, opts) do
    base_headers = [
      {"content-type", Map.get(opts, :content_type, "application/json")},
      {"accept", Map.get(opts, :accept, "application/json")},
      {"user-agent", "SPC-Runtime/0.1"}
    ]

    auth_headers = build_auth_headers(config)
    custom_headers = Map.get(config, "headers", %{})
                     |> Enum.map(fn {k, v} -> {to_string(k), to_string(v)} end)

    base_headers ++ auth_headers ++ custom_headers
  end

  defp build_auth_headers(config) do
    case Map.get(config, "auth") do
      nil ->
        []

      %{"type" => "bearer", "token_source" => source} ->
        token = resolve_token(source)
        [{"authorization", "Bearer #{token}"}]

      %{"type" => "basic", "username" => user, "password_ref" => pass_ref} ->
        password = resolve_secret(pass_ref)
        encoded = Base.encode64("#{user}:#{password}")
        [{"authorization", "Basic #{encoded}"}]

      %{"type" => "oauth2"} = oauth_config ->
        token = obtain_oauth2_token(oauth_config)
        [{"authorization", "Bearer #{token}"}]

      %{"type" => "api_key", "header_name" => header, "key_ref" => key_ref} ->
        key = resolve_secret(key_ref)
        [{to_string(header), to_string(key)}]

      _ ->
        []
    end
  end

  defp resolve_token(source) when is_binary(source) do
    # Token source might be an environment variable, a vault path,
    # or a static value. For POC, use env var.
    System.get_env(source) || ""
  end

  defp resolve_secret(ref) when is_binary(ref) do
    System.get_env(ref) || ""
  end

  defp obtain_oauth2_token(%{"token_url" => url, "client_id" => cid,
                              "client_secret_ref" => secret_ref,
                              "scope" => scope}) do
    # TODO: Cache tokens, handle expiry. For POC, fetch fresh each time.
    secret = resolve_secret(secret_ref)
    body = URI.encode_query(%{
      "grant_type" => "client_credentials",
      "client_id" => cid,
      "client_secret" => secret,
      "scope" => scope
    })

    request = Finch.build(:post, url,
                [{"content-type", "application/x-www-form-urlencoded"}],
                body)

    case Finch.request(request, SpcBoundary.Finch, receive_timeout: 10_000) do
      {:ok, %{status: 200, body: resp_body}} ->
        case Jason.decode(resp_body) do
          {:ok, %{"access_token" => token}} -> token
          _ -> ""
        end
      _ ->
        Logger.error("OAuth2 token fetch failed for #{url}")
        ""
    end
  end

  defp obtain_oauth2_token(_), do: ""

  defp method_atom(:get), do: :get
  defp method_atom(:post), do: :post
  defp method_atom(:put), do: :put
  defp method_atom(:patch), do: :patch
  defp method_atom(:delete), do: :delete
  defp method_atom(m) when is_binary(m), do: String.downcase(m) |> String.to_atom()

  # ------------------------------------------------------------------
  # Configuration access
  # ------------------------------------------------------------------

  defp get_connector_config(connector_name) do
    # Connector configs are stored in persistent_term by the extension
    # config loader. The Erlang module spc_extension_config stores them
    # under {connector, Name} within the extension map.
    # We access via the Erlang module directly.
    :spc_extension_config.get_connector_config(:current_protocol, connector_name)
  end
end