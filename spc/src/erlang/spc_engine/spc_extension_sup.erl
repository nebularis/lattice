%%% spc_extension_sup.erl
%%%
%%% Supervisor for all extension services. Started as part of the
%%% spc_engine application supervision tree.

-module(spc_extension_sup).
-behaviour(supervisor).

-export([start_link/0, init/1]).

start_link() ->
    supervisor:start_link({local, ?MODULE}, ?MODULE, []).

init([]) ->
    Children = [
        #{
            id => spc_timer_service,
            start => {spc_timer_service, start_link, []},
            restart => permanent,
            type => worker
        },
        #{
            id => spc_job_service,
            start => {spc_job_service, start_link, []},
            restart => permanent,
            type => worker
        },
        #{
            id => spc_compensation_service,
            start => {spc_compensation_service, start_link, []},
            restart => permanent,
            type => worker
        },
        #{
            id => spc_signal_service,
            start => {spc_signal_service, start_link, []},
            restart => permanent,
            type => worker
        }
    ],
    {ok, {#{strategy => one_for_one, intensity => 5, period => 60}, Children}}.