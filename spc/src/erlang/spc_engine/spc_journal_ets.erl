%%%-------------------------------------------------------------------
%%% @doc ETS-based Journal Backend
%%%
%%% Simple in-memory storage for development and testing.
%%% NOT suitable for production - no durability.
%%% @end
%%%-------------------------------------------------------------------
-module(spc_journal_ets).

-export([init/1, append/2, get_by_session/2, close/1]).

init(_Opts) ->
    Table = ets:new(spc_journal_events, [ordered_set, {keypos, 2}]),
    {ok, #{table => Table, counter => 0}}.

append(Event, State = #{table := Table, counter := Counter}) ->
    Key = {element(2, Event), Counter},  % {session_id, sequence}
    ets:insert(Table, setelement(2, Event, Key)),
    {ok, State#{counter := Counter + 1}}.

get_by_session(SessionId, #{table := Table}) ->
    Pattern = {{SessionId, '_'}, '_', '_', '_', '_', '_', '_', '_', '_', '_', '_'},
    Events = ets:match_object(Table, Pattern),
    {ok, [setelement(2, E, element(1, element(2, E))) || E <- Events]}.

close(#{table := Table}) ->
    ets:delete(Table),
    ok.