%%%-------------------------------------------------------------------
%%% @doc SPC Subject Process
%%%
%%% A gen_statem implementing one participant's behaviour in one
%%% session. All protocol-specific logic comes from the state
%%% machine table loaded via spc_config. This module is entirely
%%% generic — the same code runs brokers, carriers, operations
%%% staff, AI agents, and any other subject in any protocol.
%%%
%%% The gen_statem operates in handle_event_function mode with
%%% a single logical state: `running`. Protocol-level state is
%%% tracked in the callback data via spc_config:session_data().
%%%
%%% == Message Protocol ==
%%%
%%% Inbound (cast):
%%%   {send_request, Label, Payload}
%%%     Application requests this subject send a message.
%%%     Valid only when the current protocol state is `send`.
%%%
%%%   {message_available, FromParticipant, Label, Payload}
%%%     The session coordinator delivers a message to this subject.
%%%     Valid only when the current protocol state is `recv` and
%%%     the label matches a valid branch.
%%%
%%%   {subsession_complete, SubCoordinatorPid}
%%%     A nested subsession (from a `call` state) has completed.
%%%     The subject advances to the call's return state.
%%%
%%% Inbound (info):
%%%   {timeout, TRef, {state_timeout, StateId}}
%%%     A state timeout has fired. If the subject is still in
%%%     the timed state, it takes the timeout transition.
%%%
%%% Outbound (via session coordinator):
%%%   {enqueue, FromParticipant, ToParticipant, Label, Payload}
%%%     Sent to the session coordinator when a message is emitted.
%%%
%%%   {initiate_subsession, SubProtocol, RoleMapping, CallerPid}
%%%     Sent to the session coordinator to start a nested session.
%%%
%%% @end
%%%-------------------------------------------------------------------
-module(spc_subject).

-behaviour(gen_statem).

%% API
-export([
    start_link/4,
    start_link/5,
    send_request/3,
    deliver_message/4,
    subsession_complete/2,
    get_state/1,
    get_session_info/1
]).

%% gen_statem callbacks
-export([
    init/1,
    callback_mode/0,
    handle_event/4,
    terminate/3,
    code_change/4
]).

-include_lib("kernel/include/logger.hrl").

-record(init_args, {
    session_id     :: binary(),
    protocol_name  :: atom(),
    participant_id :: atom(),
    coordinator    :: pid() | undefined,
    opts           :: map()
}).

-type payload_iri() :: binary().  %% IRI reference to an A-Box individual in Fuseki

%%====================================================================
%% API
%%====================================================================

%% @doc Start a subject process.
%%
%% SessionId:     unique binary identifier for this session
%% ProtocolName:  atom, must match a loaded protocol in persistent_term
%% ParticipantId: atom, must be a participant in the protocol
%% Coordinator:   pid of the session coordinator process
-spec start_link(binary(), atom(), atom(), pid()) ->
    gen_statem:start_ret().
start_link(SessionId, ProtocolName, ParticipantId, Coordinator) ->
    start_link(SessionId, ProtocolName, ParticipantId, Coordinator, #{}).

-spec start_link(binary(), atom(), atom(), pid() | undefined, map()) ->
    gen_statem:start_ret().
start_link(SessionId, ProtocolName, ParticipantId, Coordinator, Opts) ->
    Args = #init_args{
        session_id = SessionId,
        protocol_name = ProtocolName,
        participant_id = ParticipantId,
        coordinator = Coordinator,
        opts = Opts
    },
    gen_statem:start_link(?MODULE, Args, []).

%% @doc Request this subject to send a message.
%% Called by the application layer (UI, API handler, AI agent).
-spec send_request(pid(), atom(), payload_iri()) -> ok.
send_request(SubjectPid, Label, Payload) ->
    gen_statem:cast(SubjectPid, {send_request, Label, Payload}).

%% @doc Request this subject to synchronously send a message.
%% Called by the application layer (UI, API handler, AI agent).
-spec send_request_sync(pid(), atom(), payload_iri()) -> ok.
send_request_sync(SubjectPid, Label, Payload) ->
    gen_statem:call(SubjectPid, {send_request, Label, Payload}).

%% @doc Deliver an incoming message to this subject.
%% Called by the session coordinator.
-spec deliver_message(pid(), atom(), atom(), payload_iri()) -> ok.
deliver_message(SubjectPid, FromParticipant, Label, Payload) ->
    gen_statem:cast(SubjectPid, {message_available, FromParticipant, Label, Payload}).

%% @doc Notify this subject that a subsession has completed.
%% Called by the session coordinator when a nested protocol finishes.
-spec subsession_complete(pid(), pid()) -> ok.
subsession_complete(SubjectPid, SubCoordinatorPid) ->
    gen_statem:cast(SubjectPid, {subsession_complete, SubCoordinatorPid}).

%% @doc Get the current protocol state of this subject.
-spec get_state(pid()) -> {ok, non_neg_integer()} | {error, term()}.
get_state(SubjectPid) ->
    gen_statem:call(SubjectPid, get_state).

%% @doc Get session information for this subject.
-spec get_session_info(pid()) -> {ok, map()} | {error, term()}.
get_session_info(SubjectPid) ->
    gen_statem:call(SubjectPid, get_session_info).

%%====================================================================
%% gen_statem Callbacks
%%====================================================================

callback_mode() ->
    [handle_event_function, state_enter].

init(#init_args{session_id = SessionId,
                protocol_name = ProtocolName,
                participant_id = ParticipantId,
                coordinator = Coordinator,
                opts = _Opts}) ->
    %% Load the protocol table (O(1), no copy — persistent_term)
    case spc_config:get_protocol_table(ProtocolName) of
        undefined ->
            {stop, {unknown_protocol, ProtocolName}};
        ProtocolTable ->
            %% Look up this participant's state table
            case spc_config:lookup_participant(ParticipantId, ProtocolTable) of
                {ok, PTable} ->
                    Data = spc_config:new_session_data(
                        SessionId, ProtocolName, ParticipantId, PTable, Coordinator
                    ),

                    ?LOG_INFO(#{
                        event => subject_started,
                        session => SessionId,
                        protocol => ProtocolName,
                        participant => ParticipantId,
                        initial_state => spc_config:current_state_id(Data)
                    }),

                    {ok, running, Data};

                error ->
                    {stop, {unknown_participant, ParticipantId, ProtocolName}}
            end
    end.

%%--------------------------------------------------------------------
%% State enter callback — handles timeout scheduling
%%--------------------------------------------------------------------
handle_event(enter, _OldState, running, Data) ->
    %% On entering the running state (which includes every protocol
    %% state transition, since we stay in `running` and track protocol
    %% state in the data), check if the new protocol state has a timeout.
    StateId = spc_config:current_state_id(Data),
    PTable = spc_config:participant_table(Data),

    case spc_config:lookup_state(StateId, PTable) of
        {ok, Descriptor} ->
            case spc_config:state_type(Descriptor) of
                'end' ->
                    %% We've reached the end state - notify coordinator and stop
                    handle_termination(Data);
                call ->
                    %% We're in a call state - initiate subsession
                    handle_call_state(Descriptor, Data);
                _ ->
                    %% Normal send/recv state - handle timeout if present
                    handle_state_timeout(Descriptor, StateId, Data)
            end;
        error ->
            %% State not found in table — this is a fatal error
            {stop, {invalid_state, StateId}, Data}
    end;

%%--------------------------------------------------------------------
%% Synchronous calls for introspection
%%--------------------------------------------------------------------
handle_event({call, From}, get_state, running, Data) ->
    StateId = spc_config:current_state_id(Data),
    {keep_state, Data, [{reply, From, {ok, StateId}}]};

handle_event({call, From}, get_session_info, running, Data) ->
    Info = #{
        session_id => spc_config:session_id(Data),
        protocol => spc_config:protocol_name(Data),
        participant => spc_config:participant_id(Data),
        current_state => spc_config:current_state_id(Data),
        call_stack_depth => length(spc_config:call_stack(Data))
    },
    {keep_state, Data, [{reply, From, {ok, Info}}]};

%%--------------------------------------------------------------------
%% Send request from the application layer
%%--------------------------------------------------------------------
handle_event(cast, {send_request, Label, Payload}, running, Data) ->
    StateId = spc_config:current_state_id(Data),
    PTable = spc_config:participant_table(Data),

    case spc_config:lookup_state(StateId, PTable) of
        {ok, Descriptor} ->
            handle_send(Label, Payload, StateId, Descriptor, Data);
        error ->
            protocol_violation(invalid_state_lookup, #{
                state_id => StateId
            }, Data)
    end;

%%--------------------------------------------------------------------
%% Message delivery from the session coordinator
%%--------------------------------------------------------------------
handle_event(cast, {message_available, FromParticipant, Label, Payload}, running, Data) ->
    StateId = spc_config:current_state_id(Data),
    PTable = spc_config:participant_table(Data),

    case spc_config:lookup_state(StateId, PTable) of
        {ok, Descriptor} ->
            handle_receive(FromParticipant, Label, Payload, StateId, Descriptor, Data);
        error ->
            protocol_violation(invalid_state_lookup, #{
                state_id => StateId
            }, Data)
    end;

%%--------------------------------------------------------------------
%% Subsession completion notification
%%--------------------------------------------------------------------
handle_event(cast, {subsession_complete, SubCoordPid}, running, Data) ->
    handle_subsession_complete(SubCoordPid, Data);

%%--------------------------------------------------------------------
%% Coordinator registration (for subjects started before coordinator)
%%--------------------------------------------------------------------
handle_event(cast, {set_coordinator, Coordinator}, running, Data) ->
    NewData = spc_config:set_coordinator(Coordinator, Data),
    {keep_state, NewData};

%%--------------------------------------------------------------------
%% Timeout firing
%%--------------------------------------------------------------------
handle_event(info, {timeout, _TRef, {state_timeout, TimedStateId}}, running, Data) ->
    handle_timeout(TimedStateId, Data);

%%--------------------------------------------------------------------
%% Catch-all for unexpected events
%%--------------------------------------------------------------------
handle_event(EventType, EventContent, StateName, Data) ->
    ?LOG_WARNING(#{
        event => unexpected_event,
        event_type => EventType,
        event_content => EventContent,
        state_name => StateName,
        session => spc_config:session_id(Data),
        participant => spc_config:participant_id(Data)
    }),
    {keep_state, Data}.

terminate(Reason, _StateName, Data) ->
    ?LOG_INFO(#{
        event => subject_terminated,
        reason => Reason,
        session => spc_config:session_id(Data),
        participant => spc_config:participant_id(Data),
        final_state => spc_config:current_state_id(Data)
    }),
    ok.

code_change(_OldVsn, StateName, Data, _Extra) ->
    {ok, StateName, Data}.

%%====================================================================
%% Internal: State Enter Helpers
%%====================================================================

handle_state_timeout(Descriptor, StateId, Data) ->
    case spc_config:state_timeout(Descriptor) of
        undefined ->
            {keep_state, Data};
        #{duration_ms := Ms} ->
            %% Schedule a timeout. The {state_timeout, StateId}
            %% tag lets us verify the timeout is still relevant
            %% when it fires (the subject may have advanced past
            %% this state by then).
            _TRef = erlang:start_timer(Ms, self(), {state_timeout, StateId}),
            %% editor's note [Tim Watson]: In principle, stale timers accumulate in the process's timer wheel.
            %% For long-running sessions with many timed states, this could produce a stream of ignored timer messages.
            %% The guard discards them cheaply, but storing the TRef and cancelling on state advance would be cleaner.
            {keep_state, Data}
    end.

handle_termination(Data) ->
    %% Notify the coordinator that this subject has completed
    case spc_config:session_coordinator(Data) of
        undefined ->
            ok;
        Coordinator ->
            Coordinator ! {subject_terminated, spc_config:participant_id(Data), self()}
    end,

    ?LOG_INFO(#{
        event => subject_completed,
        session => spc_config:session_id(Data),
        participant => spc_config:participant_id(Data),
        final_state => spc_config:current_state_id(Data)
    }),

    {stop, normal, Data}.

handle_call_state(Descriptor, Data) ->
    SubProtocol = spc_config:call_subprotocol(Descriptor),
    RoleMapping = spc_config:call_role_mapping(Descriptor),
    ReturnState = spc_config:call_return_state(Descriptor),

    case spc_config:session_coordinator(Data) of
        undefined ->
            ?LOG_ERROR(#{
                event => call_without_coordinator,
                session => spc_config:session_id(Data),
                participant => spc_config:participant_id(Data),
                subprotocol => SubProtocol
            }),
            {stop, {error, no_coordinator_for_call}, Data};
        Coordinator ->
            ?LOG_DEBUG(#{
                event => initiating_subsession,
                session => spc_config:session_id(Data),
                participant => spc_config:participant_id(Data),
                subprotocol => SubProtocol,
                role_mapping => RoleMapping,
                return_state => ReturnState
            }),

            %% Ask coordinator to start the subsession
            Coordinator ! {initiate_subsession, SubProtocol, RoleMapping, self()},

            %% Push the return state onto our call stack.
            %% We use a placeholder pid for the sub-coordinator;
            %% it will be updated when the coordinator confirms.
            NewData = spc_config:push_call(ReturnState, undefined, Data),

            %% Editor's note: this is wrong, it should be {next_state, suspended, NewData}
            %% TODO: we will need to add event handlers for {send_request, _, _} that {keep_state, Data}
            %% and for {message_available, _, _, _} that evaluates to {keep_state, Data, [postpone]} 
            %% and we will need to ensure that {subsession_complete, SubCoordPid} resolves to {next_state, running, NewData}
            
            %% for now we will keep the LLM's code though, until we can verify it...
            {keep_state, NewData}
    end.

%%====================================================================
%% Internal: Send Handling
%%====================================================================

handle_send(Label, Payload, StateId, Descriptor, Data) ->
    %% Step 1: Verify we are in a send state
    case spc_config:state_type(Descriptor) of
        send ->
            handle_send_in_send_state(Label, Payload, StateId, Descriptor, Data);
        'end' ->
            protocol_violation(send_in_end_state, #{
                state_id => StateId,
                label => Label
            }, Data);
        Other ->
            protocol_violation(send_in_wrong_state, #{
                state_id => StateId,
                state_type => Other,
                label => Label
            }, Data)
    end.

handle_send_in_send_state(Label, Payload, StateId, Descriptor, Data) ->
    %% Step 2: Verify label is valid for this state
    case spc_config:is_valid_label(Label, Descriptor) of
        true ->
            handle_send_valid_label(Label, Payload, StateId, Descriptor, Data);
        false ->
            protocol_violation(invalid_send_label, #{
                state_id => StateId,
                label => Label,
                valid_labels => maps:keys(spc_config:state_labels(Descriptor))
            }, Data)
    end.

handle_send_valid_label(Label, Payload, StateId, Descriptor, Data) ->
    %% Step 3: Payload validation (only for non-Mork-mapped channels)
    case spc_config:is_mork_mapped(Label, Descriptor) of
        true ->
            %% Mork-mapped: payload is well-typed by construction
            execute_send(Label, Payload, StateId, Descriptor, Data);
        false ->
            %% Not Mork-mapped: validate against SHACL shape
            case validate_payload(Label, Payload, Descriptor) of
                ok ->
                    execute_send(Label, Payload, StateId, Descriptor, Data);
                {error, Violations} ->
                    protocol_violation(payload_validation_failed, #{
                        state_id => StateId,
                        label => Label,
                        violations => Violations
                    }, Data)
            end
    end.

execute_send(Label, Payload, StateId, Descriptor, Data) ->
    %% Step 4: Determine next state
    {ok, NextStateId} = spc_config:next_state(Label, Descriptor),
    Partner = spc_config:state_partner(Descriptor),

    SessionId = spc_config:session_id(Data),
    ParticipantId = spc_config:participant_id(Data),
    Coordinator = spc_config:session_coordinator(Data),

    %% Step 5: Enqueue the message with the session coordinator
    case Coordinator of
        undefined ->
            ?LOG_WARNING(#{
                event => send_without_coordinator,
                session => SessionId,
                participant => ParticipantId,
                label => Label
            });
        _ ->
            %% Editor's note #1: this should probably use a more descriptive atom, like 'route'
            %% Editor's note #2: this is a tight coupling on the message protocol with the coordinator,
            %% it should be via controlled API, eg: 
            %% spc_session_coord:enqueue_message(Coordinator, ParticipantId, Partner, Label, Payload)
            Coordinator ! {enqueue, ParticipantId, Partner, Label, Payload}
    end,

    %% Step 6: Advance our protocol state
    NewData = spc_config:advance_state(NextStateId, Data),

    ?LOG_DEBUG(#{
        event => send_completed,
        session => SessionId,
        participant => ParticipantId,
        label => Label,
        partner => Partner,
        state_from => StateId,
        state_to => NextStateId
    }),

    %% Editor's note: The use of {repeat_state, NewData} rather than {keep_state, NewData} here
    %% is rather clever of the LLM (code gen): it uses gen_statem's state_enter callback as a trampoline
    %% for protocol state transitions while keeping the gen_statem state fixed at running.
    %%
    %% This pattern is not described in the architecture, but it's the correct mechanism for implementing 
    %% a single-state design, because repeat_state triggers a state_enter event even though the
    %% gen_statem state (running) hasn't changed. 
    %%
    %% This is essential: the state_enter handler checks the NEW protocol state (in Data) for
    %% end-state termination, call-state subsession initiation, and timeout scheduling. Without 
    %% repeat_state, advancing the protocol state would not trigger those checks.

    %% Trigger state_enter to handle end/call states or timeout scheduling
    {repeat_state, NewData}.

%%====================================================================
%% Internal: Receive Handling
%%====================================================================

handle_receive(FromParticipant, Label, Payload, StateId, Descriptor, Data) ->
    %% Step 1: Verify we are in a receive state
    case spc_config:state_type(Descriptor) of
        recv ->
            handle_receive_in_recv_state(
                FromParticipant, Label, Payload, StateId, Descriptor, Data
            );
        _ ->
            %% Not in receive state. The message arrived before we're
            %% ready for it. This is not a protocol violation — it's
            %% a timing issue. We defer the message by postponing it.
            %% gen_statem will redeliver it after the next state change.
            {keep_state, Data, [postpone]}
    end.

handle_receive_in_recv_state(FromParticipant, Label, Payload, StateId, Descriptor, Data) ->
    %% Step 2: Verify the sender matches our expected partner
    ExpectedPartner = spc_config:state_partner(Descriptor),
    case FromParticipant of
        ExpectedPartner ->
            handle_receive_from_partner(
                FromParticipant, Label, Payload, StateId, Descriptor, Data
            );
        _ ->
            %% Message from unexpected sender. Might be from a
            %% different protocol state's partner arriving early.
            %% Postpone and let it be redelivered later.
            {keep_state, Data, [postpone]}
    end.

handle_receive_from_partner(_FromParticipant, Label, Payload, StateId, Descriptor, Data) ->
    %% Step 3: Verify label is valid
    case spc_config:is_valid_label(Label, Descriptor) of
        true ->
            execute_receive(Label, Payload, StateId, Descriptor, Data);
        false ->
            protocol_violation(invalid_receive_label, #{
                state_id => StateId,
                label => Label,
                valid_labels => maps:keys(spc_config:state_labels(Descriptor))
            }, Data)
    end.

execute_receive(Label, Payload, StateId, Descriptor, Data) ->
    %% Step 4: Determine next state
    {ok, NextStateId} = spc_config:next_state(Label, Descriptor),
    Partner = spc_config:state_partner(Descriptor),

    SessionId = spc_config:session_id(Data),
    ParticipantId = spc_config:participant_id(Data),

    %% Step 5: Deliver payload to the application handler
    %% The handler is a callback that processes the business content
    %% of the message (e.g., storing a quote, updating a submission).
    %% It runs synchronously — if it fails, the subject process crashes
    %% and the supervision tree recovers.
    ok = dispatch_to_handler(Label, Payload, Data),

    %% Step 6: Advance state
    NewData = spc_config:advance_state(NextStateId, Data),

    ?LOG_DEBUG(#{
        event => receive_completed,
        session => SessionId,
        participant => ParticipantId,
        label => Label,
        partner => Partner,
        state_from => StateId,
        state_to => NextStateId
    }),

    %% Trigger state_enter to handle end/call states or timeout scheduling
    {repeat_state, NewData}.

%%====================================================================
%% Internal: Subsession Completion
%%====================================================================

handle_subsession_complete(SubCoordPid, Data) ->
    case spc_config:pop_call(Data) of
        {ok, ReturnState, _SubCoord, NewData0} ->
            ?LOG_DEBUG(#{
                event => subsession_completed,
                session => spc_config:session_id(Data),
                participant => spc_config:participant_id(Data),
                return_state => ReturnState,
                sub_coordinator => SubCoordPid
            }),

            NewData = spc_config:advance_state(ReturnState, NewData0),

            %% Trigger state_enter for the return state
            {repeat_state, NewData};

        empty ->
            ?LOG_WARNING(#{
                event => unexpected_subsession_complete,
                session => spc_config:session_id(Data),
                participant => spc_config:participant_id(Data),
                sub_coordinator => SubCoordPid
            }),
            {keep_state, Data}
    end.

%%====================================================================
%% Internal: Timeout Handling
%%====================================================================

handle_timeout(TimedStateId, Data) ->
    CurrentStateId = spc_config:current_state_id(Data),

    case TimedStateId =:= CurrentStateId of
        false ->
            %% The timeout fired for a state we have already left.
            %% This is expected — the timer was set when we entered
            %% the state, but we advanced before it fired. Ignore.
            {keep_state, Data};
        true ->
            %% We are still in the timed state. Take the timeout transition.
            PTable = spc_config:participant_table(Data),
            case spc_config:lookup_state(CurrentStateId, PTable) of
                {ok, Descriptor} ->
                    case spc_config:state_timeout(Descriptor) of
                        #{target := TargetStateId} ->
                            ?LOG_INFO(#{
                                event => state_timeout_fired,
                                session => spc_config:session_id(Data),
                                participant => spc_config:participant_id(Data),
                                state_from => CurrentStateId,
                                state_to => TargetStateId
                            }),

                            NewData = spc_config:advance_state(TargetStateId, Data),
                            {repeat_state, NewData};

                        undefined ->
                            %% Timeout fired but state has no timeout configured.
                            %% Should not happen. Ignore.
                            {keep_state, Data}
                    end;
                error ->
                    protocol_violation(timeout_invalid_state, #{
                        state_id => CurrentStateId
                    }, Data)
            end
    end.

%%====================================================================
%% Internal: Payload Validation
%%====================================================================

%% @private Validate a payload against its SHACL shape.
%% This is called only for non-Mork-mapped channels.
%% For Mork-mapped channels, the payload is well-typed by construction
%% and this function is never invoked.
validate_payload(Label, Payload, Descriptor) ->
    case spc_config:shape_for_label(Label, Descriptor) of
        {ok, ShapeRef} ->
            %% Delegate to the SHACL validator service.
            %% This is the one place where "runtime reasoning" occurs,
            %% and only for unmapped channels.
            spc_shacl:validate(Payload, ShapeRef);
        error ->
            %% No shape defined — accept the payload.
            %% This should not happen in a correctly extracted table.
            ?LOG_WARNING(#{
                event => missing_shape_ref,
                label => Label
            }),
            ok
    end.

%%====================================================================
%% Internal: Application Dispatch
%%====================================================================

%% @private Dispatch a received payload to the application-level handler.
%%
%% The handler is resolved by protocol + label. It is a function that
%% processes the business content of the message: storing a quote in
%% the triple store, updating a submission status, notifying a UI, etc.
%%
%% If no handler is registered, the payload is logged and accepted.
%% This allows protocol execution to proceed even when handlers have
%% not yet been implemented (useful during development).
dispatch_to_handler(Label, Payload, Data) ->
    ProtocolName = spc_config:protocol_name(Data),
    ParticipantId = spc_config:participant_id(Data),

    %% Editor's note: The module assumes a handler registry where application-level callbacks are registered
    %% per (protocol, participant, label) triple. This is a reasonable design but is not specified in the architecture. 
    %% The architecture describes the receive flow thus: "notifies the external subscriber (human or agent) asynchronously".
    %% 
    %% The synchronous dispatch in execute_receive means a slow handler blocks the subject process,
    %% and a crashing handler crashes the subject. the architecture's recommendation is that this is non-blocking.
    %% The synchronous approach is arguably more correct for maintaining ordering guarantees, so this needs some analysis.

    case spc_handler_registry:lookup(ProtocolName, ParticipantId, Label) of
        {ok, HandlerFun} ->
            %% The handler receives the payload and the session context.
            %% It returns ok or {error, Reason}.
            %% On error, we let the subject process crash — the
            %% supervision tree handles recovery.
            Context = #{
                session_id => spc_config:session_id(Data),
                protocol => ProtocolName,
                participant => ParticipantId,
                label => Label,
                current_state => spc_config:current_state_id(Data)
            },
            case HandlerFun(Payload, Context) of
                ok -> ok;
                {error, Reason} ->
                    error({handler_failed, Label, Reason})
            end;
        error ->
            ?LOG_DEBUG(#{
                event => no_handler_registered,
                protocol => ProtocolName,
                participant => ParticipantId,
                label => Label
            }),
            ok
    end.

%%====================================================================
%% Internal: Protocol Violation Handling
%%====================================================================

%% @private Handle a protocol violation.
%%
%% A protocol violation indicates a bug in the design-time pipeline
%% (incorrect state machine extraction), a Mork mapping error (producing
%% incorrectly typed data), or a session coordinator routing error
%% (delivering a message to the wrong subject).
%%
%% We do NOT attempt local recovery. We log the violation for
%% post-mortem analysis and crash the process. The supervision tree
%% will restart us, and if the violation recurs, the supervisor
%% escalates.
protocol_violation(Type, Details, Data) ->
    SessionId = spc_config:session_id(Data),
    ParticipantId = spc_config:participant_id(Data),
    StateId = spc_config:current_state_id(Data),

    ViolationEvent = #{
        type        => protocol_violation,
        violation   => Type,
        details     => Details,
        session     => SessionId,
        participant => ParticipantId,
        state_id    => StateId,
        timestamp   => erlang:system_time(millisecond)
    },

    ?LOG_ERROR(ViolationEvent),

    {stop, {protocol_violation, Type, Details}, Data}.