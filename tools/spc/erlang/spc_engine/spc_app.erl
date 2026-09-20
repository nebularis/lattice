%%% spc_app.erl
%%%
%%% OTP Application callback. Starts the top-level supervision tree.
%%% Assumes spc_sup.erl (your existing top supervisor) starts:
%%% - spc_protocol_registry
%%% - spc_session_sup (DynamicSupervisor)
%%% - spc_extension_sup (the new extension services)
%%% - spc_amqp_bridge (if AMQP is configured)

-module(spc_app).
-behaviour(application).

-export([start/2, stop/1]).

start(_Type, _Args) ->
    %% Load AMQP config from application env
    AmqpConfig = application:get_env(spc_engine, amqp, #{}),

    Children = [
        #{
            id => spc_protocol_registry,
            start => {spc_protocol_registry, start_link, []},
            restart => permanent,
            type => worker
        },
        #{
            id => spc_extension_sup,
            start => {spc_extension_sup, start_link, []},
            restart => permanent,
            type => supervisor
        },
        #{
            id => spc_session_sup,
            start => {spc_session_sup, start_link, []},
            restart => permanent,
            type => supervisor
        }
    ] ++ amqp_child(AmqpConfig),

    supervisor:start_link({local, spc_sup}, spc_top_sup, Children).

stop(_State) ->
    ok.

amqp_child(Config) when map_size(Config) =:= 0 ->
    [];
amqp_child(Config) ->
    [#{
        id => spc_amqp_bridge,
        start => {spc_amqp_bridge, start_link, [Config]},
        restart => permanent,
        type => worker
    }].