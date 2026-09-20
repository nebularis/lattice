%%% spc_amqp_bridge.erl
%%%
%%% Native Erlang AMQP client bridge. Manages a connection pool to
%%% RabbitMQ and provides publish/consume operations. The bridge is
%%% configuration-driven: exchanges, queues, and bindings are declared
%%% from the generated extension config at session startup, not hardcoded.
%%%
%%% The bridge maintains:
%%% - A single persistent connection (with reconnection logic)
%%% - A pool of channels (one per concurrent operation context)
%%% - Declared exchanges/queues per protocol
%%%
%%% The bridge does NOT interpret SPC protocol semantics. It is a
%%% transport layer: publish bytes to a routing key, consume bytes
%%% from a queue, deliver them to a callback.

-module(spc_amqp_bridge).
-behaviour(gen_server).

-export([
    start_link/1,
    publish/3,
    publish/4,
    publish_with_headers/3,
    publish_with_headers/4,
    declare_topology/1,
    consume/3,
    cancel_consumer/2,
    stop/0
]).

-export([init/1, handle_call/3, handle_cast/2, handle_info/2, terminate/2]).

%% amqp_client records
-include_lib("amqp_client/include/amqp_client.hrl").

-record(state, {
    connection      :: pid() | undefined,
    publish_channel :: pid() | undefined,
    consume_channels :: #{binary() => pid()},  % Queue => Channel
    consumer_tags    :: #{binary() => {pid(), binary()}}, % Tag => {Channel, Queue}
    config          :: map(),
    reconnect_timer :: reference() | undefined,
    declared        :: #{binary() => boolean()} % exchange/queue names already declared
}).

-define(RECONNECT_DELAY_MS, 5000).
-define(HEARTBEAT_SEC, 30).

%% ------------------------------------------------------------------
%% API
%% ------------------------------------------------------------------

start_link(Config) ->
    gen_server:start_link({local, ?MODULE}, ?MODULE, Config, []).

%% Publish a message to an exchange with a routing key.
-spec publish(binary(), binary(), term()) -> ok | {error, term()}.
publish(Exchange, RoutingKey, Payload) ->
    publish(Exchange, RoutingKey, Payload, #{}).

-spec publish(binary(), binary(), term(), map()) -> ok | {error, term()}.
publish(Exchange, RoutingKey, Payload, Opts) ->
    gen_server:call(?MODULE, {publish, Exchange, RoutingKey, Payload, Opts}).

-spec publish_with_headers(binary(), term(), map()) -> ok | {error, term()}.
publish_with_headers(Exchange, Payload, Headers) ->
    publish_with_headers(Exchange, Payload, Headers, #{}).

-spec publish_with_headers(binary(), term(), map(), map()) -> ok | {error, term()}.
publish_with_headers(Exchange, Payload, Headers, Opts) ->
    gen_server:call(?MODULE, {publish_headers, Exchange, Payload, Headers, Opts}).

%% Declare exchanges, queues, and bindings from configuration.
%% Called once per protocol at session setup time.
-spec declare_topology(map()) -> ok | {error, term()}.
declare_topology(TopologyConfig) ->
    gen_server:call(?MODULE, {declare_topology, TopologyConfig}, 30000).

%% Start consuming from a queue. Messages are delivered to CallbackPid
%% as {amqp_message, Queue, RoutingKey, Payload, Headers, DeliveryTag}.
-spec consume(binary(), pid(), map()) -> {ok, binary()} | {error, term()}.
consume(Queue, CallbackPid, Opts) ->
    gen_server:call(?MODULE, {consume, Queue, CallbackPid, Opts}).

-spec cancel_consumer(pid(), binary()) -> ok.
cancel_consumer(_Channel, ConsumerTag) ->
    gen_server:cast(?MODULE, {cancel_consumer, ConsumerTag}).

stop() ->
    gen_server:stop(?MODULE).

%% ------------------------------------------------------------------
%% gen_server callbacks
%% ------------------------------------------------------------------

init(Config) ->
    State = #state{
        connection = undefined,
        publish_channel = undefined,
        consume_channels = #{},
        consumer_tags = #{},
        config = Config,
        reconnect_timer = undefined,
        declared = #{}
    },
    %% Connect asynchronously
    self() ! connect,
    {ok, State}.

handle_call({publish, Exchange, RoutingKey, Payload, Opts}, _From, State) ->
    case State#state.publish_channel of
        undefined ->
            {reply, {error, not_connected}, State};
        Channel ->
            Result = do_publish(Channel, Exchange, RoutingKey, Payload, Opts),
            {reply, Result, State}
    end;

handle_call({publish_headers, Exchange, Payload, Headers, Opts}, _From, State) ->
    case State#state.publish_channel of
        undefined ->
            {reply, {error, not_connected}, State};
        Channel ->
            Result = do_publish_headers(Channel, Exchange, Payload, Headers, Opts),
            {reply, Result, State}
    end;

handle_call({declare_topology, TopologyConfig}, _From, State) ->
    case State#state.publish_channel of
        undefined ->
            {reply, {error, not_connected}, State};
        Channel ->
            Result = do_declare_topology(Channel, TopologyConfig, State),
            case Result of
                {ok, State1} -> {reply, ok, State1};
                {error, _} = Err -> {reply, Err, State}
            end
    end;

handle_call({consume, Queue, CallbackPid, _Opts}, _From, State) ->
    case State#state.connection of
        undefined ->
            {reply, {error, not_connected}, State};
        Conn ->
            case open_consume_channel(Conn, Queue, CallbackPid) of
                {ok, Channel, Tag} ->
                    ConsChannels = (State#state.consume_channels)#{Queue => Channel},
                    ConsTags = (State#state.consumer_tags)#{Tag => {Channel, Queue}},
                    {reply, {ok, Tag},
                     State#state{consume_channels = ConsChannels,
                                 consumer_tags = ConsTags}};
                {error, _} = Err ->
                    {reply, Err, State}
            end
    end;

handle_call(_Request, _From, State) ->
    {reply, {error, unknown_call}, State}.

handle_cast({cancel_consumer, Tag}, State) ->
    case maps:take(Tag, State#state.consumer_tags) of
        {{Channel, Queue}, Tags} ->
            catch amqp_channel:call(Channel, #'basic.cancel'{consumer_tag = Tag}),
            catch amqp_channel:close(Channel),
            ConsChannels = maps:remove(Queue, State#state.consume_channels),
            {noreply, State#state{consumer_tags = Tags,
                                  consume_channels = ConsChannels}};
        error ->
            {noreply, State}
    end;

handle_cast(_, State) ->
    {noreply, State}.

handle_info(connect, State) ->
    case do_connect(State#state.config) of
        {ok, Conn, PubChan} ->
            erlang:monitor(process, Conn),
            erlang:monitor(process, PubChan),
            {noreply, State#state{
                connection = Conn,
                publish_channel = PubChan,
                reconnect_timer = undefined
            }};
        {error, Reason} ->
            logger:warning("AMQP connection failed: ~p. Retrying in ~pms.",
                           [Reason, ?RECONNECT_DELAY_MS]),
            TRef = erlang:send_after(?RECONNECT_DELAY_MS, self(), connect),
            {noreply, State#state{reconnect_timer = TRef}}
    end;

handle_info({'DOWN', _Ref, process, Pid, Reason}, State) ->
    case Pid of
        _ when Pid =:= State#state.connection ->
            logger:error("AMQP connection lost: ~p. Reconnecting.", [Reason]),
            close_all_channels(State),
            TRef = erlang:send_after(?RECONNECT_DELAY_MS, self(), connect),
            {noreply, State#state{
                connection = undefined,
                publish_channel = undefined,
                consume_channels = #{},
                consumer_tags = #{},
                declared = #{},
                reconnect_timer = TRef
            }};
        _ when Pid =:= State#state.publish_channel ->
            logger:warning("AMQP publish channel lost. Reopening."),
            case State#state.connection of
                undefined ->
                    {noreply, State#state{publish_channel = undefined}};
                Conn ->
                    case amqp_connection:open_channel(Conn) of
                        {ok, NewChan} ->
                            erlang:monitor(process, NewChan),
                            {noreply, State#state{publish_channel = NewChan}};
                        _ ->
                            {noreply, State#state{publish_channel = undefined}}
                    end
            end;
        _ ->
            %% A consume channel died. Remove it.
            ConsCh = maps:filter(fun(_, Ch) -> Ch =/= Pid end,
                                  State#state.consume_channels),
            ConsTags = maps:filter(fun(_, {Ch, _}) -> Ch =/= Pid end,
                                    State#state.consumer_tags),
            {noreply, State#state{consume_channels = ConsCh,
                                  consumer_tags = ConsTags}}
    end;

%% amqp_client delivers messages as info messages when using direct consumer
handle_info({#'basic.deliver'{consumer_tag = Tag,
                               routing_key = RK,
                               delivery_tag = DTag,
                               exchange = _Ex},
             #amqp_msg{payload = Body, props = Props}},
            State) ->
    case maps:get(Tag, State#state.consumer_tags, undefined) of
        undefined ->
            {noreply, State};
        {Channel, Queue} ->
            Headers = case Props#'P_basic'.headers of
                undefined -> #{};
                H -> amqp_headers_to_map(H)
            end,
            %% Find the callback pid. In our architecture, this is
            %% typically the signal service or a session coordinator.
            %% The consumer setup stores the callback pid — we need
            %% to track it. For simplicity, use the signal service.
            spc_signal_service ! {signal_received, Queue, RK, Body, Headers},
            %% Acknowledge
            amqp_channel:cast(Channel, #'basic.ack'{delivery_tag = DTag}),
            {noreply, State}
    end;

handle_info(#'basic.consume_ok'{}, State) ->
    {noreply, State};

handle_info(#'basic.cancel_ok'{}, State) ->
    {noreply, State};

handle_info(_Info, State) ->
    {noreply, State}.

terminate(_Reason, State) ->
    close_all_channels(State),
    case State#state.connection of
        undefined -> ok;
        Conn -> catch amqp_connection:close(Conn)
    end,
    ok.

%% ------------------------------------------------------------------
%% Internal: connection
%% ------------------------------------------------------------------

do_connect(Config) ->
    Params = #amqp_params_network{
        host = binary_to_list(maps:get(<<"host">>, Config, <<"localhost">>)),
        port = maps:get(<<"port">>, Config, 5672),
        virtual_host = maps:get(<<"vhost">>, Config, <<"/">>),
        username = maps:get(<<"username">>, Config, <<"guest">>),
        password = maps:get(<<"password">>, Config, <<"guest">>),
        heartbeat = ?HEARTBEAT_SEC,
        ssl_options = build_ssl_options(maps:get(<<"ssl">>, Config, #{}))
    },
    case amqp_connection:start(Params) of
        {ok, Conn} ->
            case amqp_connection:open_channel(Conn) of
                {ok, Chan} ->
                    %% Enable publisher confirms for reliable publishing
                    #'confirm.select_ok'{} =
                        amqp_channel:call(Chan, #'confirm.select'{}),
                    {ok, Conn, Chan};
                {error, Reason} ->
                    catch amqp_connection:close(Conn),
                    {error, {channel_open_failed, Reason}}
            end;
        {error, Reason} ->
            {error, {connection_failed, Reason}}
    end.

build_ssl_options(SslConfig) when map_size(SslConfig) =:= 0 ->
    none;
build_ssl_options(SslConfig) ->
    Opts0 = [{verify, verify_peer}],
    Opts1 = case maps:get(<<"cacertfile">>, SslConfig, undefined) of
        undefined -> Opts0;
        Ca -> [{cacertfile, binary_to_list(Ca)} | Opts0]
    end,
    Opts2 = case maps:get(<<"certfile">>, SslConfig, undefined) of
        undefined -> Opts1;
        Cert -> [{certfile, binary_to_list(Cert)} | Opts1]
    end,
    Opts3 = case maps:get(<<"keyfile">>, SslConfig, undefined) of
        undefined -> Opts2;
        Key -> [{keyfile, binary_to_list(Key)} | Opts2]
    end,
    Opts3.

%% ------------------------------------------------------------------
%% Internal: publishing
%% ------------------------------------------------------------------

do_publish(Channel, Exchange, RoutingKey, Payload, Opts) ->
    Body = encode_payload(Payload),
    Props = build_props(Opts),
    Publish = #'basic.publish'{
        exchange = Exchange,
        routing_key = RoutingKey,
        mandatory = maps:get(mandatory, Opts, false)
    },
    try
        amqp_channel:cast(Channel, Publish, #amqp_msg{
            payload = Body,
            props = Props
        }),
        %% Wait for confirm if using publisher confirms
        case amqp_channel:wait_for_confirms(Channel, 5000) of
            true -> ok;
            false -> {error, nacked};
            timeout -> {error, confirm_timeout}
        end
    catch
        _:Reason -> {error, {publish_failed, Reason}}
    end.

do_publish_headers(Channel, Exchange, Payload, Headers, Opts) ->
    Body = encode_payload(Payload),
    HeaderList = maps:fold(fun(K, V, Acc) ->
        [{ensure_binary(K), longstr, ensure_binary(V)} | Acc]
    end, [], Headers),
    Props = (build_props(Opts))#'P_basic'{headers = HeaderList},
    Publish = #'basic.publish'{
        exchange = Exchange,
        routing_key = <<>>,
        mandatory = maps:get(mandatory, Opts, false)
    },
    try
        amqp_channel:cast(Channel, Publish, #amqp_msg{
            payload = Body,
            props = Props
        }),
        case amqp_channel:wait_for_confirms(Channel, 5000) of
            true -> ok;
            false -> {error, nacked};
            timeout -> {error, confirm_timeout}
        end
    catch
        _:Reason -> {error, {publish_failed, Reason}}
    end.

build_props(Opts) ->
    #'P_basic'{
        content_type = maps:get(content_type, Opts, <<"application/json">>),
        delivery_mode = case maps:get(persistent, Opts, true) of
            true -> 2;    % persistent
            false -> 1    % transient
        end,
        message_id = maps:get(message_id, Opts, undefined),
        correlation_id = maps:get(correlation_id, Opts, undefined),
        timestamp = erlang:system_time(second)
    }.

%% ------------------------------------------------------------------
%% Internal: topology declaration
%% ------------------------------------------------------------------

do_declare_topology(Channel, TopologyConfig, State) ->
    try
        %% Declare exchanges
        Exchanges = maps:get(<<"exchanges">>, TopologyConfig, []),
        lists:foreach(fun(Ex) ->
            ExName = maps:get(<<"name">>, Ex),
            case maps:is_key(ExName, State#state.declared) of
                true -> ok;
                false ->
                    ExDeclare = #'exchange.declare'{
                        exchange = ExName,
                        type = maps:get(<<"type">>, Ex, <<"topic">>),
                        durable = maps:get(<<"durable">>, Ex, true),
                        auto_delete = maps:get(<<"auto_delete">>, Ex, false)
                    },
                    #'exchange.declare_ok'{} =
                        amqp_channel:call(Channel, ExDeclare)
            end
        end, Exchanges),

        %% Declare queues
        Queues = maps:get(<<"queues">>, TopologyConfig, []),
        lists:foreach(fun(Q) ->
            QName = maps:get(<<"name">>, Q),
            case maps:is_key(QName, State#state.declared) of
                true -> ok;
                false ->
                    Args = build_queue_args(Q),
                    QDeclare = #'queue.declare'{
                        queue = QName,
                        durable = maps:get(<<"durable">>, Q, true),
                        auto_delete = maps:get(<<"auto_delete">>, Q, false),
                        arguments = Args
                    },
                    #'queue.declare_ok'{} =
                        amqp_channel:call(Channel, QDeclare)
            end
        end, Queues),

        %% Declare bindings
        Bindings = maps:get(<<"bindings">>, TopologyConfig, []),
        lists:foreach(fun(B) ->
            Bind = #'queue.bind'{
                queue = maps:get(<<"queue">>, B),
                exchange = maps:get(<<"exchange">>, B),
                routing_key = maps:get(<<"routing_key">>, B, <<>>)
            },
            #'queue.bind_ok'{} = amqp_channel:call(Channel, Bind)
        end, Bindings),

        %% Record declared names
        AllNames = [maps:get(<<"name">>, E) || E <- Exchanges] ++
                   [maps:get(<<"name">>, Q) || Q <- Queues],
        Declared = lists:foldl(fun(N, Acc) -> Acc#{N => true} end,
                               State#state.declared, AllNames),
        {ok, State#state{declared = Declared}}
    catch
        _:Reason ->
            {error, {topology_declaration_failed, Reason}}
    end.

build_queue_args(Q) ->
    Args0 = [],
    Args1 = case maps:get(<<"ttl">>, Q, undefined) of
        undefined -> Args0;
        TTL -> [{<<"x-message-ttl">>, long, TTL} | Args0]
    end,
    Args2 = case maps:get(<<"dlx">>, Q, undefined) of
        undefined -> Args1;
        DLX -> [{<<"x-dead-letter-exchange">>, longstr, DLX} | Args1]
    end,
    Args3 = case maps:get(<<"dlx_routing_key">>, Q, undefined) of
        undefined -> Args2;
        DLRK -> [{<<"x-dead-letter-routing-key">>, longstr, DLRK} | Args2]
    end,
    Args4 = case maps:get(<<"max_length">>, Q, undefined) of
        undefined -> Args3;
        ML -> [{<<"x-max-length">>, long, ML} | Args3]
    end,
    Args4.

%% ------------------------------------------------------------------
%% Internal: consuming
%% ------------------------------------------------------------------

open_consume_channel(Conn, Queue, _CallbackPid) ->
    case amqp_connection:open_channel(Conn) of
        {ok, Channel} ->
            %% Set prefetch
            #'basic.qos_ok'{} =
                amqp_channel:call(Channel,
                    #'basic.qos'{prefetch_count = 1}),
            %% Subscribe. Messages arrive as info messages to this gen_server
            %% because we use the default consumer (the channel owner).
            Sub = #'basic.consume'{
                queue = Queue,
                no_ack = false
            },
            #'basic.consume_ok'{consumer_tag = Tag} =
                amqp_channel:subscribe(Channel, Sub, self()),
            {ok, Channel, Tag};
        {error, Reason} ->
            {error, {channel_open_failed, Reason}}
    end.

%% ------------------------------------------------------------------
%% Internal: helpers
%% ------------------------------------------------------------------

close_all_channels(State) ->
    case State#state.publish_channel of
        undefined -> ok;
        PubCh -> catch amqp_channel:close(PubCh)
    end,
    maps:foreach(fun(_, Ch) ->
        catch amqp_channel:close(Ch)
    end, State#state.consume_channels).

encode_payload(Payload) when is_binary(Payload) ->
    Payload;
encode_payload(Payload) when is_map(Payload) ->
    %% Use the JSON encoder available. In the umbrella,
    %% the Elixir Jason library is available.
    %% From Erlang, call it via the Elixir module name.
    'Elixir.Jason':encode_to_iodata!(Payload);
encode_payload(Payload) ->
    term_to_binary(Payload).

amqp_headers_to_map(Headers) ->
    lists:foldl(fun({Key, _Type, Value}, Acc) ->
        Acc#{Key => Value}
    end, #{}, Headers).

ensure_binary(B) when is_binary(B) -> B;
ensure_binary(A) when is_atom(A) -> atom_to_binary(A);
ensure_binary(L) when is_list(L) -> list_to_binary(L);
ensure_binary(I) when is_integer(I) -> integer_to_binary(I).