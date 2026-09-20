# src/spc/processle/grammar.py
"""
PEG grammar for ProcessLE.

ProcessLE is a controlled natural language for expressing SPC protocols.
The grammar is deliberately constrained to produce unambiguous parses
that map directly to SPC global type syntax.

Example:
    protocol PlacementNegotiation
        participants Broker, Carrier, Operations
    begin
        the Broker sends submit_risk carrying RiskSubmission
            refined by ins:ValidRiskSubmission
            to the Carrier.
        the Carrier then sends one of
            offer_of_terms carrying TermSheet
                refined by ins:ValidTermSheet
                to the Broker,
            revised_offer carrying RevisedTerms
                to the Broker,
            decline carrying DeclineNotice
                to the Broker.
        ...
    end

    with timeout PT72H on Broker after submit_risk
        triggers follow_up.
    with retry 3 times exponential backoff on Carrier for bind_confirmation
        on exhaustion label bind_failed.
"""

from parsimonious.grammar import Grammar

PROCESSLE_GRAMMAR = Grammar(r"""
    protocol        = ws "protocol" ws name ws
                      participants_decl ws
                      subprotocol_decls
                      "begin" ws global_type ws "end" ws
                      extension_block? ws

    participants_decl = "participants" ws name_list ws

    name_list       = name (ws "," ws name)*

    subprotocol_decls = subprotocol_decl*

    subprotocol_decl = "subprotocol" ws name ws
                       "(" ws role_param_list ws ")" ws
                       "=" ws global_type ws "."

    role_param_list = role_param (ws "," ws role_param)*
    role_param      = name (ws ":" ws name)?

    global_type     = communication / parallel / recursion /
                      recursion_var / subcall / end_type

    communication   = "the" ws name ws "sends" ws comm_body ws
                      "to" ws "the" ws name ws "." ws
                      continuation?

    comm_body       = single_message / choice_messages

    single_message  = label ws payload_clause? ws refinement_clause?

    choice_messages = "one" ws "of" ws message_branch
                      (ws "," ws message_branch)* ws

    message_branch  = label ws payload_clause? ws refinement_clause?
                      ws "to" ws "the" ws name

    payload_clause  = "carrying" ws name

    refinement_clause = "refined" ws "by" ws concept_ref

    concept_ref     = ~r"[a-zA-Z_][a-zA-Z0-9_]*:[a-zA-Z_][a-zA-Z0-9_]*"

    continuation    = "the" ws name ws "then" ws global_type
                    / "then" ws global_type

    parallel        = global_type ws "in" ws "parallel" ws "with" ws global_type

    recursion       = "repeat" ws name ws ":" ws global_type ws
                      "until" ws "done" ws "."

    recursion_var   = "continue" ws name ws "."

    subcall         = "the" ws name ws "calls" ws name ws
                      "with" ws name_list ws "." ws continuation?

    end_type        = "done" ws "."

    extension_block = extension_stmt+

    extension_stmt  = timer_stmt / retry_stmt / error_stmt /
                      compensation_stmt / signal_stmt / connector_stmt

    timer_stmt      = "with" ws "timeout" ws duration ws
                      "on" ws name ws "after" ws label ws
                      "triggers" ws label ws "."

    retry_stmt      = "with" ws "retry" ws integer ws "times" ws
                      backoff_strategy ws "backoff" ws
                      "on" ws name ws "for" ws label ws
                      retry_exhausted? ws "."

    backoff_strategy = "exponential" / "constant" / "linear" / "none"

    retry_exhausted = "on" ws "exhaustion" ws
                      ("label" ws label / "escalate" ws "to" ws name)

    error_stmt      = "on" ws error_type ws "error" ws
                      "for" ws name ws
                      ("recover" ws "via" ws label /
                       "escalate" ws "to" ws name) ws "."

    error_type      = "transport" / "timeout" / "validation" / "business"

    compensation_stmt = "compensate" ws label ws "with" ws label ws
                        "in" ws "scope" ws name ws
                        ("ordering" ws comp_ordering)? ws "."

    comp_ordering   = "sequential" / "parallel"

    signal_stmt     = "signal" ws signal_dir ws label ws
                      "on" ws name ws
                      "to" ws "topic" ws quoted_string ws
                      ("with" ws "key" ws quoted_string)? ws "."

    signal_dir      = "emit" / "subscribe"

    connector_stmt  = "connector" ws name ws
                      "type" ws conn_type ws
                      "url" ws quoted_string ws
                      connector_auth? ws "."

    conn_type       = "http" / "amqp"

    connector_auth  = "auth" ws auth_type ws auth_details

    auth_type       = "bearer" / "basic" / "oauth2" / "api_key"
    auth_details    = quoted_string (ws quoted_string)*

    label           = ~r"[a-z][a-z0-9_]*"
    name            = ~r"[A-Z][a-zA-Z0-9_]*"
    integer         = ~r"[0-9]+"
    duration        = ~r"P(T?\d+[DHMS])+"
    quoted_string   = ~r'"[^"]*"'

    ws              = ~r"\s*"
""")