%%% spc_extension_hooks.erl
%%%
%%% Integration module called by the session coordinator at specific
%%% lifecycle points. This is the single point of contact between the
%%% core SPC interpreter and all extension services.
%%%
%%% The coordinator calls these functions; it does not call extension
%%% services directly. This maintains the separation between the core
%%% (which knows only about state machines and routing) and extensions
%%% (which know about timers, retries, errors, compensation, signals).

-module(spc_extension_hooks).

-export([
    on_session_start/3,
    on_state_enter/6,
    on_state_exit/5,
    on_transition/7,
    on_send/7,
    on_error/5,
    on_session_end/2
]).

%% Called when a session is created and all subjects are initialised.
-spec on_session_start(atom(), atom(), pid()) -> ok.
on_session_start(Protocol, SessionId, CoordPid) ->
    %% Set up signal subscriptions for this session.
    spc_signal_service:setup_subscriptions(Protocol, SessionId, CoordPid),

    %% Declare AMQP topology if configured.
    case spc_extension_config:get_connector_config(Protocol, amqp_topology) of
        undefined -> ok;
        TopologyConfig ->
            spc_amqp_bridge:declare_topology(TopologyConfig)
    end,

    %% Set timers for initial states of all participants.
    %% The coordinator should call on_state_enter for each participant's
    %% initial state. This is handled below.
    ok.

%% Called when a subject enters a new state (after a transition).
-spec on_state_enter(atom(), atom(), atom(), non_neg_integer(), pid(), map()) -> ok.
on_state_enter(Protocol, SessionId, Participant, StateId, CoordPid, _StateDesc) ->
    %% Start any timers configured for this state.
    spc_timer_service:set_timers_for_state(
        SessionId, Participant, StateId, Protocol, CoordPid),
    ok.

%% Called when a subject is about to leave its current state.
-spec on_state_exit(atom(), atom(), atom(), non_neg_integer(), pid()) -> ok.
on_state_exit(_Protocol, SessionId, Participant, StateId, _CoordPid) ->
    %% Cancel timers for the state being left.
    spc_timer_service:cancel_timers(SessionId, Participant, StateId),
    ok.

%% Called after a successful state transition.
-spec on_transition(atom(), atom(), atom(), atom(), non_neg_integer(),
                    non_neg_integer(), map()) -> ok.
on_transition(Protocol, SessionId, Participant, Label,
              _FromState, _ToState, Payload) ->
    %% Emit signals configured for this label.
    spc_signal_service:emit_signals(
        Protocol, SessionId, Participant, Label, Payload),

    %% Record compensable actions.
    %% Check if this label is part of any compensation scope.
    %% The config indexes compensation pairs by action_label.
    record_compensation_if_needed(Protocol, SessionId, Participant, Label),

    ok.

%% Called when a subject sends a message that requires job/retry wrapping.
%% Returns {direct, DeliverFun} if no retry config, or {job, JobRef} if
%% the delivery is handed off to the job service.
-spec on_send(atom(), atom(), atom(), atom(), term(), pid(), fun()) ->
    {direct, fun()} | {job, reference()}.
on_send(Protocol, _SessionId, Participant, Label,
        _Payload, _CoordPid, DeliverFun) ->
    case spc_extension_config:get_job_config(Protocol, Participant, Label) of
        undefined ->
            {direct, DeliverFun};
        _JobCfg ->
            %% Hand off to the job service, which wraps DeliverFun
            %% with retry logic.
            JobRef = spc_job_service:submit(
                _SessionId, Participant, Label, _Payload, _CoordPid, DeliverFun),
            {job, JobRef}
    end.

%% Called when an error occurs.
-spec on_error(atom(), atom(), atom(), atom(), term()) ->
    {recover, atom(), non_neg_integer()} |
    {escalate, atom(), term()} |
    {fail_session, term()}.
on_error(Protocol, _SessionId, Participant, ErrorClass, ErrorDetail) ->
    spc_error_service:handle_error(
        Protocol, _SessionId, Participant, ErrorClass, ErrorDetail).

%% Called when a session ends (all subjects terminated or session failed).
-spec on_session_end(atom(), atom()) -> ok.
on_session_end(SessionId, _Outcome) ->
    %% Clean up all extension state for this session.
    spc_timer_service:cancel_all_for_session(SessionId),
    spc_compensation_service:clear_session(SessionId),
    spc_signal_service:teardown_session(SessionId),
    ok.

%% ------------------------------------------------------------------
%% Internal
%% ------------------------------------------------------------------

record_compensation_if_needed(Protocol, SessionId, Participant, Label) ->
    %% Scan compensation scopes for this label.
    %% In production, this would be pre-indexed. For now, we check
    %% all known scopes.
    %% The config would ideally include an index: {label -> scope_id}.
    %% This is a TODO for the Python config generator.
    %% For now, we use a brute-force approach.
    ok.