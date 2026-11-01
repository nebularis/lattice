# SPDX-License-Identifier: MPL-2.0
"""Language model providers, the `LLMProvider` seam (ADR-A71) as the worker's proposers use it.

A provider takes a conversation and the tools it may call, and returns the model's next message and the tokens the
provider counted. The conversation is held in the Chat Completions shape, the lingua franca of model endpoints: messages
with a `role` of `system`, `user`, `assistant` or `tool`, an assistant's `tool_calls`, and a tool's `tool_call_id`. A
provider of another wire format translates to and from it, and may keep what it needs to send back unchanged in a key of
its own on the assistant message, which every other provider leaves out.

Two providers are offered, chosen by `LATTICE_PROPOSER_PROVIDER`:

- `chat-completions`, the default: any endpoint that speaks Chat Completions, at `LATTICE_PROPOSER_URL`.
- `anthropic`: Anthropic's Messages API through its SDK, with prompt caching on the growing conversation, so each turn
  of a tool loop reads the turns before it from the cache. `LATTICE_PROPOSER_URL` overrides the API's base URL, and
  `LATTICE_PROPOSER_EFFORT` sets the model's effort.

Both read `LATTICE_PROPOSER_MODEL`, and the key from `LATTICE_PROPOSER_KEY` or the file `LATTICE_PROPOSER_KEY_FILE`
names. Neither sends a sampling temperature unless a caller asks for one, since current models refuse most values."""

from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Protocol

from .config_studio_secrets import secret

_WIRE = ("role", "content", "tool_calls", "tool_call_id")


class LLMProvider(Protocol):
    """A chat model that may call tools. `chat` returns the assistant's message and the tokens it read and wrote, the
    tokens read counting those served from a cache."""

    name: str

    def chat(self, messages: list, tools: list, temperature: Optional[float] = None) -> tuple[dict, int, int]: ...


@dataclass
class ChatCompletionsProvider:
    endpoint: str
    model: str
    key: Optional[str] = None
    timeout: float = 300.0

    @property
    def name(self) -> str:
        return self.model

    def chat(self, messages: list, tools: list, temperature: Optional[float] = None) -> tuple[dict, int, int]:
        body: dict[str, Any] = {"model": self.model, "messages": [{k: v for k, v in m.items() if k in _WIRE} for m in messages]}
        if tools:
            body["tools"] = [{"type": "function", "function": t} for t in tools]
        if temperature is not None:
            body["temperature"] = temperature
        headers = {"Content-Type": "application/json"}
        if self.key:
            headers["Authorization"] = f"Bearer {self.key}"
        request = urllib.request.Request(self.endpoint.rstrip("/") + "/chat/completions", data=json.dumps(body).encode("utf-8"),
                                         headers=headers, method="POST")
        with urllib.request.urlopen(request, timeout=self.timeout) as response:  # noqa: S310, the deployment's own endpoint
            reply = json.loads(response.read().decode("utf-8"))
        usage = reply.get("usage") or {}
        return reply["choices"][0]["message"], int(usage.get("prompt_tokens") or 0), int(usage.get("completion_tokens") or 0)


# The models that take server-side fallbacks, which re-run a declined request on another model inside the same call.
_FALLBACKS = ("claude-fable-5-1", "claude-opus-5-5", "claude-opus-5", "claude-sonnet-5-5")


@dataclass
class AnthropicProvider:
    model: str
    key: Optional[str] = None
    base_url: Optional[str] = None
    effort: Optional[str] = None
    max_tokens: int = 16000
    timeout: float = 600.0
    client: Any = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if self.client is None:
            import anthropic

            self.client = anthropic.Anthropic(api_key=self.key, base_url=self.base_url, timeout=self.timeout)

    @property
    def name(self) -> str:
        return self.model

    def chat(self, messages: list, tools: list, temperature: Optional[float] = None) -> tuple[dict, int, int]:
        # A temperature is not sent, since the Messages API refuses sampling parameters.
        system, turns = _to_messages(messages)
        request: dict[str, Any] = {
            "model": self.model, "max_tokens": self.max_tokens, "messages": turns,
            # The breakpoint moves to the last block each turn, so a turn reads every earlier turn from the cache.
            "cache_control": {"type": "ephemeral"},
        }
        if system:
            request["system"] = system
        if tools:
            request["tools"] = [{"name": t["name"], "description": t.get("description", ""), "input_schema": t["parameters"]} for t in tools]
        if self.effort:
            request["output_config"] = {"effort": self.effort}
        if self.model in _FALLBACKS:
            request.update(betas=["server-side-fallback-2026-07-01"], fallbacks="default")
            response = self.client.beta.messages.create(**request)
        else:
            response = self.client.messages.create(**request)
        if response.stop_reason == "refusal":
            details = getattr(response, "stop_details", None)
            raise ValueError(f"the model declined the request ({getattr(details, 'category', None) or 'no category given'})")
        if response.stop_reason == "max_tokens":
            raise ValueError(f"the model's reply passed {self.max_tokens} tokens")
        text = "".join(b.text for b in response.content if b.type == "text")
        calls = [{"id": b.id, "type": "function", "function": {"name": b.name, "arguments": json.dumps(b.input)}}
                 for b in response.content if b.type == "tool_use"]
        message = {"role": "assistant", "content": text or None, "anthropic": response.content}
        if calls:
            message["tool_calls"] = calls
        usage = response.usage
        read = usage.input_tokens + (usage.cache_read_input_tokens or 0) + (usage.cache_creation_input_tokens or 0)
        return message, read, usage.output_tokens


def _to_messages(messages: list) -> tuple[str, list]:
    """The system text and the Messages API's turns for a conversation in the Chat Completions shape. An assistant turn
    this provider wrote is sent back as it came, with its thinking, and a run of tool results becomes one user turn."""
    system: list[str] = []
    turns: list[dict] = []
    for m in messages:
        role = m["role"]
        if role == "system":
            system.append(m["content"])
        elif role == "user":
            turns.append({"role": "user", "content": m["content"]})
        elif role == "assistant":
            if "anthropic" in m:
                turns.append({"role": "assistant", "content": m["anthropic"]})
                continue
            blocks: list[dict] = [{"type": "text", "text": m["content"]}] if m.get("content") else []
            blocks += [{"type": "tool_use", "id": c["id"], "name": c["function"]["name"], "input": json.loads(c["function"]["arguments"] or "{}")}
                       for c in m.get("tool_calls") or []]
            turns.append({"role": "assistant", "content": blocks})
        elif role == "tool":
            result = {"type": "tool_result", "tool_use_id": m["tool_call_id"], "content": m["content"]}
            if turns and turns[-1]["role"] == "user" and isinstance(turns[-1]["content"], list):
                turns[-1]["content"].append(result)
            else:
                turns.append({"role": "user", "content": [result]})
    return "\n\n".join(system), turns


def provider_from_env(env: Mapping[str, str]) -> LLMProvider:
    kind = (env.get("LATTICE_PROPOSER_PROVIDER") or "chat-completions").strip()
    url, model = ((env.get(k) or "").strip() for k in ("LATTICE_PROPOSER_URL", "LATTICE_PROPOSER_MODEL"))
    if kind == "chat-completions":
        if not (url and model):
            raise ValueError("no language model is configured: set LATTICE_PROPOSER_URL and LATTICE_PROPOSER_MODEL")
        return ChatCompletionsProvider(url, model, secret(env, "LATTICE_PROPOSER_KEY"))
    if kind == "anthropic":
        if not model:
            raise ValueError("no language model is configured: set LATTICE_PROPOSER_MODEL")
        return AnthropicProvider(model, secret(env, "LATTICE_PROPOSER_KEY"), url or None, (env.get("LATTICE_PROPOSER_EFFORT") or "").strip() or None)
    raise ValueError(f"LATTICE_PROPOSER_PROVIDER names {kind}, which is neither chat-completions nor anthropic")
