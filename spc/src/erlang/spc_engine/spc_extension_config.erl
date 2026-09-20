%%% spc_extension_config.erl
%%% Configuration schema for all SPC extensions.
%%% 
%%% The Python design-time pipeline generates a single JSON document per protocol
%%% version containing all extension configurations. This module loads and provides
%%% typed access to that configuration.
%%%
%%% The configuration is stored in persistent_term under the key
%%% {spc_extensions, ProtocolName, Version}.

-module(spc_extension_config).
-export([
    load/3,
    get_timer_config/3,
    get_job_config/3,
    get_error_config/3,
    get_compensation_config/2,
    get_signal_config/3,
    get_connector_config/2,
    get_all_timers_for_state/3,
    get_all_signals_for_label/3
]).

-type protocol_name() :: atom().
-type version() :: binary().
-type participant() :: atom().
-type state_id() :: non_neg_integer().
-type label() :: atom().

%% Timer configuration for a single state
-record(timer_cfg, {
    type        :: interrupting | non_interrupting,
    duration_ms :: pos_integer() | undefined,
    cron        :: binary() | undefined,
    datetime    :: binary() | undefined,        % ISO 8601
    timeout_label :: label(),
    target_state  :: state_id()
}).

%% Retry/job configuration for a single label
-record(job_cfg, {
    max_attempts    :: pos_integer(),
    backoff_strategy :: none | constant | exponential | jitter,
    base_delay_ms   :: non_neg_integer(),
    multiplier      :: float(),
    jitter_pct      :: float(),             % 0.0 - 1.0
    max_delay_ms    :: pos_integer(),
    on_exhausted    :: {error_label, label()} | {escalate, participant()}
}).

%% Error handler configuration for a state
-record(error_cfg, {
    error_type     :: business | transport | timeout | validation | unknown,
    recovery_label :: label() | undefined,
    recovery_state :: state_id() | undefined,
    escalate_to    :: participant() | undefined
}).

%% Compensation pair
-record(comp_pair, {
    action_label :: label(),
    action_state :: state_id(),
    comp_label   :: label(),
    comp_state   :: state_id()
}).

%% Compensation scope
-record(comp_scope, {
    scope_id :: atom(),
    pairs    :: [#comp_pair{}],
    ordering :: sequential | parallel
}).

%% Signal binding
-record(signal_cfg, {
    topic          :: binary(),
    exchange_type  :: direct | fanout | topic | headers,
    routing_key_template :: binary(),    % e.g., "session.{role}.{label}"
    correlation_fields   :: [binary()],  % Mork concept paths
    direction      :: emit | subscribe
}).

%% Connector binding (references a connector by name, not inline config)
-record(connector_binding, {
    connector_name :: atom(),
    label          :: label(),
    direction      :: egress | ingress,
    query_template :: binary() | undefined,   % for egress
    frame_path     :: binary() | undefined,   % JSON-LD frame for egress
    converter      :: atom() | undefined      % module for custom format
}).

-export_type([
    timer_cfg/0, job_cfg/0, error_cfg/0,
    comp_scope/0, signal_cfg/0, connector_binding/0
]).

%% ------------------------------------------------------------------
%% Loading
%% ------------------------------------------------------------------

-spec load(protocol_name(), version(), map()) -> ok.
load(Protocol, Version, JsonMap) ->
    %% JsonMap is the decoded JSON configuration from the design-time pipeline.
    %% We convert it to records and store in persistent_term.
    Parsed = parse_extensions(JsonMap),
    persistent_term:put({spc_extensions, Protocol, Version}, Parsed),
    ok.

%% ------------------------------------------------------------------
%% Accessors
%% ------------------------------------------------------------------

-spec get_timer_config(protocol_name(), participant(), state_id()) ->
    [#timer_cfg{}].
get_timer_config(Protocol, Participant, StateId) ->
    Ext = get_ext(Protocol),
    Key = {timer, Participant, StateId},
    maps:get(Key, Ext, []).

-spec get_all_timers_for_state(protocol_name(), participant(), state_id()) ->
    [#timer_cfg{}].
get_all_timers_for_state(Protocol, Participant, StateId) ->
    get_timer_config(Protocol, Participant, StateId).

-spec get_job_config(protocol_name(), participant(), label()) ->
    #job_cfg{} | undefined.
get_job_config(Protocol, Participant, Label) ->
    Ext = get_ext(Protocol),
    Key = {job, Participant, Label},
    maps:get(Key, Ext, undefined).

-spec get_error_config(protocol_name(), participant(), atom()) ->
    #error_cfg{} | undefined.
get_error_config(Protocol, Participant, ErrorType) ->
    Ext = get_ext(Protocol),
    Key = {error, Participant, ErrorType},
    maps:get(Key, Ext, undefined).

-spec get_compensation_config(protocol_name(), atom()) ->
    #comp_scope{} | undefined.
get_compensation_config(Protocol, ScopeId) ->
    Ext = get_ext(Protocol),
    Key = {compensation, ScopeId},
    maps:get(Key, Ext, undefined).

-spec get_signal_config(protocol_name(), participant(), label()) ->
    [#signal_cfg{}].
get_signal_config(Protocol, Participant, Label) ->
    Ext = get_ext(Protocol),
    Key = {signal, Participant, Label},
    maps:get(Key, Ext, []).

-spec get_all_signals_for_label(protocol_name(), participant(), label()) ->
    [#signal_cfg{}].
get_all_signals_for_label(Protocol, Participant, Label) ->
    get_signal_config(Protocol, Participant, Label).

-spec get_connector_config(protocol_name(), atom()) ->
    map() | undefined.
get_connector_config(Protocol, ConnectorName) ->
    Ext = get_ext(Protocol),
    Key = {connector, ConnectorName},
    maps:get(Key, Ext, undefined).

%% ------------------------------------------------------------------
%% Internal: fetch from persistent_term
%% ------------------------------------------------------------------

get_ext(Protocol) ->
    %% Find the current version. In production, this would be tracked
    %% by the protocol registry. For now, use 'current'.
    case persistent_term:get({spc_extensions, Protocol, current}, undefined) of
        undefined -> #{};
        Ext -> Ext
    end.

%% ------------------------------------------------------------------
%% Internal: parse the JSON configuration into the indexed map
%% ------------------------------------------------------------------

parse_extensions(JsonMap) ->
    M0 = #{},
    M1 = parse_timers(maps:get(<<"timers">>, JsonMap, []), M0),
    M2 = parse_jobs(maps:get(<<"jobs">>, JsonMap, []), M1),
    M3 = parse_errors(maps:get(<<"errors">>, JsonMap, []), M2),
    M4 = parse_compensation(maps:get(<<"compensation">>, JsonMap, []), M3),
    M5 = parse_signals(maps:get(<<"signals">>, JsonMap, []), M4),
    M6 = parse_connectors(maps:get(<<"connectors">>, JsonMap, []), M5),
    M6.

parse_timers([], Acc) -> Acc;
parse_timers([T | Rest], Acc) ->
    Participant = binary_to_atom(maps:get(<<"participant">>, T)),
    StateId = maps:get(<<"state_id">>, T),
    Cfg = #timer_cfg{
        type = binary_to_atom(maps:get(<<"type">>, T, <<"interrupting">>)),
        duration_ms = maps:get(<<"duration_ms">>, T, undefined),
        cron = maps:get(<<"cron">>, T, undefined),
        datetime = maps:get(<<"datetime">>, T, undefined),
        timeout_label = binary_to_atom(maps:get(<<"timeout_label">>, T)),
        target_state = maps:get(<<"target_state">>, T)
    },
    Key = {timer, Participant, StateId},
    Existing = maps:get(Key, Acc, []),
    parse_timers(Rest, Acc#{Key => Existing ++ [Cfg]}).

parse_jobs([], Acc) -> Acc;
parse_jobs([J | Rest], Acc) ->
    Participant = binary_to_atom(maps:get(<<"participant">>, J)),
    Label = binary_to_atom(maps:get(<<"label">>, J)),
    Cfg = #job_cfg{
        max_attempts = maps:get(<<"max_attempts">>, J, 3),
        backoff_strategy = binary_to_atom(maps:get(<<"backoff_strategy">>, J, <<"exponential">>)),
        base_delay_ms = maps:get(<<"base_delay_ms">>, J, 1000),
        multiplier = maps:get(<<"multiplier">>, J, 2.0),
        jitter_pct = maps:get(<<"jitter_pct">>, J, 0.1),
        max_delay_ms = maps:get(<<"max_delay_ms">>, J, 60000),
        on_exhausted = parse_on_exhausted(maps:get(<<"on_exhausted">>, J))
    },
    Key = {job, Participant, Label},
    parse_jobs(Rest, Acc#{Key => Cfg}).

parse_errors([], Acc) -> Acc;
parse_errors([E | Rest], Acc) ->
    Participant = binary_to_atom(maps:get(<<"participant">>, E)),
    ErrorType = binary_to_atom(maps:get(<<"error_type">>, E)),
    Cfg = #error_cfg{
        error_type = ErrorType,
        recovery_label = opt_atom(maps:get(<<"recovery_label">>, E, null)),
        recovery_state = maps:get(<<"recovery_state">>, E, undefined),
        escalate_to = opt_atom(maps:get(<<"escalate_to">>, E, null))
    },
    Key = {error, Participant, ErrorType},
    parse_errors(Rest, Acc#{Key => Cfg}).

parse_compensation([], Acc) -> Acc;
parse_compensation([C | Rest], Acc) ->
    ScopeId = binary_to_atom(maps:get(<<"scope_id">>, C)),
    Pairs = [#comp_pair{
        action_label = binary_to_atom(maps:get(<<"action_label">>, P)),
        action_state = maps:get(<<"action_state">>, P),
        comp_label = binary_to_atom(maps:get(<<"comp_label">>, P)),
        comp_state = maps:get(<<"comp_state">>, P)
    } || P <- maps:get(<<"pairs">>, C, [])],
    Cfg = #comp_scope{
        scope_id = ScopeId,
        pairs = Pairs,
        ordering = binary_to_atom(maps:get(<<"ordering">>, C, <<"sequential">>))
    },
    Key = {compensation, ScopeId},
    parse_compensation(Rest, Acc#{Key => Cfg}).

parse_signals([], Acc) -> Acc;
parse_signals([S | Rest], Acc) ->
    Participant = binary_to_atom(maps:get(<<"participant">>, S)),
    Label = binary_to_atom(maps:get(<<"label">>, S)),
    Cfg = #signal_cfg{
        topic = maps:get(<<"topic">>, S),
        exchange_type = binary_to_atom(maps:get(<<"exchange_type">>, S, <<"topic">>)),
        routing_key_template = maps:get(<<"routing_key_template">>, S, <<>>),
        correlation_fields = maps:get(<<"correlation_fields">>, S, []),
        direction = binary_to_atom(maps:get(<<"direction">>, S, <<"emit">>))
    },
    Key = {signal, Participant, Label},
    Existing = maps:get(Key, Acc, []),
    parse_signals(Rest, Acc#{Key => Existing ++ [Cfg]}).

parse_connectors([], Acc) -> Acc;
parse_connectors([C | Rest], Acc) ->
    Name = binary_to_atom(maps:get(<<"name">>, C)),
    %% Store the entire connector config map — it's read by the
    %% HTTP client and AMQP bridge directly.
    Key = {connector, Name},
    parse_connectors(Rest, Acc#{Key => C}).

%% Helpers

parse_on_exhausted(#{<<"type">> := <<"error_label">>, <<"label">> := L}) ->
    {error_label, binary_to_atom(L)};
parse_on_exhausted(#{<<"type">> := <<"escalate">>, <<"to">> := T}) ->
    {escalate, binary_to_atom(T)};
parse_on_exhausted(_) ->
    {error_label, retry_exhausted}.

opt_atom(null) -> undefined;
opt_atom(undefined) -> undefined;
opt_atom(B) when is_binary(B) -> binary_to_atom(B).

binary_to_atom(B) when is_binary(B) -> binary_to_existing_atom(B, utf8);
binary_to_atom(A) when is_atom(A) -> A.