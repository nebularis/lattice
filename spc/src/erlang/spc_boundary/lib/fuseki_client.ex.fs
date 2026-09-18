# apps/spc_boundary/lib/spc_boundary/fuseki_client.ex
defmodule SpcBoundary.FusekiClient do
  @moduledoc """
  Client for Apache Jena Fuseki. Executes pre-compiled SPARQL templates
  with parameter substitution.

  The query registry (generated at design time) maps template names to
  .rq files and their parameter schemas. At startup, the templates are
  loaded and parsed. At runtime, parameters are substituted and the
  query is sent to Fuseki via SPARQL Protocol (HTTP POST).
  """

  require Logger

  @fuseki_url Application.compile_env(:spc_boundary, :fuseki_url, "http://localhost:3030")
  @dataset Application.compile_env(:spc_boundary, :fuseki_dataset, "spc")

  @doc """
  Execute a named SPARQL template with the given parameters.
  Returns {:ok, result} where result is parsed RDF or JSON-LD,
  or {:error, reason}.
  """
  @spec execute_template(atom() | binary(), map()) :: {:ok, term()} | {:error, term()}
  def execute_template(template_name, params) do
    case get_template(template_name) do
      nil ->
        {:error, {:unknown_template, template_name}}

      template_config ->
        query_text = substitute_params(template_config, params)
        execute_query(query_text, template_config)
    end
  end

  @doc """
  Execute a SPARQL UPDATE (INSERT DATA) to materialise triples.
  Used by ingress endpoints.
  """
  @spec insert_triples(binary()) :: :ok | {:error, term()}
  def insert_triples(sparql_update) do
    url = "#{@fuseki_url}/#{@dataset}/update"

    request = Finch.build(:post, url,
                [{"content-type", "application/sparql-update"}],
                sparql_update)

    case Finch.request(request, SpcBoundary.Finch, receive_timeout: 30_000) do
      {:ok, %{status: status}} when status in [200, 204] ->
        :ok
      {:ok, %{status: status, body: body}} ->
        {:error, {:fuseki_error, status, body}}
      {:error, reason} ->
        {:error, {:transport, reason}}
    end
  end

  @doc """
  Execute a raw SPARQL CONSTRUCT query and return the result
  as a JSON-LD string (leveraging Fuseki's JSON-LD support).
  """
  @spec construct_as_jsonld(binary()) :: {:ok, binary()} | {:error, term()}
  def construct_as_jsonld(query_text) do
    url = "#{@fuseki_url}/#{@dataset}/query"

    request = Finch.build(:post, url,
                [{"content-type", "application/sparql-query"},
                 {"accept", "application/ld+json"}],
                query_text)

    case Finch.request(request, SpcBoundary.Finch, receive_timeout: 30_000) do
      {:ok, %{status: 200, body: body}} ->
        {:ok, body}
      {:ok, %{status: status, body: body}} ->
        {:error, {:fuseki_error, status, body}}
      {:error, reason} ->
        {:error, {:transport, reason}}
    end
  end

  # ------------------------------------------------------------------
  # Template management
  # ------------------------------------------------------------------

  defp get_template(name) do
    registry = :persistent_term.get({:spc_query_registry}, %{})
    Map.get(registry, to_string(name))
  end

  defp substitute_params(%{"template" => template, "parameters" => param_defs}, params) do
    Enum.reduce(param_defs, template, fn {param_name, param_spec}, query ->
      value = Map.get(params, String.to_atom(param_name))
              || Map.get(params, param_name)

      placeholder = "?#{param_name}"
      replacement = format_sparql_value(value, Map.get(param_spec, "type", "string"))

      String.replace(query, placeholder, replacement)
    end)
  end

  defp format_sparql_value(nil, _type), do: "UNDEF"
  defp format_sparql_value(value, "iri"), do: "<#{value}>"
  defp format_sparql_value(value, "string"), do: ~s("#{escape_sparql(value)}")
  defp format_sparql_value(value, "integer"), do: "#{value}"
  defp format_sparql_value(value, "decimal"), do: "#{value}"
  defp format_sparql_value(value, _), do: ~s("#{value}")

  defp escape_sparql(s) when is_binary(s) do
    s
    |> String.replace("\\", "\\\\")
    |> String.replace("\"", "\\\"")
    |> String.replace("\n", "\\n")
  end
  defp escape_sparql(s), do: escape_sparql(to_string(s))

  defp execute_query(query_text, template_config) do
    output_format = Map.get(template_config, "output_format", "json-ld")

    case output_format do
      "json-ld" ->
        construct_as_jsonld(query_text)

      "sparql-results" ->
        execute_select(query_text)

      _ ->
        construct_as_jsonld(query_text)
    end
  end

  defp execute_select(query_text) do
    url = "#{@fuseki_url}/#{@dataset}/query"

    request = Finch.build(:post, url,
                [{"content-type", "application/sparql-query"},
                 {"accept", "application/sparql-results+json"}],
                query_text)

    case Finch.request(request, SpcBoundary.Finch, receive_timeout: 30_000) do
      {:ok, %{status: 200, body: body}} ->
        {:ok, Jason.decode!(body)}
      {:ok, %{status: status, body: body}} ->
        {:error, {:fuseki_error, status, body}}
      {:error, reason} ->
        {:error, {:transport, reason}}
    end
  end
end