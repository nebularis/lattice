%%%-------------------------------------------------------------------
%%% @doc SPC Subject Configuration
%%%
%%% Defines the data structures for subject state machine tables,
%%% session state, and all related types. This module is the single
%%% source of truth for the shape of these structures.
%%%
%%% The state machine table is loaded once per protocol version and
%%% stored in persistent_term. Subject processes reference it without
%%% copying. Session-specific mutable state (current state ID, session
%%% references) is held in each subject process's gen_statem data.
%%% @end
%%%-------------------------------------------------------------------
-module(spc_config).

-export([
    %% Table loading and access
    load_protocol/1,
    load_protocol_from_term/2,
    get_protocol_table/1,
    unload_protocol/1,
    
    %% Table queries
    lookup_participant/2,
    lookup_state/2,
    state_type/1,
    state_partner/1,
    state_labels/1,
    state_transitions/1,
    state_shapes/1,
    state_mork/1,
    state_timeout/1,
    is_valid_label/2,
    next_state/2,
    is_mork_mapped/2,
    shape_for_label/2,
    
    %% Call state queries
    call_subprotocol/1,
    call_role_mapping/1,
    call_return_state/1,
    
    %% Session data construction and access
    new_session_data/5,
    session_id/1,
    protocol_name/1,
    participant_id/1,
    current_state_id/1,
    participant_table/1,
    session_coordinator/1,
    advance_state/2,
    call_stack/1,
    push_call/3,
    pop_call/1,
    
    %% Protocol metadata
    protocol_version/1,
    initial_state/1,
    all_participants/1
]).

-export_type([
    protocol_table/0,
    participant_table/0,
    state_descriptor/0,
    session_data/0,
    state_id/0,
    label/0,
    participant/0
]).

%%====================================================================
%% Types
%%====================================================================

-type state_id()    :: non_neg_integer().
-type label()       :: atom().
-type participant() :: atom().
-type shape_ref()   :: binary().

-type timeout_spec() :: #{
    duration_ms := pos_integer(),
    target      := state_id()
} | undefined.

-type state_descriptor() :: #{
    type        := send | recv | 'end' | call,
    partner     => participant(),
    labels      => #{label() := true},
    transitions => #{label() := state_id()},
    shapes      => #{label() := shape_ref()},
    mork        => #{label() := boolean()},
    timeout     => timeout_spec(),
    subprotocol  => atom(),
    role_mapping => #{atom() := participant()},
    return_state => state_id()
}.

-type participant_table() :: #{
    initial_state := state_id(),
    states        := #{state_id() := state_descriptor()}
}.

-type protocol_table() :: #{
    protocol     := atom(),
    version      := binary(),
    participants := #{participant() := participant_table()}
}.

-record(session_data, {
    session_id       :: binary(),
    protocol_name    :: atom(),
    participant_id   :: participant(),
    current_state_id :: state_id(),
    ptable           :: participant_table(),
    coordinator      :: pid(),
    call_stack = []  :: [{state_id(), pid()}]
}).

-opaque session_data() :: #session_data{}.

%%====================================================================
%% Protocol Table Loading
%%====================================================================

-spec load_protocol(file:filename()) -> {ok, atom()} | {error, term()}.
load_protocol(JsonPath) ->
    case file:read_file(JsonPath) of
        {ok, Binary} ->
            case jsx:decode(Binary, [return_maps]) of
                #{<<"protocol">> := ProtocolBin} = RawTable ->
                    ErlTable = convert_raw_table(RawTable),
                    ProtocolName = binary_to_atom(ProtocolBin, utf8),
                    ok = validate_table(ErlTable),
                    persistent_term:put({spc_protocol, ProtocolName}, ErlTable),
                    {ok, ProtocolName};
                _ ->
                    {error, invalid_table_format}
            end;
        {error, Reason} ->
            {error, {file_read_failed, Reason}}
    end.

-spec load_protocol_from_term(atom(), protocol_table()) -> ok.
load_protocol_from_term(ProtocolName, Table) ->
    ok = validate_table(Table),
    persistent_term:put({spc_protocol, ProtocolName}, Table),
    ok.

-spec get_protocol_table(atom()) -> protocol_table().
get_protocol_table(ProtocolName) ->
    persistent_term:get({spc_protocol, ProtocolName}).

-spec unload_protocol(atom()) -> boolean().
unload_protocol(ProtocolName) ->
    persistent_term:erase({spc_protocol, ProtocolName}).

%%====================================================================
%% Table Queries
%%====================================================================

-spec lookup_participant(participant(), protocol_table()) ->
    {ok, participant_table()} | error.
lookup_participant(ParticipantId, #{participants := Participants}) ->
    maps:find(ParticipantId, Participants).

-spec lookup_state(state_id(), participant_table()) ->
    {ok, state_descriptor()} | error.
lookup_state(StateId, #{states := States}) ->
    maps:find(StateId, States).

-spec state_type(state_descriptor()) -> send | recv | 'end' | call.
state_type(#{type := Type}) -> Type.

-spec state_partner(state_descriptor()) -> participant().
state_partner(#{partner := Partner}) -> Partner.

-spec state_labels(state_descriptor()) -> #{label() := true}.
state_labels(#{labels := Labels}) -> Labels;
state_labels(_) -> #{}.

-spec state_transitions(state_descriptor()) -> #{label() := state_id()}.
state_transitions(#{transitions := Transitions}) -> Transitions;
state_transitions(_) -> #{}.

-spec state_shapes(state_descriptor()) -> #{label() := shape_ref()}.
state_shapes(#{shapes := Shapes}) -> Shapes;
state_shapes(_) -> #{}.

-spec state_mork(state_descriptor()) -> #{label() := boolean()}.
state_mork(#{mork := Mork}) -> Mork;
state_mork(_) -> #{}.

-spec state_timeout(state_descriptor()) -> timeout_spec().
state_timeout(#{timeout := Timeout}) -> Timeout;
state_timeout(_) -> undefined.

-spec is_valid_label(label(), state_descriptor()) -> boolean().
is_valid_label(Label, State) ->
    maps:is_key(Label, state_labels(State)).

-spec next_state(label(), state_descriptor()) -> {ok, state_id()} | error.
next_state(Label, State) ->
    maps:find(Label, state_transitions(State)).

-spec is_mork_mapped(label(), state_descriptor()) -> boolean().
is_mork_mapped(Label, State) ->
    maps:get(Label, state_mork(State), false).

-spec shape_for_label(label(), state_descriptor()) -> {ok, shape_ref()} | error.
shape_for_label(Label, State) ->
    maps:find(Label, state_shapes(State)).

%%====================================================================
%% Call State Queries
%%====================================================================

-spec call_subprotocol(state_descriptor()) -> atom().
call_subprotocol(#{subprotocol := Sub}) -> Sub.

-spec call_role_mapping(state_descriptor()) -> #{atom() := participant()}.
call_role_mapping(#{role_mapping := Mapping}) -> Mapping;
call_role_mapping(_) -> #{}.

-spec call_return_state(state_descriptor()) -> state_id().
call_return_state(#{return_state := ReturnState}) -> ReturnState.

%%====================================================================
%% Session Data Construction and Access
%%====================================================================

-spec new_session_data(binary(), atom(), participant(), participant_table(), pid()) 
    -> session_data().
new_session_data(SessionId, ProtocolName, ParticipantId, PTable, Coordinator) ->
    #{initial_state := InitialState} = PTable,
    #session_data{
        session_id = SessionId,
        protocol_name = ProtocolName,
        participant_id = ParticipantId,
        current_state_id = InitialState,
        ptable = PTable,
        coordinator = Coordinator,
        call_stack = []
    }.

-spec session_id(session_data()) -> binary().
session_id(#session_data{session_id = Id}) -> Id.

-spec protocol_name(session_data()) -> atom().
protocol_name(#session_data{protocol_name = Name}) -> Name.

-spec participant_id(session_data()) -> participant().
participant_id(#session_data{participant_id = Id}) -> Id.

-spec current_state_id(session_data()) -> state_id().
current_state_id(#session_data{current_state_id = Id}) -> Id.

-spec participant_table(session_data()) -> participant_table().
participant_table(#session_data{ptable = PTable}) -> PTable.

-spec session_coordinator(session_data()) -> pid().
session_coordinator(#session_data{coordinator = Coord}) -> Coord.

-spec advance_state(state_id(), session_data()) -> session_data().
advance_state(NewStateId, Data) ->
    Data#session_data{current_state_id = NewStateId}.

-spec call_stack(session_data()) -> [{state_id(), pid()}].
call_stack(#session_data{call_stack = Stack}) -> Stack.

-spec push_call(state_id(), pid(), session_data()) -> session_data().
push_call(ReturnState, SubCoordinator, Data = #session_data{call_stack = Stack}) ->
    Data#session_data{call_stack = [{ReturnState, SubCoordinator} | Stack]}.

-spec pop_call(session_data()) -> {ok, state_id(), pid(), session_data()} | empty.
pop_call(#session_data{call_stack = []}) ->
    empty;
pop_call(Data = #session_data{call_stack = [{ReturnState, SubCoord} | Rest]}) ->
    {ok, ReturnState, SubCoord, Data#session_data{call_stack = Rest}}.

%%====================================================================
%% Protocol Metadata
%%====================================================================

-spec protocol_version(protocol_table()) -> binary().
protocol_version(#{version := Version}) -> Version.

-spec initial_state(participant_table()) -> state_id().
initial_state(#{initial_state := State}) -> State.

-spec all_participants(protocol_table()) -> [participant()].
all_participants(#{participants := Participants}) ->
    maps:keys(Participants).

%%====================================================================
%% Internal Functions
%%====================================================================

convert_raw_table(#{<<"protocol">> := Protocol, 
                    <<"version">> := Version,
                    <<"participants">> := Participants}) ->
    #{
        protocol => binary_to_atom(Protocol, utf8),
        version => Version,
        participants => maps:fold(
            fun(K, V, Acc) ->
                maps:put(binary_to_atom(K, utf8), convert_participant_table(V), Acc)
            end,
            #{},
            Participants
        )
    }.

convert_participant_table(#{<<"initial_state">> := InitialState,
                            <<"states">> := States}) ->
    #{
        initial_state => InitialState,
        states => maps:fold(
            fun(K, V, Acc) ->
                StateId = case is_binary(K) of
                    true -> binary_to_integer(K);
                    false -> K
                end,
                maps:put(StateId, convert_state_descriptor(V), Acc)
            end,
            #{},
            States
        )
    }.

convert_state_descriptor(RawState) ->
    Base = #{type => binary_to_atom(maps:get(<<"type">>, RawState), utf8)},
    add_optional_field(partner, <<"partner">>, RawState,
    add_optional_field(labels, <<"valid_labels">>, RawState,
    add_optional_field(transitions, <<"transitions">>, RawState,
    add_optional_field(shapes, <<"payload_shapes">>, RawState,
    add_optional_field(mork, <<"mork_mapped">>, RawState,
    add_optional_field(timeout, <<"timeout">>, RawState,
    add_optional_field(subprotocol, <<"subprotocol">>, RawState,
    add_optional_field(role_mapping, <<"role_mapping">>, RawState,
    add_optional_field(return_state, <<"return_state">>, RawState, Base))))))))).

add_optional_field(Key, JsonKey, RawState, Acc) ->
    case maps:find(JsonKey, RawState) of
        {ok, Value} -> maps:put(Key, convert_field(Key, Value), Acc);
        error -> Acc
    end.

convert_field(partner, V) when is_binary(V) -> binary_to_atom(V, utf8);
convert_field(labels, V) when is_list(V) -> 
    maps:from_list([{binary_to_atom(L, utf8), true} || L <- V]);
convert_field(transitions, V) when is_map(V) ->
    maps:fold(
        fun(K, StateId, Acc) ->
            maps:put(binary_to_atom(K, utf8), StateId, Acc)
        end, #{}, V);
convert_field(shapes, V) when is_map(V) ->
    maps:fold(
        fun(K, ShapePath, Acc) ->
            maps:put(binary_to_atom(K, utf8), ShapePath, Acc)
        end, #{}, V);
convert_field(mork, V) when is_map(V) ->
    maps:fold(
        fun(K, IsMork, Acc) ->
            maps:put(binary_to_atom(K, utf8), IsMork, Acc)
        end, #{}, V);
convert_field(timeout, #{<<"duration_ms">> := Duration, <<"target">> := Target}) ->
    #{duration_ms => Duration, target => Target};
convert_field(subprotocol, V) when is_binary(V) -> binary_to_atom(V, utf8);
convert_field(role_mapping, V) when is_map(V) ->
    maps:fold(
        fun(K, Part, Acc) ->
            maps:put(binary_to_atom(K, utf8), binary_to_atom(Part, utf8), Acc)
        end, #{}, V);
convert_field(return_state, V) when is_integer(V) -> V;
convert_field(_, V) -> V.

validate_table(#{protocol := _, version := _, participants := Participants}) 
  when is_map(Participants), map_size(Participants) > 0 ->
    maps:foreach(fun(_, PTable) -> validate_participant_table(PTable) end, Participants),
    ok;
validate_table(_) ->
    error({invalid_protocol_table, missing_required_fields}).

validate_participant_table(#{initial_state := InitState, states := States})
  when is_map(States), map_size(States) > 0 ->
    case maps:find(InitState, States) of
        {ok, _} -> ok;
        error -> error({invalid_participant_table, initial_state_not_found})
    end,
    maps:foreach(fun(_, State) -> validate_state_descriptor(State) end, States),
    ok;
validate_participant_table(_) ->
    error({invalid_participant_table, missing_required_fields}).

validate_state_descriptor(#{type := Type}) when Type =:= send; Type =:= recv; 
                                                 Type =:= 'end'; Type =:= call ->
    ok;
validate_state_descriptor(_) ->
    error({invalid_state_descriptor, invalid_or_missing_type}).