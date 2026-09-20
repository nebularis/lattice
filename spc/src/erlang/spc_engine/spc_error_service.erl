%%% spc_error_service.erl
%%%
%%% Routes errors to configured handlers. When an error occurs (transport
%%% failure, validation failure, timeout, business error, job exhaustion),
%%% this service looks up the error handler configuration and determines
%%% the recovery action: transition to a recovery state, escalate to
%%% another participant, or mark the session as failed.
%%%
%%% This service does not own state transitions — it tells the coordinator
%%% what to do, and the coordinator delivers the appropriate message to
%%% the subject process.

-module(spc_error_service).

-export([
    handle_error/5,
    classify_error/1
]).

-type error_class() :: business | transport | timeout | validation | unknown.
-type error_action() :: {recover, atom(), non_neg_integer()}
                      | {escalate, atom(), term()}
                      | {fail_session, term()}.

%% ------------------------------------------------------------------
%% API
%% ------------------------------------------------------------------

%% Called by the coordinator when an error occurs for a participant.
%% Returns the action the coordinator should take.
-spec handle_error(atom(), atom(), atom(), error_class(), term()) -> error_action().
handle_error(Protocol, SessionId, Participant, ErrorClass, ErrorDetail) ->
    case spc_extension_config:get_error_config(Protocol, Participant, ErrorClass) of
        undefined ->
            %% No handler configured for this error type.
            %% Try the catch-all 'unknown' handler.
            case spc_extension_config:get_error_config(Protocol, Participant, unknown) of
                undefined ->
                    %% No handler at all. Fail the session.
                    {fail_session, {unhandled_error, ErrorClass, ErrorDetail}};
                CatchAll ->
                    apply_handler(CatchAll, SessionId, Participant, ErrorDetail)
            end;
        Cfg ->
            apply_handler(Cfg, SessionId, Participant, ErrorDetail)
    end.

%% Classify a raw error reason into one of the standard error types.
-spec classify_error(term()) -> error_class().
classify_error({transport, _}) -> transport;
classify_error({http_error, _, _}) -> transport;
classify_error({amqp_error, _}) -> transport;
classify_error({timeout, _}) -> timeout;
classify_error(timeout) -> timeout;
classify_error({validation, _}) -> validation;
classify_error({shacl_violation, _}) -> validation;
classify_error({business, _}) -> business;
classify_error({retry_exhausted, _}) -> transport;
classify_error(_) -> unknown.

%% ------------------------------------------------------------------
%% Internal
%% ------------------------------------------------------------------

apply_handler(Cfg, _SessionId, Participant, ErrorDetail) ->
    case Cfg of
        #{recovery_label := Label, recovery_state := State}
          when Label =/= undefined, State =/= undefined ->
            %% Transition the subject to the recovery state via the
            %% recovery label. The coordinator delivers this as a
            %% synthetic protocol message.
            {recover, Label, State};
        #{escalate_to := Target} when Target =/= undefined ->
            %% Escalate to another participant.
            {escalate, Target, ErrorDetail};
        _ ->
            {fail_session, {no_recovery, Participant, ErrorDetail}}
    end.