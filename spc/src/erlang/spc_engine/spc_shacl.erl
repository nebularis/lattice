%%%-------------------------------------------------------------------
%%% @doc SHACL Validation Interface
%%%
%%% Provides payload validation against SHACL shapes.
%%% Used as a fallback for non-Mork-mapped channels.
%%%
%%% This module wraps an external SHACL validator (e.g., via NIF
%%% to a Rust library, or via HTTP to a validation service).
%%% @end
%%%-------------------------------------------------------------------
-module(spc_shacl).

-export([
    validate/2,
    load_shape/1,
    validate_with_shape/2
]).

-type shape_ref() :: binary().
-type payload() :: map().
-type validation_result() :: ok | {error, [validation_error()]}.
-type validation_error() :: #{
    path := binary(),
    message := binary(),
    severity := violation | warning | info
}.

%%====================================================================
%% API
%%====================================================================

-spec validate(shape_ref(), payload()) -> validation_result().
validate(ShapeRef, Payload) ->
    case load_shape(ShapeRef) of
        {ok, Shape} ->
            validate_with_shape(Shape, Payload);
        {error, Reason} ->
            {error, [{#{path => <<"">>, 
                        message => iolist_to_binary(io_lib:format("Failed to load shape: ~p", [Reason])),
                        severity => violation}}]}
    end.

-spec load_shape(shape_ref()) -> {ok, term()} | {error, term()}.
load_shape(ShapeRef) ->
    %% In a real implementation, this would:
    %% 1. Check a cache for the compiled shape
    %% 2. If not cached, load the Turtle file
    %% 3. Parse and compile to an internal representation
    %% 4. Cache and return
    
    %% For now, return a stub that validates basic structure
    case filelib:is_regular(ShapeRef) of
        true ->
            {ok, #{shape_ref => ShapeRef, validator => stub}};
        false ->
            %% Allow inline shape names for testing
            {ok, #{shape_ref => ShapeRef, validator => stub}}
    end.

-spec validate_with_shape(term(), payload()) -> validation_result().
validate_with_shape(#{validator := stub}, Payload) when is_map(Payload) ->
    %% Stub validator: always passes if payload is a map
    ok;
validate_with_shape(#{validator := stub}, _Payload) ->
    {error, [#{path => <<"">>,
               message => <<"Payload must be a map">>,
               severity => violation}]};
validate_with_shape(#{validator := external, endpoint := Endpoint}, Payload) ->
    %% External HTTP validator
    validate_external(Endpoint, Payload).

validate_external(Endpoint, Payload) ->
    Body = jsx:encode(#{payload => Payload}),
    case httpc:request(post, {binary_to_list(Endpoint), [], "application/json", Body}, [], []) of
        {ok, {{_, 200, _}, _, ResponseBody}} ->
            case jsx:decode(list_to_binary(ResponseBody), [return_maps]) of
                #{<<"valid">> := true} -> ok;
                #{<<"errors">> := Errors} -> {error, convert_errors(Errors)}
            end;
        {error, Reason} ->
            {error, [#{path => <<"">>,
                       message => iolist_to_binary(io_lib:format("Validation service error: ~p", [Reason])),
                       severity => violation}]}
    end.

convert_errors(Errors) ->
    [#{path => maps:get(<<"path">>, E, <<"">>),
       message => maps:get(<<"message">>, E, <<"Unknown error">>),
       severity => binary_to_atom(maps:get(<<"severity">>, E, <<"violation">>), utf8)}
     || E <- Errors].