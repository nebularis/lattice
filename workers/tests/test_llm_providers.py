# SPDX-License-Identifier: MPL-2.0
from types import SimpleNamespace as NS

import pytest

from lattice_workers.llm_providers import AnthropicProvider, ChatCompletionsProvider, provider_from_env

TOOLS = [{"name": "check_mapping", "description": "Check a proposal.", "parameters": {"type": "object", "properties": {"mcn": {"type": "string"}}}}]


class FakeClient:
    """Stands in for the Anthropic SDK client, answering from a script and keeping each request."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.requests = []
        self.messages = NS(create=self._create)
        self.beta = NS(messages=NS(create=self._create))

    def _create(self, **request):
        self.requests.append(request)
        return self.responses.pop(0)


def _response(content, stop="end_turn", read=0, written=0):
    return NS(content=content, stop_reason=stop, stop_details=None,
              usage=NS(input_tokens=100, output_tokens=20, cache_read_input_tokens=read, cache_creation_input_tokens=written))


def test_the_anthropic_provider_caches_the_conversation_and_sends_its_own_turns_back_unchanged():
    thinking = NS(type="thinking", thinking="", signature="sig")
    call_a = NS(type="tool_use", id="a", name="check_mapping", input={"mcn": "x"})
    call_b = NS(type="tool_use", id="b", name="check_mapping", input={"mcn": "y"})
    client = FakeClient(_response([thinking, call_a, call_b], "tool_use", written=900), _response([NS(type="text", text="done")], read=900))
    provider = AnthropicProvider("claude-opus-5-5", client=client, effort="high")
    messages = [{"role": "system", "content": "Propose."}, {"role": "user", "content": "Go."}]
    message, read, written = provider.chat(messages, TOOLS, temperature=0)
    assert (read, written) == (1000, 20)
    assert [c["function"]["name"] for c in message["tool_calls"]] == ["check_mapping", "check_mapping"]
    messages += [message, {"role": "tool", "tool_call_id": "a", "content": "ok"}, {"role": "tool", "tool_call_id": "b", "content": "ok"}]
    message, read, _ = provider.chat(messages, TOOLS)
    assert message["content"] == "done" and "tool_calls" not in message and read == 1000
    first, second = client.requests
    assert first["system"] == "Propose." and first["cache_control"] == {"type": "ephemeral"}
    assert first["tools"][0]["input_schema"]["properties"]["mcn"] == {"type": "string"}
    assert first["fallbacks"] == "default" and first["output_config"] == {"effort": "high"} and "temperature" not in first
    assert second["messages"][1] == {"role": "assistant", "content": [thinking, call_a, call_b]}  # thinking kept, as it came
    assert second["messages"][2]["role"] == "user" and [r["tool_use_id"] for r in second["messages"][2]["content"]] == ["a", "b"]


def test_a_declined_or_cut_off_reply_fails_the_turn():
    for stop, said in (("refusal", "declined"), ("max_tokens", "passed")):
        provider = AnthropicProvider("claude-haiku-5-5", client=FakeClient(_response([], stop)))
        with pytest.raises(ValueError, match=said):
            provider.chat([{"role": "user", "content": "Go."}], [])
        assert "fallbacks" not in provider.client.requests[0]  # a model without fallbacks is not sent them


def test_a_chat_completions_turn_from_another_provider_is_translated():
    client = FakeClient(_response([NS(type="text", text="ok")]))
    AnthropicProvider("claude-sonnet-5", client=client).chat([
        {"role": "user", "content": "Go."},
        {"role": "assistant", "content": "Checking.", "tool_calls": [{"id": "1", "type": "function", "function": {"name": "check_mapping", "arguments": "{\"mcn\": \"x\"}"}}]},
        {"role": "tool", "tool_call_id": "1", "content": "ok"}], TOOLS)
    assistant = client.requests[0]["messages"][1]["content"]
    assert assistant == [{"type": "text", "text": "Checking."}, {"type": "tool_use", "id": "1", "name": "check_mapping", "input": {"mcn": "x"}}]


def test_the_provider_is_chosen_by_the_environment():
    assert isinstance(provider_from_env({"LATTICE_PROPOSER_URL": "http://m/v1", "LATTICE_PROPOSER_MODEL": "m"}), ChatCompletionsProvider)
    chosen = provider_from_env({"LATTICE_PROPOSER_PROVIDER": "anthropic", "LATTICE_PROPOSER_MODEL": "claude-opus-5-5",
                                "LATTICE_PROPOSER_KEY": "sk-test", "LATTICE_PROPOSER_EFFORT": "high"})
    assert isinstance(chosen, AnthropicProvider) and (chosen.model, chosen.effort, chosen.base_url) == ("claude-opus-5-5", "high", None)
    with pytest.raises(ValueError, match="no language model"):
        provider_from_env({"LATTICE_PROPOSER_PROVIDER": "anthropic"})
    with pytest.raises(ValueError, match="neither"):
        provider_from_env({"LATTICE_PROPOSER_PROVIDER": "other", "LATTICE_PROPOSER_MODEL": "m"})
