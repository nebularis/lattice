%%% spc_signal_service.erl
%%%
%%% Manages signal emission and subscription. When a subject completes
%%% a transition on a label that has signal configuration, the coordinator
%%% notifies this service, which emits the signal to the configured topic
%%% (via the AMQP bridge or internal pub/sub).
%%%
%%% Subscriptions work in reverse: this service subscribes to configured
%%% topics and delivers incoming signals to the coordinator as synthetic
%%% protocol messages.
%%%
%%% Correlation: Each signal carries correlation keys computed from the
%%% payload (using field paths defined in the config, which reference
%%% Mork concept paths). The correlation key resolution happens at the
%%% MORK ingress boundary — by the time the signal reaches this service,
%%% the keys are already resolved.

-module(spc_signal_service).
-behaviour(gen_server).

-export([
    start_link/0,
    emit_signals/5,
    setup_subscriptions/3,
    teardown_session/1
]).

-export([init/1, handle_call/3, handle_cast/2, handle_info/2, terminate/2]).

-record(state, {
    %% Active subscriptions: {SessionId, Topic} => ConsumerTag
    subscriptions :: #{term() => term()},
    %% AMQP channel reference (if using AMQP for signals)
    amqp_channel  :: pid() | undefined
}).

%% ------------------------------------------------------------------
%% API
%% ------------------------------------------------------------------

start_link() ->
    gen_server:start_link({local, ?MODULE}, ?MODULE, [], []).

%% Emit all configured signals for a transition.
%% Called by the coordinator after a successful state transition.
-spec emit_signals(atom(), atom(), atom(), atom(), map()) -> ok.
emit_signals(Protocol, SessionId, Participant, Label, Payload) ->
    case spc_extension_config:get_signal_config(Protocol, Participant, Label) of
        [] -> ok;
        Cfgs ->
            gen_server:cast(?MODULE, {emit, SessionId, Cfgs, Payload})
    end.

%% Set up subscriptions for a session. Called at session initialisation.
-spec setup_subscriptions(atom(), atom(), pid()) -> ok.
setup_subscriptions(Protocol, SessionId, CoordPid) ->
    gen_server:cast(?MODULE, {subscribe, Protocol, SessionId, CoordPid}).

%% Tear down subscriptions for a session. Called at session termination.
-spec teardown_session(atom()) -> ok.
teardown_session(SessionId) ->
    gen_server:cast(?MODULE, {teardown, SessionId}).

%% ------------------------------------------------------------------
%% gen_server callbacks
%% ------------------------------------------------------------------

init([]) ->
    {ok, #state{subscriptions = #{}, amqp_channel = undefined}}.

handle_call(_Request, _From, State) ->
    {reply, {error, unknown_call}, State}.

handle_cast({emit, SessionId, Cfgs, Payload}, State) ->
    lists:foreach(fun(Cfg) ->
        case Cfg#signal_cfg.direction of
            emit ->
                RoutingKey = render_routing_key(
                    Cfg#signal_cfg.routing_key_template,
                    SessionId,
                    Payload
                ),
                Message = #{
                    topic => Cfg#signal_cfg.topic,
                    routing_key => RoutingKey,
                    payload => Payload,
                    correlation => extract_correlation(
                        Cfg#signal_cfg.correlation_fields, Payload
                    ),
                    session_id => SessionId,
                    timestamp => erlang:system_time(millisecond)
                },
                do_emit(Cfg, Message, State);
            subscribe ->
                %% Subscribe signals are set up at session init, not per-transition
                ok
        end
    end, Cfgs),
    {noreply, State};

handle_cast({subscribe, Protocol, SessionId, CoordPid}, State) ->
    %% Find all subscribe-direction signals across all participants/labels
    %% This is a scan over the extension config. In production, the config
    %% would include a pre-indexed list of subscriptions per protocol.
    %% For now, we rely on the coordinator passing the subscription list.
    %% TODO: Index subscriptions at config load time.
    State1 = State,
    {noreply, State1};

handle_cast({teardown, SessionId}, State) ->
    %% Cancel all subscriptions for this session
    {ToRemove, ToKeep} = maps:fold(fun(Key = {SId, _}, Tag, {Remove, Keep}) ->
        case SId of
            SessionId -> {[{Key, Tag} | Remove], Keep};
            _ -> {Remove, Keep#{Key => Tag}}
        end
    end, {[], #{}}, State#state.subscriptions),
    %% Cancel AMQP consumers if applicable
    lists:foreach(fun({_Key, Tag}) ->
        case State#state.amqp_channel of
            undefined -> ok;
            Chan -> spc_amqp_bridge:cancel_consumer(Chan, Tag)
        end
    end, ToRemove),
    {noreply, State#state{subscriptions = ToKeep}};

handle_cast(_, State) ->
    {noreply, State}.

handle_info({signal_received, Topic, RoutingKey, Payload, Correlation}, State) ->
    %% A subscribed signal has arrived. Find the session and deliver
    %% to the coordinator.
    %% Correlation resolution maps the signal to the correct session.
    case resolve_session(Correlation, State) of
        {ok, CoordPid, Participant, Label} ->
            CoordPid ! {signal_deliver, Participant, Label, Payload};
        {error, _Reason} ->
            %% Signal cannot be correlated. Log and discard.
            ok
    end,
    {noreply, State};

handle_info(_Info, State) ->
    {noreply, State}.

terminate(_Reason, _State) ->
    ok.

%% ------------------------------------------------------------------
%% Internal
%% ------------------------------------------------------------------

do_emit(Cfg, Message, _State) ->
    %% Route the signal based on exchange type.
    %% For AMQP-backed signals, publish to the configured exchange.
    %% For internal signals (same BEAM cluster), use pg (process groups).
    case Cfg#signal_cfg.exchange_type of
        direct ->
            spc_amqp_bridge:publish(
                maps:get(topic, Message),
                maps:get(routing_key, Message),
                maps:get(payload, Message)
            );
        topic ->
            spc_amqp_bridge:publish(
                maps:get(topic, Message),
                maps:get(routing_key, Message),
                maps:get(payload, Message)
            );
        fanout ->
            spc_amqp_bridge:publish(
                maps:get(topic, Message),
                <<>>,
                maps:get(payload, Message)
            );
        headers ->
            Headers = maps:get(correlation, Message),
            spc_amqp_bridge:publish_with_headers(
                maps:get(topic, Message),
                maps:get(payload, Message),
                Headers
            )
    end.

render_routing_key(Template, SessionId, Payload) ->
    %% Replace {session_id}, {role}, {label} etc in the template.
    %% The template is a binary like <<"session.{role}.{label}">>
    S1 = binary:replace(Template, <<"{session_id}">>,
                         atom_to_binary(SessionId)),
    S2 = binary:replace(S1, <<"{role}">>,
                         maps:get(participant, Payload, <<>>)),
    binary:replace(S2, <<"{label}">>,
                    maps:get(label, Payload, <<>>)).

extract_correlation(Fields, Payload) ->
    maps:from_list([
        {Field, maps:get(Field, Payload, undefined)}
        || Field <- Fields
    ]).

resolve_session(_Correlation, _State) ->
    %% TODO: Use correlation keys to look up the session coordinator.
    %% This requires a correlation index maintained by the session supervisor
    %% or a dedicated correlation registry.
    {error, not_implemented}.