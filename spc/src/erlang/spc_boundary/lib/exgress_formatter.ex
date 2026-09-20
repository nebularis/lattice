# apps/spc_boundary/lib/spc_boundary/egress_formatter.ex
defmodule SpcBoundary.EgressFormatter do
  @moduledoc """
  Formats SPARQL CONSTRUCT results into target formats for egress.

  The formatting strategy is determined by the query template configuration:
  - "json-ld": the result is already JSON-LD from Fuseki; optionally apply
    a JSON-LD frame for reshaping
  - "custom": delegate to a converter module (generated at design time)
  - "passthrough": return the raw result

  JSON-LD framing is the preferred approach because it requires no
  generated code — only a frame document (generated at design time as a
  JSON file). The frame specifies the shape of the output JSON, and
  the JSON-LD processor handles the transformation.
  """

  require Logger

  @doc """
  Format a query result according to the template's output configuration.
  """
  @spec format(atom() | binary(), term()) :: {:ok, binary()} | {:error, term()}
  def format(template_name, result) do
    registry = :persistent_term.get({:spc_query_registry}, %{})
    config = Map.get(registry, to_string(template_name), %{})

    case Map.get(config, "output_format", "passthrough") do
      "json-ld" ->
        apply_frame(result, config)

      "custom" ->
        apply_custom_converter(result, config)

      "passthrough" ->
        {:ok, result}

      other ->
        {:error, {:unknown_format, other}}
    end
  end

  # ------------------------------------------------------------------
  # JSON-LD framing
  # ------------------------------------------------------------------

  defp apply_frame(jsonld_result, config) do
    case Map.get(config, "frame_file") of
      nil ->
        # No frame — return the JSON-LD as-is
        {:ok, jsonld_result}

      frame_path ->
        # Load the frame (cached in persistent_term)
        frame = load_frame(frame_path)
        # Apply the frame using the JSON-LD library
        # For POC, we use a simplified framing approach.
        # In production, use a proper JSON-LD processor (e.g., json_ld hex package).
        apply_jsonld_frame(jsonld_result, frame)
    end
  end

  defp load_frame(frame_path) do
    cache_key = {:spc_jsonld_frame, frame_path}
    case :persistent_term.get(cache_key, :not_loaded) do
      :not_loaded ->
        case File.read(frame_path) do
          {:ok, content} ->
            frame = Jason.decode!(content)
            :persistent_term.put(cache_key, frame)
            frame
          {:error, reason} ->
            Logger.error("Failed to load JSON-LD frame #{frame_path}: #{inspect(reason)}")
            %{}
        end
      frame ->
        frame
    end
  end

  defp apply_jsonld_frame(jsonld_binary, frame) when is_binary(jsonld_binary) do
    case Jason.decode(jsonld_binary) do
      {:ok, jsonld_doc} ->
        apply_jsonld_frame(jsonld_doc, frame)
      {:error, reason} ->
        {:error, {:json_parse_failed, reason}}
    end
  end

  defp apply_jsonld_frame(jsonld_doc, frame) when is_map(jsonld_doc) do
    # Simplified JSON-LD framing: extract the @graph, match against
    # the frame's @type, and restructure.
    # A full implementation would use the JSON-LD 1.1 Framing Algorithm.
    # For POC, we do a best-effort extraction.
    graph = case jsonld_doc do
      %{"@graph" => g} -> g
      doc when is_list(doc) -> doc
      doc -> [doc]
    end

    target_type = Map.get(frame, "@type")
    context = Map.get(frame, "@context", %{})

    # Find nodes matching the frame's @type
    matching = Enum.filter(graph, fn node ->
      node_types = List.wrap(Map.get(node, "@type", []))
      target_type == nil or target_type in node_types
    end)

    # Apply context mapping: rename keys from IRIs to short names
    formatted = Enum.map(matching, fn node ->
      apply_context(node, context)
    end)

    result = case formatted do
      [single] -> single
      multiple -> multiple
    end

    {:ok, Jason.encode!(result)}
  end

  defp apply_context(node, context) when is_map(node) do
    # Reverse the context: IRI -> short name
    reverse_ctx = Enum.reduce(context, %{}, fn
      {short_name, iri}, acc when is_binary(iri) -> Map.put(acc, iri, short_name)
      {short_name, %{"@id" => iri}}, acc -> Map.put(acc, iri, short_name)
      _, acc -> acc
    end)

    Enum.reduce(node, %{}, fn {key, value}, acc ->
      short_key = Map.get(reverse_ctx, key, key)
      # Skip JSON-LD keywords in output unless explicitly mapped
      case short_key do
        "@" <> _ -> acc
        _ -> Map.put(acc, short_key, unwrap_value(value))
      end
    end)
  end

  defp unwrap_value(%{"@value" => v}), do: v
  defp unwrap_value(%{"@id" => id}), do: id
  defp unwrap_value(v) when is_list(v), do: Enum.map(v, &unwrap_value/1)
  defp unwrap_value(v), do: v

  # ------------------------------------------------------------------
  # Custom converter delegation
  # ------------------------------------------------------------------

  defp apply_custom_converter(result, config) do
    case Map.get(config, "converter_module") do
      nil ->
        {:error, :no_converter_module}

      module_name ->
        module = String.to_existing_atom(module_name)
        module.convert(result)
    end
  end
end