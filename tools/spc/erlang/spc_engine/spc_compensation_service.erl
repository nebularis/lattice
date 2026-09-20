%%% spc_compensation_service.erl
%%%
%%% Tracks completed actions within compensation scopes and executes
%%% compensation sequences when triggered. The compensation plan (which
%%% actions to undo, in what order) is defined in the extension config
%%% and generated at design time.
%%%
%%% Architecture: One ETS table per session tracks which compensable
%%% actions have completed. When compensation is triggered (by error
%%% handling, explicit protocol action, or session failure), this service
%%% reads the completed actions, looks up their compensation pairs,
%%% and returns an ordered sequence of compensation actions for the
%%% coordinator to execute.
%%%
%%% The coordinator executes compensations as synthetic protocol messages.
%%% Each compensation action is a send from the compensating subject.

-module(spc_compensation_service).
-behaviour(gen_server).

-export([
    start_link/0,
    record_action/4,
    trigger_compensation/3,
    clear_session/1
]).

-export([init/1, handle_call/3, handle_cast/2, handle_info/2, terminate/2]).

-record(state, {
    %% ETS table for tracking completed compensable actions.
    %% Key: {SessionId, ScopeId, ActionLabel}
    %% Value: {Participant, StateId, Timestamp, Payload}
    table :: ets:tid()
}).

%% ------------------------------------------------------------------
%% API
%% ------------------------------------------------------------------

start_link() ->
    gen_server:start_link({local, ?MODULE}, ?MODULE, [], []).

%% Record that a compensable action has completed.
%% Called by the coordinator after a successful transition on a label
%% that appears in a compensation scope.
-spec record_action(atom(), atom(), atom(), map()) -> ok.
record_action(SessionId, ScopeId, ActionLabel, Meta) ->
    gen_server:cast(?MODULE, {record, SessionId, ScopeId, ActionLabel, Meta}).

%% Trigger compensation for a scope. Returns the ordered list of
%% compensation actions to execute.
-spec trigger_compensation(atom(), atom(), atom()) ->
    {ok, [{atom(), atom(), non_neg_integer()}]} | {error, term()}.
trigger_compensation(Protocol, SessionId, ScopeId) ->
    gen_server:call(?MODULE, {compensate, Protocol, SessionId, ScopeId}).

%% Clean up all tracking for a session.
-spec clear_session(atom()) -> ok.
clear_session(SessionId) ->
    gen_server:cast(?MODULE, {clear, SessionId}).

%% ------------------------------------------------------------------
%% gen_server callbacks
%% ------------------------------------------------------------------

init([]) ->
    Table = ets:new(spc_compensation_tracker, [
        ordered_set, protected, {keypos, 1}
    ]),
    {ok, #state{table = Table}}.

handle_call({compensate, Protocol, SessionId, ScopeId}, _From, State) ->
    case spc_extension_config:get_compensation_config(Protocol, ScopeId) of
        undefined ->
            {reply, {error, {unknown_scope, ScopeId}}, State};
        Scope ->
            %% Find all completed actions in this scope for this session
            CompletedActions = ets:match_object(
                State#state.table,
                {{SessionId, ScopeId, '_'}, '_'}
            ),
            %% Build the compensation sequence
            CompActions = build_compensation_sequence(Scope, CompletedActions),
            %% Remove the completed actions from tracking
            [ets:delete(State#state.table, Key) || {Key, _} <- CompletedActions],
            {reply, {ok, CompActions}, State}
    end;

handle_call(_Request, _From, State) ->
    {reply, {error, unknown_call}, State}.

handle_cast({record, SessionId, ScopeId, ActionLabel, Meta}, State) ->
    Key = {SessionId, ScopeId, ActionLabel},
    Value = Meta#{timestamp => erlang:system_time(millisecond)},
    ets:insert(State#state.table, {Key, Value}),
    {noreply, State};

handle_cast({clear, SessionId}, State) ->
    %% Delete all entries for this session
    %% ets:match_delete with partial key
    Pattern = {{SessionId, '_', '_'}, '_'},
    ets:match_delete(State#state.table, Pattern),
    {noreply, State};

handle_cast(_, State) ->
    {noreply, State}.

handle_info(_Info, State) ->
    {noreply, State}.

terminate(_Reason, State) ->
    ets:delete(State#state.table),
    ok.

%% ------------------------------------------------------------------
%% Internal
%% ------------------------------------------------------------------

build_compensation_sequence(Scope, CompletedActions) ->
    %% The scope defines pairs and ordering.
    %% We need to find, for each completed action, its compensation pair,
    %% and return them in the correct order.
    Pairs = Scope#comp_scope.pairs,
    Ordering = Scope#comp_scope.ordering,

    CompletedLabels = [Label || {{_, _, Label}, _} <- CompletedActions],

    %% Find compensation pairs for completed actions
    CompPairs = lists:filtermap(fun(Pair) ->
        case lists:member(Pair#comp_pair.action_label, CompletedLabels) of
            true ->
                {true, {Pair#comp_pair.comp_label, Pair#comp_pair.comp_state}};
            false ->
                false
        end
    end, Pairs),

    %% Order: for sequential, reverse order (LIFO — last action compensated first).
    %% For parallel, order doesn't matter (coordinator can fire all at once).
    case Ordering of
        sequential -> lists:reverse(CompPairs);
        parallel -> CompPairs
    end.