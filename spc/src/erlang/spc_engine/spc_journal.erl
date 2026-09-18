%%%-------------------------------------------------------------------
%%% @doc SPC Event Journal
%%%
%%% Append-only event journal for session state transitions.
%%% Provides durability, audit trail, and recovery capabilities.
%%%
%%% Events are written synchronously before state advances.
%%% The journal is the source of truth; process state is a cache.
%%% @end
%%%-------------------------------------------------------------------
-module(spc_journal).

-behaviour(gen_server).

-export([
    start_link/1,
    log_event/6,
    log_send/6,
    log_receive/6,
    log_timeout/4,
    log_call/5,
    log_return/4,
    log_termination/3,
    replay_session/2,
    get_session_events/2,
    close/1
]).

-export([init/1, handle_call/3, handle_cast/2, handle_info/2, 
         terminate/2, code_change/3]).

-record(state, {
    storage_backend :: module(),
    backend_state   :: term(),
    hash_chain      :: binary()
}).

-record(event, {
    session_id      :: binary(),
    participant_id  :: atom(),
    event_type      :: send | recv | timeout | call | return | termination,
    label           :: atom() | undefined,
    state_before    :: non_neg_integer(),
    state_after     :: non_neg_integer(),
    payload_ref     :: binary() | undefined,
    timestamp       :: integer(),
    prev_hash       :: binary(),
    hash            :: binary()
}).

%%====================================================================
%% API
%%====================================================================

start_link(Opts) ->
    gen_server:start_link(?MODULE, Opts, []).

-spec log_event(pid(), binary(), atom(), atom(), 
                non_neg_integer(), non_neg_integer()) -> ok.
log_event(Journal, SessionId, ParticipantId, EventType, StateBefore, StateAfter) ->
    gen_server:call(Journal, {log, SessionId, ParticipantId, EventType, 
                              undefined, StateBefore, StateAfter, undefined}).

-spec log_send(pid(), binary(), atom(), atom(), 
               non_neg_integer(), non_neg_integer()) -> ok.
log_send(Journal, SessionId, ParticipantId, Label, StateBefore, StateAfter) ->
    gen_server:call(Journal, {log, SessionId, ParticipantId, send,
                              Label, StateBefore, StateAfter, undefined}).

-spec log_receive(pid(), binary(), atom(), atom(),
                  non_neg_integer(), non_neg_integer()) -> ok.
log_receive(Journal, SessionId, ParticipantId, Label, StateBefore, StateAfter) ->
    gen_server:call(Journal, {log, SessionId, ParticipantId, recv,
                              Label, StateBefore, StateAfter, undefined}).

-spec log_timeout(pid(), binary(), atom(), non_neg_integer()) -> ok.
log_timeout(Journal, SessionId, ParticipantId, StateAfter) ->
    gen_server:call(Journal, {log, SessionId, ParticipantId, timeout,
                              undefined, StateAfter, StateAfter, undefined}).

-spec log_call(pid(), binary(), atom(), atom(), non_neg_integer()) -> ok.
log_call(Journal, SessionId, ParticipantId, Subprotocol, StateAfter) ->
    gen_server:call(Journal, {log, SessionId, ParticipantId, call,
                              Subprotocol, StateAfter, StateAfter, undefined}).

-spec log_return(pid(), binary(), atom(), non_neg_integer()) -> ok.
log_return(Journal, SessionId, ParticipantId, StateAfter) ->
    gen_server:call(Journal, {log, SessionId, ParticipantId, return,
                              undefined, StateAfter, StateAfter, undefined}).

-spec log_termination(pid(), binary(), atom()) -> ok.
log_termination(Journal, SessionId, ParticipantId) ->
    gen_server:call(Journal, {log, SessionId, ParticipantId, termination,
                              undefined, -1, -1, undefined}).

-spec replay_session(pid(), binary()) -> {ok, [#event{}]} | {error, term()}.
replay_session(Journal, SessionId) ->
    gen_server:call(Journal, {replay, SessionId}).

-spec get_session_events(pid(), binary()) -> {ok, [#event{}]} | {error, term()}.
get_session_events(Journal, SessionId) ->
    gen_server:call(Journal, {get_events, SessionId}).

-spec close(pid()) -> ok.
close(Journal) ->
    gen_server:stop(Journal).

%%====================================================================
%% gen_server callbacks
%%====================================================================

init(Opts) ->
    Backend = proplists:get_value(backend, Opts, spc_journal_ets),
    BackendOpts = proplists:get_value(backend_opts, Opts, []),
    {ok, BackendState} = Backend:init(BackendOpts),
    GenesisHash = crypto:hash(sha256, <<"SPC_JOURNAL_GENESIS">>),
    {ok, #state{
        storage_backend = Backend,
        backend_state = BackendState,
        hash_chain = GenesisHash
    }}.

handle_call({log, SessionId, ParticipantId, EventType, Label, 
             StateBefore, StateAfter, PayloadRef}, _From, State) ->
    #state{storage_backend = Backend, 
           backend_state = BackendState,
           hash_chain = PrevHash} = State,
    
    Timestamp = erlang:system_time(microsecond),
    EventData = term_to_binary({SessionId, ParticipantId, EventType, Label,
                                StateBefore, StateAfter, PayloadRef, Timestamp, PrevHash}),
    Hash = crypto:hash(sha256, EventData),
    
    Event = #event{
        session_id = SessionId,
        participant_id = ParticipantId,
        event_type = EventType,
        label = Label,
        state_before = StateBefore,
        state_after = StateAfter,
        payload_ref = PayloadRef,
        timestamp = Timestamp,
        prev_hash = PrevHash,
        hash = Hash
    },
    
    {ok, NewBackendState} = Backend:append(Event, BackendState),
    {reply, ok, State#state{backend_state = NewBackendState, hash_chain = Hash}};

handle_call({replay, SessionId}, _From, State) ->
    #state{storage_backend = Backend, backend_state = BackendState} = State,
    Result = Backend:get_by_session(SessionId, BackendState),
    {reply, Result, State};

handle_call({get_events, SessionId}, _From, State) ->
    #state{storage_backend = Backend, backend_state = BackendState} = State,
    Result = Backend:get_by_session(SessionId, BackendState),
    {reply, Result, State}.

handle_cast(_Msg, State) ->
    {noreply, State}.

handle_info(_Info, State) ->
    {noreply, State}.

terminate(_Reason, #state{storage_backend = Backend, backend_state = BackendState}) ->
    Backend:close(BackendState),
    ok.

code_change(_OldVsn, State, _Extra) ->
    {ok, State}.