%%% spc_job_service.erl
%%%
%%% Manages retry logic for outbound actions. When a subject emits a
%%% send that has a job/retry configuration, the coordinator delegates
%%% delivery to this service rather than sending directly. The service
%%% wraps the delivery with retry/backoff logic.
%%%
%%% Architecture: The job service is a gen_server that spawns a
%%% supervised task per delivery attempt. Each task is a short-lived
%%% process that attempts delivery (via the connector subsystem or
%%% the coordinator's routing). On failure, the service schedules a
%%% retry after the computed backoff delay.
%%%
%%% The job service does NOT mutate subject state. If retries exhaust,
%%% it notifies the coordinator, which triggers error handling via the
%%% error service. The subject process remains in its current state
%%% throughout the retry sequence.

-module(spc_job_service).
-behaviour(gen_server).

-export([
    start_link/0,
    submit/6,
    cancel_job/1
]).

-export([init/1, handle_call/3, handle_cast/2, handle_info/2, terminate/2]).

-record(state, {
    %% Active jobs: JobRef => job_state
    jobs :: #{reference() => job_state()}
}).

-record(job_state, {
    ref            :: reference(),
    session_id     :: atom(),
    participant    :: atom(),
    label          :: atom(),
    payload        :: term(),
    coordinator    :: pid(),
    cfg            :: term(),  % #job_cfg{}
    attempt        :: non_neg_integer(),
    timer_ref      :: reference() | undefined,
    deliver_fun    :: fun()     % fun/0 that attempts delivery, returns ok | {error, Reason}
}).

%% ------------------------------------------------------------------
%% API
%% ------------------------------------------------------------------

start_link() ->
    gen_server:start_link({local, ?MODULE}, ?MODULE, [], []).

%% Submit a delivery job with retry semantics.
%% DeliverFun is a fun/0 that attempts the delivery and returns
%% ok | {error, Reason}.
-spec submit(atom(), atom(), atom(), term(), pid(), fun()) -> reference().
submit(SessionId, Participant, Label, Payload, CoordPid, DeliverFun) ->
    Ref = make_ref(),
    gen_server:cast(?MODULE, {submit, Ref, SessionId, Participant,
                              Label, Payload, CoordPid, DeliverFun}),
    Ref.

-spec cancel_job(reference()) -> ok.
cancel_job(Ref) ->
    gen_server:cast(?MODULE, {cancel, Ref}).

%% ------------------------------------------------------------------
%% gen_server callbacks
%% ------------------------------------------------------------------

init([]) ->
    {ok, #state{jobs = #{}}}.

handle_call(_Request, _From, State) ->
    {reply, {error, unknown_call}, State}.

handle_cast({submit, Ref, SessionId, Participant, Label, Payload, CoordPid, DeliverFun}, State) ->
    Protocol = get_protocol_for_session(SessionId),
    Cfg = spc_extension_config:get_job_config(Protocol, Participant, Label),
    Job = #job_state{
        ref = Ref,
        session_id = SessionId,
        participant = Participant,
        label = Label,
        payload = Payload,
        coordinator = CoordPid,
        cfg = Cfg,
        attempt = 0,
        timer_ref = undefined,
        deliver_fun = DeliverFun
    },
    Job1 = attempt_delivery(Job),
    Jobs = (State#state.jobs)#{Ref => Job1},
    {noreply, State#state{jobs = Jobs}};

handle_cast({cancel, Ref}, State) ->
    case maps:take(Ref, State#state.jobs) of
        {Job, Jobs} ->
            cancel_timer(Job),
            {noreply, State#state{jobs = Jobs}};
        error ->
            {noreply, State}
    end;

handle_cast(_, State) ->
    {noreply, State}.

handle_info({retry, Ref}, State) ->
    case maps:get(Ref, State#state.jobs, undefined) of
        undefined ->
            {noreply, State};
        Job ->
            Job1 = attempt_delivery(Job),
            Jobs = (State#state.jobs)#{Ref => Job1},
            {noreply, State#state{jobs = Jobs}}
    end;

handle_info({delivery_result, Ref, ok}, State) ->
    case maps:take(Ref, State#state.jobs) of
        {Job, Jobs} ->
            %% Success. Notify coordinator.
            Job#job_state.coordinator !
                {job_completed, Job#job_state.participant,
                 Job#job_state.label, ok},
            {noreply, State#state{jobs = Jobs}};
        error ->
            {noreply, State}
    end;

handle_info({delivery_result, Ref, {error, Reason}}, State) ->
    case maps:get(Ref, State#state.jobs, undefined) of
        undefined ->
            {noreply, State};
        Job ->
            MaxAttempts = case Job#job_state.cfg of
                undefined -> 1;
                C -> C#job_cfg.max_attempts
            end,
            case Job#job_state.attempt >= MaxAttempts of
                true ->
                    %% Exhausted. Notify coordinator with error.
                    OnExhausted = case Job#job_state.cfg of
                        undefined -> {error_label, retry_exhausted};
                        C2 -> C2#job_cfg.on_exhausted
                    end,
                    Job#job_state.coordinator !
                        {job_exhausted, Job#job_state.participant,
                         Job#job_state.label, Reason, OnExhausted},
                    Jobs = maps:remove(Ref, State#state.jobs),
                    {noreply, State#state{jobs = Jobs}};
                false ->
                    %% Schedule retry
                    Delay = compute_backoff(Job),
                    TRef = erlang:send_after(Delay, self(), {retry, Ref}),
                    Job1 = Job#job_state{timer_ref = TRef},
                    Jobs = (State#state.jobs)#{Ref => Job1},
                    {noreply, State#state{jobs = Jobs}}
            end
    end;

handle_info(_Info, State) ->
    {noreply, State}.

terminate(_Reason, State) ->
    maps:foreach(fun(_, Job) -> cancel_timer(Job) end, State#state.jobs),
    ok.

%% ------------------------------------------------------------------
%% Internal
%% ------------------------------------------------------------------

attempt_delivery(#job_state{ref = Ref, deliver_fun = Fun} = Job) ->
    Self = self(),
    %% Spawn a short-lived process for the delivery attempt.
    %% This isolates the job service from delivery failures (crashes, timeouts).
    spawn_link(fun() ->
        Result = try Fun() of
            ok -> ok;
            {ok, _} -> ok;
            {error, _} = Err -> Err;
            Other -> {error, {unexpected_result, Other}}
        catch
            Class:Reason:Stack ->
                {error, {Class, Reason, Stack}}
        end,
        Self ! {delivery_result, Ref, Result}
    end),
    Job#job_state{attempt = Job#job_state.attempt + 1}.

compute_backoff(#job_state{cfg = undefined}) ->
    1000;
compute_backoff(#job_state{attempt = Attempt, cfg = Cfg}) ->
    #job_cfg{
        backoff_strategy = Strategy,
        base_delay_ms = Base,
        multiplier = Mult,
        jitter_pct = Jitter,
        max_delay_ms = MaxDelay
    } = Cfg,
    Raw = case Strategy of
        none -> Base;
        constant -> Base;
        exponential ->
            %% Base * Mult^(Attempt - 1)
            round(Base * math:pow(Mult, Attempt - 1));
        jitter ->
            ExpDelay = round(Base * math:pow(Mult, Attempt - 1)),
            JitterRange = round(ExpDelay * Jitter),
            ExpDelay + rand:uniform(max(1, JitterRange * 2)) - JitterRange
    end,
    min(Raw, MaxDelay).

cancel_timer(#job_state{timer_ref = undefined}) -> ok;
cancel_timer(#job_state{timer_ref = TRef}) ->
    erlang:cancel_timer(TRef),
    ok.

get_protocol_for_session(SessionId) ->
    %% Look up the protocol name for a session. In production this comes
    %% from the session coordinator or a registry.
    %% For now, the session coordinator stores this in the process dictionary
    %% or we query the coordinator.
    case persistent_term:get({spc_session_protocol, SessionId}, undefined) of
        undefined -> default_protocol;
        Protocol -> Protocol
    end.