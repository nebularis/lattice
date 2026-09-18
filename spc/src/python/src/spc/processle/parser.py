# src/spc/processle/parser.py
"""
ProcessLE parser: text → AST.

Walks the PEG parse tree produced by parsimonious and constructs
the typed AST nodes defined in ast_nodes.py.
"""

from __future__ import annotations
from parsimonious.nodes import Node
from spc.processle.grammar import PROCESSLE_GRAMMAR
from spc.processle import ast_nodes as ast
import re
from typing import Optional


class ProcessLEParser:
    """Parse ProcessLE source text into an AST Protocol node."""

    def __init__(self):
        self.grammar = PROCESSLE_GRAMMAR

    def parse(self, source: str) -> ast.Protocol:
        """Parse a ProcessLE source string into a Protocol AST."""
        tree = self.grammar.parse(source)
        return self._visit_protocol(tree)

    def parse_file(self, path: str) -> ast.Protocol:
        """Parse a ProcessLE source file."""
        with open(path) as f:
            return self.parse(f.read())

    # --- Visitor methods ---

    def _visit_protocol(self, node: Node) -> ast.Protocol:
        children = self._named_children(node)
        name = self._extract_name(children["name"])
        participants = self._visit_participants(children["participants_decl"])

        subprotocols = []
        for sp_node in self._find_all(node, "subprotocol_decl"):
            subprotocols.append(self._visit_subprotocol(sp_node))

        global_type = self._visit_global_type(
            self._find_first(node, "global_type"))

        extensions = []
        ext_block = self._find_first(node, "extension_block")
        if ext_block:
            extensions = self._visit_extension_block(ext_block)

        return ast.Protocol(
            name=name,
            participants=participants,
            global_type=global_type,
            subprotocols=subprotocols,
            extensions=extensions,
        )

    def _visit_participants(self, node: Node) -> list[ast.Participant]:
        names = self._extract_name_list(node)
        return [ast.Participant(name=n) for n in names]

    def _visit_subprotocol(self, node: Node) -> ast.SubprotocolDecl:
        name = self._extract_text(self._find_first(node, "name"))
        role_params = []
        for rp in self._find_all(node, "role_param"):
            names = self._find_all(rp, "name")
            rp_name = self._extract_text(names[0])
            rp_type = self._extract_text(names[1]) if len(names) > 1 else None
            role_params.append(ast.RoleParam(name=rp_name, type_ref=rp_type))
        body = self._visit_global_type(self._find_first(node, "global_type"))
        return ast.SubprotocolDecl(name=name, role_params=role_params, body=body)

    def _visit_global_type(self, node: Node) -> ast.GlobalType:
        """Dispatch to the appropriate global type visitor."""
        if node is None:
            return ast.End()

        # Walk down through the grammar alternation
        inner = self._unwrap_alternation(node)
        expr_name = inner.expr_name if hasattr(inner, 'expr_name') else ""

        if expr_name == "communication":
            return self._visit_communication(inner)
        elif expr_name == "parallel":
            return self._visit_parallel(inner)
        elif expr_name == "recursion":
            return self._visit_recursion(inner)
        elif expr_name == "recursion_var":
            return self._visit_recursion_var(inner)
        elif expr_name == "subcall":
            return self._visit_subcall(inner)
        elif expr_name == "end_type":
            return ast.End()
        else:
            # Try to find a communication or other construct in children
            comm = self._find_first(node, "communication")
            if comm:
                return self._visit_communication(comm)
            return ast.End()

    def _visit_communication(self, node: Node) -> ast.Communication:
        names = self._find_all(node, "name")
        sender = self._extract_text(names[0])

        # Receiver might be in the main comm or in each branch
        comm_body = self._find_first(node, "comm_body")

        single = self._find_first(comm_body, "single_message")
        if single:
            receiver = self._extract_text(names[1]) if len(names) > 1 else ""
            option = self._visit_single_message(single)
            # Continuation
            cont_node = self._find_first(node, "continuation")
            if cont_node:
                option.continuation = self._visit_continuation(cont_node)
            return ast.Communication(
                sender=sender, receiver=receiver, options=[option]
            )

        # Choice messages
        branches = self._find_all(comm_body, "message_branch")
        options = []
        receiver = None
        for branch in branches:
            opt, branch_receiver = self._visit_message_branch(branch)
            if receiver is None:
                receiver = branch_receiver
            options.append(opt)

        # Continuation after the choice
        cont_node = self._find_first(node, "continuation")
        if cont_node:
            cont = self._visit_continuation(cont_node)
            # Attach continuation to each branch that doesn't have one
            for opt in options:
                if opt.continuation is None:
                    opt.continuation = cont

        return ast.Communication(
            sender=sender, receiver=receiver or "", options=options
        )

    def _visit_single_message(self, node: Node) -> ast.MessageOption:
        label = self._extract_text(self._find_first(node, "label"))
        sort = self._extract_payload_sort(node)
        refinement = self._extract_refinement(node)
        return ast.MessageOption(
            label=label, sort=sort or "Unit", refinement=refinement
        )

    def _visit_message_branch(self, node: Node) -> tuple[ast.MessageOption, str]:
        label = self._extract_text(self._find_first(node, "label"))
        sort = self._extract_payload_sort(node)
        refinement = self._extract_refinement(node)
        names = self._find_all(node, "name")
        receiver = self._extract_text(names[-1]) if names else ""
        return ast.MessageOption(
            label=label, sort=sort or "Unit", refinement=refinement
        ), receiver

    def _visit_continuation(self, node: Node) -> ast.GlobalType:
        gt = self._find_first(node, "global_type")
        if gt:
            return self._visit_global_type(gt)
        return ast.End()

    def _visit_parallel(self, node: Node) -> ast.ParallelComp:
        gts = self._find_all(node, "global_type")
        left = self._visit_global_type(gts[0])
        right = self._visit_global_type(gts[1])
        return ast.ParallelComp(left=left, right=right)

    def _visit_recursion(self, node: Node) -> ast.Recursion:
        var_name = self._extract_text(self._find_first(node, "name"))
        body = self._visit_global_type(self._find_first(node, "global_type"))
        return ast.Recursion(var=var_name, body=body)

    def _visit_recursion_var(self, node: Node) -> ast.RecursionVar:
        var_name = self._extract_text(self._find_first(node, "name"))
        return ast.RecursionVar(var=var_name)

    def _visit_subcall(self, node: Node) -> ast.SubprotocolCall:
        names = self._find_all(node, "name")
        caller = self._extract_text(names[0])
        protocol_name = self._extract_text(names[1])
        role_args = [self._extract_text(n) for n in names[2:]]
        cont_node = self._find_first(node, "continuation")
        cont = self._visit_continuation(cont_node) if cont_node else None
        return ast.SubprotocolCall(
            caller=caller, protocol_name=protocol_name,
            role_args=role_args, continuation=cont
        )

    # --- Extension visitors ---

    def _visit_extension_block(self, node: Node) -> list[ast.ExtensionAnnotation]:
        extensions = []
        for stmt in self._find_all(node, "extension_stmt"):
            inner = self._unwrap_alternation(stmt)
            ext = self._visit_extension_stmt(inner)
            if ext:
                extensions.append(ext)
        return extensions

    def _visit_extension_stmt(self, node: Node) -> Optional[ast.ExtensionAnnotation]:
        expr_name = node.expr_name if hasattr(node, 'expr_name') else ""

        if expr_name == "timer_stmt" or self._find_first(node, "timer_stmt"):
            n = self._find_first(node, "timer_stmt") or node
            return self._visit_timer_stmt(n)
        elif expr_name == "retry_stmt" or self._find_first(node, "retry_stmt"):
            n = self._find_first(node, "retry_stmt") or node
            return self._visit_retry_stmt(n)
        elif expr_name == "error_stmt" or self._find_first(node, "error_stmt"):
            n = self._find_first(node, "error_stmt") or node
            return self._visit_error_stmt(n)
        elif expr_name == "compensation_stmt" or self._find_first(node, "compensation_stmt"):
            n = self._find_first(node, "compensation_stmt") or node
            return self._visit_compensation_stmt(n)
        elif expr_name == "signal_stmt" or self._find_first(node, "signal_stmt"):
            n = self._find_first(node, "signal_stmt") or node
            return self._visit_signal_stmt(n)
        elif expr_name == "connector_stmt" or self._find_first(node, "connector_stmt"):
            n = self._find_first(node, "connector_stmt") or node
            return self._visit_connector_stmt(n)
        return None

    def _visit_timer_stmt(self, node: Node) -> ast.TimerAnnotation:
        duration = self._extract_text(self._find_first(node, "duration"))
        names = self._find_all(node, "name")
        participant = self._extract_text(names[0]) if names else ""
        labels = self._find_all(node, "label")
        after_label = self._extract_text(labels[0]) if labels else ""
        timeout_label = self._extract_text(labels[1]) if len(labels) > 1 else ""
        return ast.TimerAnnotation(
            target_participant=participant,
            target_state_desc=f"after {after_label}",
            target_label=after_label,
            duration=duration,
            timeout_label=timeout_label,
        )

    def _visit_retry_stmt(self, node: Node) -> ast.RetryAnnotation:
        integer_node = self._find_first(node, "integer")
        max_attempts = int(self._extract_text(integer_node)) if integer_node else 3
        strategy = self._extract_text(
            self._find_first(node, "backoff_strategy")) or "exponential"
        names = self._find_all(node, "name")
        participant = self._extract_text(names[0]) if names else ""
        labels = self._find_all(node, "label")
        label = self._extract_text(labels[0]) if labels else ""

        on_exhausted_label = None
        on_exhausted_escalate = None
        exhaust_node = self._find_first(node, "retry_exhausted")
        if exhaust_node:
            exhaust_labels = self._find_all(exhaust_node, "label")
            exhaust_names = self._find_all(exhaust_node, "name")
            if exhaust_labels:
                on_exhausted_label = self._extract_text(exhaust_labels[0])
            if exhaust_names:
                on_exhausted_escalate = self._extract_text(exhaust_names[0])

        return ast.RetryAnnotation(
            target_participant=participant,
            target_label=label,
            max_attempts=max_attempts,
            backoff=strategy,
            on_exhausted_label=on_exhausted_label,
            on_exhausted_escalate=on_exhausted_escalate,
        )

    def _visit_error_stmt(self, node: Node) -> ast.ErrorAnnotation:
        error_type = self._extract_text(
            self._find_first(node, "error_type")) or "unknown"
        names = self._find_all(node, "name")
        participant = self._extract_text(names[0]) if names else ""
        labels = self._find_all(node, "label")
        recovery_label = self._extract_text(labels[0]) if labels else None
        escalate_to = self._extract_text(names[1]) if len(names) > 1 else None
        return ast.ErrorAnnotation(
            target_participant=participant,
            error_type=error_type,
            recovery_label=recovery_label,
            escalate_to=escalate_to,
        )

    def _visit_compensation_stmt(self, node: Node) -> ast.CompensationAnnotation:
        labels = self._find_all(node, "label")
        names = self._find_all(node, "name")
        action_label = self._extract_text(labels[0]) if labels else ""
        comp_label = self._extract_text(labels[1]) if len(labels) > 1 else ""
        scope = self._extract_text(names[0]) if names else "default"
        ordering_node = self._find_first(node, "comp_ordering")
        ordering = self._extract_text(ordering_node) if ordering_node else "sequential"
        return ast.CompensationAnnotation(
            scope_name=scope,
            action_label=action_label,
            comp_label=comp_label,
            ordering=ordering,
        )

    def _visit_signal_stmt(self, node: Node) -> ast.SignalAnnotation:
        direction = self._extract_text(
            self._find_first(node, "signal_dir")) or "emit"
        labels = self._find_all(node, "label")
        label = self._extract_text(labels[0]) if labels else ""
        names = self._find_all(node, "name")
        participant = self._extract_text(names[0]) if names else ""
        strings = self._find_all(node, "quoted_string")
        topic = self._extract_quoted(strings[0]) if strings else ""
        routing_key = self._extract_quoted(strings[1]) if len(strings) > 1 else ""
        return ast.SignalAnnotation(
            target_participant=participant,
            target_label=label,
            topic=topic,
            routing_key_template=routing_key,
            direction=direction,
        )

    def _visit_connector_stmt(self, node: Node) -> ast.ConnectorAnnotation:
        names = self._find_all(node, "name")
        conn_name = self._extract_text(names[0]) if names else ""
        conn_type = self._extract_text(
            self._find_first(node, "conn_type")) or "http"
        strings = self._find_all(node, "quoted_string")
        base_url = self._extract_quoted(strings[0]) if strings else ""
        return ast.ConnectorAnnotation(
            connector_name=conn_name,
            connector_type=conn_type,
            base_url=base_url,
        )

    # --- Utility methods ---

    def _extract_text(self, node: Optional[Node]) -> str:
        if node is None:
            return ""
        return node.text.strip()

    def _extract_name(self, node: Node) -> str:
        return self._extract_text(node)

    def _extract_name_list(self, node: Node) -> list[str]:
        names = self._find_all(node, "name")
        return [self._extract_text(n) for n in names]

    def _extract_payload_sort(self, node: Node) -> Optional[str]:
        payload = self._find_first(node, "payload_clause")
        if payload:
            name = self._find_first(payload, "name")
            return self._extract_text(name) if name else None
        return None

    def _extract_refinement(self, node: Node) -> Optional[ast.Refinement]:
        ref = self._find_first(node, "refinement_clause")
        if ref:
            concept = self._find_first(ref, "concept_ref")
            if concept:
                return ast.ConceptMembership(
                    concept_iri=self._extract_text(concept))
        return None

    def _extract_quoted(self, node: Optional[Node]) -> str:
        if node is None:
            return ""
        text = node.text.strip()
        if text.startswith('"') and text.endswith('"'):
            return text[1:-1]
        return text

    def _find_first(self, node: Node, expr_name: str) -> Optional[Node]:
        """Find the first descendant with the given expression name."""
        if node.expr_name == expr_name:
            return node
        for child in node:
            result = self._find_first(child, expr_name)
            if result is not None:
                return result
        return None

    def _find_all(self, node: Node, expr_name: str) -> list[Node]:
        """Find all descendants with the given expression name."""
        results = []
        if node.expr_name == expr_name:
            results.append(node)
        for child in node:
            results.extend(self._find_all(child, expr_name))
        return results

    def _unwrap_alternation(self, node: Node) -> Node:
        """Unwrap single-child alternation nodes to find the actual construct."""
        while len(node) == 1 and node.expr_name in (
            "", "global_type", "extension_stmt", "comm_body"
        ):
            node = node[0]
        return node

    def _named_children(self, node: Node) -> dict[str, Node]:
        """Extract named children from a sequence node."""
        result = {}
        for child in node:
            if child.expr_name:
                result[child.expr_name] = child
        return result