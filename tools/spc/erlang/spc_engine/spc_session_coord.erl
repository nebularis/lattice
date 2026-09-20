%%%-------------------------------------------------------------------
%%% @doc SPC Session Coordinator
%%%
%%% Manages message routing between subjects within a session.
%%% Maintains the message queue (the multiset μ from SPC configuration)
%%% and delivers messages to receiving subjects when they are ready.
%%%
%%% The coordinator also handles:
%%% - Subject registration and lifecycle tracking
%%% - Subsession initiation for nested protocol calls
%%% - Session completion detection
%%%
%%% @end
%%%-------------------------------------------------------------------
-module(spc_session_coord).

-behaviour(gen_server).

%% Editor's Note: Missing Features:
%% The architecture describes timeout, retry, and error handler annotations from EXT ontologies,
%% that are attached to state machine table entries. The coordinator has no mechanism to forward 
%% these or to enforce timeout-based escalation at the session level. This is arguably the subject's
%% responsibility (via gen_statem:state_timeout), but session-level timeouts would need coordinator involvement.


%% API
-export([
    start_link/3,
    register_subject/3,
    enqueue_message/5,
    get_session_status/1,
    stop/1
]).

%% gen_server callbacks
-export([
    init/1,
    handle_call/3,
    handle_cast/2,
    handle_info/2,
    terminate/2,
    code_change/3
]).

-include_lib("kernel/include/logger.hrl").

-record(state, {
    session_id      :: binary(),
    protocol_name   :: atom(),
    subjects = #{}  :: #{atom() => pid()},       %% participant_id => pid
    pending = []    :: [pending_message()],      %% messages awaiting delivery
    terminated = [] :: [atom()],                 %% participants that have ended
    parent          :: pid() | undefined,        %% parent session for nested calls
    caller          :: pid() | undefined         %% subject that initiated this subsession
}).

-type pending_message() :: {
    From :: atom(),
    To :: atom(),
    Label :: atom(),
    Payload :: binary() | atom(),
    Timestamp :: integer()
}.

%%====================================================================
%% API
%%====================================================================

%% @doc Start the session coordinator.
-spec start_link(binary(), atom(), pid() | undefined) -> gen_server:start_ret().
start_link(SessionId, ProtocolName, Parent) ->
    gen_server:start_link(?MODULE, {SessionId, ProtocolName, Parent}, []).

%% @doc Register a subject with the coordinator.
-spec register_subject(pid(), atom(), pid()) -> ok.
register_subject(Coordinator, ParticipantId, SubjectPid) ->
    gen_server:call(Coordinator, {register_subject, ParticipantId, SubjectPid}).

%% @doc Enqueue a message for delivery.
-spec enqueue_message(pid(), atom(), atom(), atom(), term()) -> ok.
enqueue_message(Coordinator, From, To, Label, Payload) ->
    gen_server:cast(Coordinator, {enqueue, From, To, Label, Payload}).

%% @doc Get the current status of the session.
-spec get_session_status(pid()) -> {ok, map()}.
get_session_status(Coordinator) ->
    gen_server:call(Coordinator, get_status).

%% @doc Stop the coordinator gracefully.
-spec stop(pid()) -> ok.
stop(Coordinator) ->
    gen_server:stop(Coordinator).

%%====================================================================
%% gen_server callbacks
%%====================================================================

init({SessionId, ProtocolName, Parent}) ->
    ?LOG_INFO(#{
        event => session_coordinator_started,
        session => SessionId,
        protocol => ProtocolName,
        parent => Parent
    }),
    {ok, #state{
        session_id = SessionId,
        protocol_name = ProtocolName,
        parent = Parent
    }}.

handle_call({register_subject, ParticipantId, SubjectPid}, _From, State) ->
    #state{subjects = Subjects, session_id = SessionId} = State,

    %% Monitor the subject so we know when it terminates
    erlang:monitor(process, SubjectPid),

    NewSubjects = maps:put(ParticipantId, SubjectPid, Subjects),
    NewState = State#state{subjects = NewSubjects},

    ?LOG_DEBUG(#{
        event => subject_registered,
        session => SessionId,
        participant => ParticipantId,
        pid => SubjectPid
    }),

    %% Try to deliver any pending messages for this subject
    NewState2 = attempt_pending_deliveries(NewState),

    {reply, ok, NewState2};

handle_call(get_status, _From, State) ->
    #state{
        session_id = SessionId,
        protocol_name = ProtocolName,
        subjects = Subjects,
        pending = Pending,
        terminated = Terminated
    } = State,

    Status = #{
        session_id => SessionId,
        protocol => ProtocolName,
        active_subjects => maps:keys(Subjects),
        terminated_subjects => Terminated,
        pending_messages => length(Pending),
        is_complete => is_session_complete(State)
    },
    {reply, {ok, Status}, State};

handle_call(_Request, _From, State) ->
    {reply, {error, unknown_request}, State}.

%% Editor's note: where is the 'morked' flag!? NB: it is missing in 'subject' too...

handle_cast({enqueue, From, To, Label, Payload}, State) ->
    #state{session_id = SessionId, pending = Pending} = State,

    Message = {From, To, Label, Payload, erlang:system_time(millisecond)},

    ?LOG_DEBUG(#{
        event => message_enqueued,
        session => SessionId,
        from => From,
        to => To,
        label => Label
    }),

    %% Editor's note: this is wrong, it prepends the message which reverses the ordering...
    %% Probably the LLM chose this because appending is far less efficient, however the 
    %% idiomatic approach would be `pending = queue:new() :: queue:queue(pending_message())'

    NewState = State#state{pending = [Message | Pending]},
    NewState2 = attempt_pending_deliveries(NewState),
    {noreply, NewState2};

%% Editor's note: where is ext routing!? We should have:
%% handle_info({route, Partner, Label, PayloadIRI}, State) ->
%%     %% Dispatch to egress layer (Elixir bridge, RabbitMQ, etc.)
%%     spc_egress:dispatch(State#state.session_id, Partner, Label, PayloadIRI),
%%     {noreply, State};

handle_cast(_Msg, State) ->
    {noreply, State}.

%% Handle messages from subject processes
handle_info({enqueue, From, To, Label, Payload}, State) ->
    %% Same as the cast version - subjects send this directly
    handle_cast({enqueue, From, To, Label, Payload}, State);

handle_info({subject_terminated, ParticipantId, _Pid}, State) ->
    #state{
        session_id = SessionId,
        subjects = Subjects,
        terminated = Terminated
    } = State,

    ?LOG_INFO(#{
        event => subject_terminated_notification,
        session => SessionId,
        participant => ParticipantId
    }),

    NewSubjects = maps:remove(ParticipantId, Subjects),
    NewTerminated = [ParticipantId | Terminated],
    NewState = State#state{subjects = NewSubjects, terminated = NewTerminated},

    %% Check if session is complete
    case is_session_complete(NewState) of
        true ->
            handle_session_complete(NewState);
        false ->
            {noreply, NewState}
    end;

handle_info({initiate_subsession, SubProtocol, RoleMapping, CallerPid}, State) ->
    #state{session_id = SessionId} = State,

    ?LOG_INFO(#{
        event => initiating_subsession,
        session => SessionId,
        subprotocol => SubProtocol,
        role_mapping => RoleMapping,
        caller => CallerPid
    }),

    %% Create a new subsession
    SubSessionId = generate_subsession_id(SessionId, SubProtocol),

    case spc_session_sup:start_session(SubSessionId, SubProtocol, self()) of
        {ok, SubCoordinator} ->
            %% Editor's note: I am not sure we can skip monitoring here (despite the sup)! 

            %% Map roles from parent session to subsession
            maps:foreach(
                fun(SubRole, ParentParticipant) ->
                    case maps:find(ParentParticipant, State#state.subjects) of
                        {ok, SubjectPid} ->
                            %% Reuse existing subject for the role
                            register_subject(SubCoordinator, SubRole, SubjectPid);
                        error ->
                            %% Need to start a new subject for this role
                            ok
                    end
                end,
                RoleMapping
            ),

            %% Track this subsession
            NewState = State#state{caller = CallerPid},
            {noreply, NewState};

        {error, Reason} ->
            ?LOG_ERROR(#{
                event => subsession_start_failed,
                session => SessionId,
                subprotocol => SubProtocol,
                reason => Reason
            }),
            {noreply, State}
    end;

handle_info({'DOWN', _Ref, process, Pid, Reason}, State) ->
    #state{session_id = SessionId, subjects = Subjects} = State,

    %% Find which participant this was
    case find_participant_by_pid(Pid, Subjects) of
        {ok, ParticipantId} ->
            ?LOG_WARNING(#{
                event => subject_crashed,
                session => SessionId,
                participant => ParticipantId,
                pid => Pid,
                reason => Reason
            }),
            %% Let the supervisor handle restart
            NewSubjects = maps:remove(ParticipantId, Subjects),
            {noreply, State#state{subjects = NewSubjects}};
        error ->
            {noreply, State}
    end;

handle_info(_Info, State) ->
    {noreply, State}.

terminate(Reason, #state{session_id = SessionId}) ->
    ?LOG_INFO(#{
        event => session_coordinator_terminated,
        session => SessionId,
        reason => Reason
    }),
    ok.

code_change(_OldVsn, State, _Extra) ->
    {ok, State}.

%%====================================================================
%% Internal functions
%%====================================================================

%% @private Attempt to deliver any pending messages to their recipients.
attempt_pending_deliveries(#state{pending = []} = State) ->
    State;
attempt_pending_deliveries(#state{pending = Pending, subjects = Subjects} = State) ->
    {Delivered, Remaining} = lists:partition(
        fun({_From, To, _Label, _Payload, _Ts}) ->
            maps:is_key(To, Subjects)
        end,
        Pending
    ),

    %% Deliver messages where recipient is registered
    lists:foreach(
        fun({From, To, Label, Payload, _Ts}) ->
            case maps:find(To, Subjects) of
                {ok, Pid} ->
                    spc_subject:deliver_message(Pid, From, Label, Payload);
                error ->
                    ok  % Should not happen given the partition above
            end
        end,
        Delivered
    ),

    State#state{pending = Remaining}.

%% @private Check if all subjects have terminated.
is_session_complete(#state{subjects = Subjects, protocol_name = ProtocolName}) ->
    case spc_config:get_protocol_table(ProtocolName) of
        undefined ->
            false;
        ProtocolTable ->
            AllParticipants = spc_config:all_participants(ProtocolTable),
            
            %% Editor's Note: This conflates "all subjects terminated" with "all subjects deregistered." 
            %% A subject that crashes and is removed from the map (in the DOWN handler) would count toward 
            %% completion here, even though a supervisor may have restarted it.
            %% I would change this to:
            %% AllParticipants = spc_config:all_participants(ProtocolTable),
            %% lists:sort(Terminated) =:= lists:sort(AllParticipants)            

            %% Session is complete when no subjects remain active
            maps:size(Subjects) =:= 0 andalso length(AllParticipants) > 0
    end.

%% @private Handle session completion.
handle_session_complete(#state{session_id = SessionId, parent = Parent, caller = Caller} = State) ->
    ?LOG_INFO(#{
        event => session_complete,
        session => SessionId
    }),

    %% If this is a subsession, notify the parent
    case {Parent, Caller} of
        {undefined, _} ->
            %% Top-level session - just stop
            {stop, normal, State};
        {ParentPid, CallerPid} when is_pid(ParentPid), is_pid(CallerPid) ->
            %% Subsession - notify caller
            spc_subject:subsession_complete(CallerPid, self()),
            {stop, normal, State};
        _ ->
            {stop, normal, State}
    end.

%% @private Find a participant ID by their process PID.
find_participant_by_pid(Pid, Subjects) ->
    Result = maps:fold(
        fun(ParticipantId, SubjectPid, Acc) ->
            case SubjectPid of
                Pid -> {ok, ParticipantId};
                _ -> Acc
            end
        end,
        error,
        Subjects
    ),
    Result.

%% @private Generate a unique subsession ID.
generate_subsession_id(ParentSessionId, SubProtocol) ->
    Unique = integer_to_binary(erlang:unique_integer([positive])),
    <<ParentSessionId/binary, ":", (atom_to_binary(SubProtocol, utf8))/binary, ":", Unique/binary>>.