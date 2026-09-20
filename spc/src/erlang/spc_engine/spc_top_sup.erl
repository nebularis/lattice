%%% spc_top_sup.erl

-module(spc_top_sup).
-behaviour(supervisor).

-export([start_link/2, init/1]).

start_link(Name, Children) ->
    supervisor:start_link(Name, ?MODULE, Children).

init(Children) ->
    {ok, {#{strategy => one_for_one, intensity => 10, period => 60}, Children}}.