%%% spc_timer_service.erl
%%%
%%% Manages timers for all active sessions. Each timer is an Erlang timer
%%% reference associated with a (SessionId, Participant, StateId) triple.
%%%
%%% Design: The timer service is a gen_server that maintains a registry of
%%% active timers. When a subject process enters a state with timer config,
%%% the coordinator calls set_timer/5. When the subject leaves that state
%%% (any transition), the coordinator calls cancel_timer/3. When a timer
%%% fires, this service sends a message to the coordinator, which delivers
%%% it to the subject as a timeout event.
%%%
%%% Interrupting timers: the timeout message is delivered as a normal
%%% protocol event ({deliver, system, TimeoutLabel, #{}}) that the
%%% gen_statem processes via its standard transition logic.
%%%
%%% Non-interrupting timers: the timeout message is delivered as a side
%%% notification to the coordinator, which may log it or trigger an
%%% external action but does NOT force a state transition on the subject.
%%%
%%% Cron-based timers use erlang:send_after for the next occurrence,
%%% recomputed after each firing. The cron expression is parsed at config
%%% load time by the Python pipeline; we receive the next-fire-ms directly,
%%% or compute it from a simple cron subset.

-module(spc_timer_service).
-behaviour(gen_server).

-export([
    start_link/0,
    set_timers_for_state/5,
    cancel_timers/3,
    cancel_all_for_session/1
]).

-export([init/1, handle_call/3, handle_cast/2, handle_info/2, terminate/2]).

-include("spc_extension_config.hrl").

-record(state, {
    %% Key: {SessionId, Participant, StateId}
    %% Value: [TimerRef]
    active :: #{term() => [reference()]}
}).

-record(timer_entry, {
    session_id    :: atom(),
    participant   :: atom(),
    state_id      :: non_neg_integer(),
    coordinator   :: pid(),
    cfg           :: #timer_cfg{}
}).

%% ------------------------------------------------------------------
%% API
%% ------------------------------------------------------------------

start_link() ->
    gen_server:start_link({local, ?MODULE}, ?MODULE, [], []).

%% Called by the coordinator when a subject enters a new state.
%% Looks up timer config for that state and sets all configured timers.
-spec set_timers_for_state(
    atom(),              % SessionId
    atom(),              % Participant
    non_neg_integer(),   % StateId
    atom(),              % Protocol
    pid()                % CoordinatorPid
) -> ok.
set_timers_for_state(SessionId, Participant, StateId, Protocol, CoordPid) ->
    case spc_extension_config:get_timer_config(Protocol, Participant, StateId) of
        [] -> ok;
        Cfgs ->
            gen_server:cast(?MODULE, {set_timers, SessionId, Participant,
                                      StateId, CoordPid, Cfgs})
    end.

%% Called by the coordinator when a subject leaves a state (any transition).
-spec cancel_timers(atom(), atom(), non_neg_integer()) -> ok.
cancel_timers(SessionId, Participant, StateId) ->
    gen_server:cast(?MODULE, {cancel, SessionId, Participant, StateId}).

%% Called when a session terminates — clean up all timers.
-spec cancel_all_for_session(atom()) -> ok.
cancel_all_for_session(SessionId) ->
    gen_server:cast(?MODULE, {cancel_session, SessionId}).

%% ------------------------------------------------------------------
%% gen_server callbacks
%% ------------------------------------------------------------------

init([]) ->
    {ok, #state{active = #{}}}.

handle_call(_Request, _From, State) ->
    {reply, {error, unknown_call}, State}.

handle_cast({set_timers, SessionId, Participant, StateId, CoordPid, Cfgs}, State) ->
    %% First cancel any existing timers for this (session, participant, state)
    Key = {SessionId, Participant, StateId},
    State1 = do_cancel(Key, State),
    %% Set new timers
    Refs = lists:map(fun(Cfg) ->
        DurationMs = resolve_duration(Cfg),
        Entry = #timer_entry{
            session_id = SessionId,
            participant = Participant,
            state_id = StateId,
            coordinator = CoordPid,
            cfg = Cfg
        },
        TRef = erlang:send_after(DurationMs, self(), {timer_fired, TRef0 = make_ref(), Entry}),
        %% We use make_ref for the message tag and erlang timer ref for cancellation
        %% Simplify: use the erlang timer ref directly
        erlang:send_after(DurationMs, self(), {timer_fired, Entry})
    end, Cfgs),
    Active = (State1#state.active)#{Key => Refs},
    {noreply, State1#state{active = Active}};

handle_cast({cancel, SessionId, Participant, StateId}, State) ->
    Key = {SessionId, Participant, StateId},
    {noreply, do_cancel(Key, State)};

handle_cast({cancel_session, SessionId}, State) ->
    %% Cancel all timers for this session
    Active = maps:filter(fun({SId, _, _}, _) -> SId =/= SessionId end,
                          State#state.active),
    %% Cancel the removed refs
    Removed = maps:filter(fun({SId, _, _}, _) -> SId =:= SessionId end,
                           State#state.active),
    maps:foreach(fun(_, Refs) ->
        [erlang:cancel_timer(R) || R <- Refs]
    end, Removed),
    {noreply, State#state{active = Active}};

handle_cast(_, State) ->
    {noreply, State}.

handle_info({timer_fired, #timer_entry{} = Entry}, State) ->
    #timer_entry{
        session_id = SessionId,
        participant = Participant,
        state_id = StateId,
        coordinator = CoordPid,
        cfg = Cfg
    } = Entry,
    Key = {SessionId, Participant, StateId},
    %% Only fire if the timer is still active (subject hasn't moved on)
    case maps:is_key(Key, State#state.active) of
        false ->
            %% Subject already transitioned; timer is stale. Ignore.
            {noreply, State};
        true ->
            case Cfg#timer_cfg.type of
                interrupting ->
                    %% Deliver timeout as a protocol message to the coordinator,
                    %% which delivers it to the subject as a state transition.
                    CoordPid ! {timer_timeout, Participant,
                                Cfg#timer_cfg.timeout_label,
                                Cfg#timer_cfg.target_state,
                                #{source => timer, session => SessionId}},
                    %% Remove the timer entry
                    {noreply, do_cancel(Key, State)};
                non_interrupting ->
                    %% Side notification only — log it, maybe notify external.
                    %% Do NOT force a state transition.
                    CoordPid ! {timer_notification, Participant,
                                Cfg#timer_cfg.timeout_label,
                                #{source => timer, session => SessionId,
                                  type => non_interrupting}},
                    %% For cron timers, reschedule
                    case Cfg#timer_cfg.cron of
                        undefined ->
                            {noreply, do_cancel(Key, State)};
                        _CronExpr ->
                            %% Reschedule next occurrence
                            NextMs = resolve_duration(Cfg),
                            NewRef = erlang:send_after(NextMs, self(),
                                        {timer_fired, Entry}),
                            Active = (State#state.active)#{Key => [NewRef]},
                            {noreply, State#state{active = Active}}
                    end
            end
    end;

handle_info(_Info, State) ->
    {noreply, State}.

terminate(_Reason, State) ->
    %% Cancel all outstanding timers
    maps:foreach(fun(_, Refs) ->
        [erlang:cancel_timer(R) || R <- Refs]
    end, State#state.active),
    ok.

%% ------------------------------------------------------------------
%% Internal
%% ------------------------------------------------------------------

do_cancel(Key, #state{active = Active} = State) ->
    case maps:take(Key, Active) of
        {Refs, Active1} ->
            [erlang:cancel_timer(R) || R <- Refs],
            State#state{active = Active1};
        error ->
            State
    end.

resolve_duration(#timer_cfg{duration_ms = Ms}) when is_integer(Ms), Ms > 0 ->
    Ms;
resolve_duration(#timer_cfg{datetime = DT}) when is_binary(DT) ->
    %% Parse ISO 8601 datetime, compute ms until then
    Now = erlang:system_time(millisecond),
    Target = iso8601_to_epoch_ms(DT),
    max(0, Target - Now);
resolve_duration(#timer_cfg{cron = Cron}) when is_binary(Cron) ->
    %% Compute next cron occurrence in ms from now.
    %% For the POC, we support a simple subset: the Python pipeline
    %% can pre-compute "next_fire_ms" relative to session start.
    %% Full cron parsing would use a library.
    next_cron_ms(Cron);
resolve_duration(_) ->
    %% Fallback: 1 hour
    3600000.

iso8601_to_epoch_ms(DT) ->
    %% Minimal ISO 8601 parser. Production would use a library.
    %% Format: "2025-01-15T10:30:00Z"
    case calendar:rfc3339_to_system_time(binary_to_list(DT),
                                          [{unit, millisecond}]) of
        Ms when is_integer(Ms) -> Ms;
        _ -> erlang:system_time(millisecond) + 3600000
    end.

next_cron_ms(_CronExpr) ->
    %% Stub: return 1 hour. Real implementation would parse cron
    %% or the Python pipeline would pre-compute intervals.
    3600000.