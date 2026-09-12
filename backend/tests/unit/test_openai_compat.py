"""Content-block <-> Chat Completions translation."""

from __future__ import annotations

import json
from types import SimpleNamespace

from multirag.agent.openai_compat import (
    from_openai_message,
    to_openai_messages,
    to_openai_tools,
)


def _openai_message(content=None, tool_calls=None):
    return SimpleNamespace(content=content, tool_calls=tool_calls)


def _tool_call(call_id, name, arguments):
    return SimpleNamespace(
        id=call_id,
        function=SimpleNamespace(name=name, arguments=arguments),
    )


def test_tool_schema_is_wrapped_as_a_function_tool():
    schema = {
        "name": "search_docs",
        "description": "Semantic search.",
        "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}},
    }
    assert to_openai_tools([schema]) == [
        {
            "type": "function",
            "function": {
                "name": "search_docs",
                "description": "Semantic search.",
                "parameters": schema["input_schema"],
            },
        },
    ]


def test_system_prompt_leads_the_message_list():
    messages = to_openai_messages("be helpful", [])
    assert messages == [{"role": "system", "content": "be helpful"}]


def test_plain_turns_flatten_to_text_content():
    messages = to_openai_messages(
        "sys",
        [
            {"role": "user", "content": [{"type": "text", "text": "hi"}]},
            {"role": "assistant", "content": [{"type": "text", "text": "hello"}]},
        ],
    )
    assert messages[1:] == [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"},
    ]


def test_string_content_is_accepted():
    messages = to_openai_messages("sys", [{"role": "user", "content": "hi"}])
    assert messages[1] == {"role": "user", "content": "hi"}


def test_tool_use_becomes_tool_calls_without_empty_content():
    messages = to_openai_messages(
        "sys",
        [
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "id": "call_1",
                        "name": "search_docs",
                        "input": {"query": "warranty"},
                    },
                ],
            },
        ],
    )
    assistant = messages[1]
    assert "content" not in assistant
    assert assistant["tool_calls"] == [
        {
            "id": "call_1",
            "type": "function",
            "function": {
                "name": "search_docs",
                "arguments": json.dumps({"query": "warranty"}),
            },
        },
    ]


def test_narration_alongside_tool_calls_is_preserved():
    messages = to_openai_messages(
        "sys",
        [
            {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "Looking that up."},
                    {"type": "tool_use", "id": "call_1", "name": "t", "input": {}},
                ],
            },
        ],
    )
    assert messages[1]["content"] == "Looking that up."
    assert len(messages[1]["tool_calls"]) == 1


def test_tool_results_expand_into_separate_tool_messages():
    messages = to_openai_messages(
        "sys",
        [
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "call_1",
                        "content": [{"type": "text", "text": '{"hits": []}'}],
                    },
                    {
                        "type": "tool_result",
                        "tool_use_id": "call_2",
                        "content": [{"type": "text", "text": "boom"}],
                        "is_error": True,
                    },
                ],
            },
        ],
    )
    assert messages[1:] == [
        {"role": "tool", "tool_call_id": "call_1", "content": '{"hits": []}'},
        {"role": "tool", "tool_call_id": "call_2", "content": "boom"},
    ]


def test_empty_tool_result_still_carries_content():
    messages = to_openai_messages(
        "sys",
        [{"role": "user", "content": [{"type": "tool_result", "tool_use_id": "c1"}]}],
    )
    assert messages[1]["content"] == "(no output)"


def test_response_text_converts_to_a_text_block():
    assert from_openai_message(_openai_message(content="done")) == [
        {"type": "text", "text": "done"},
    ]


def test_response_tool_calls_convert_to_tool_use_blocks():
    blocks = from_openai_message(
        _openai_message(
            content=None,
            tool_calls=[_tool_call("call_9", "list_metrics", '{"domain": "sales"}')],
        ),
    )
    assert blocks == [
        {
            "type": "tool_use",
            "id": "call_9",
            "name": "list_metrics",
            "input": {"domain": "sales"},
        },
    ]


def test_unparseable_arguments_degrade_to_an_empty_input():
    blocks = from_openai_message(
        _openai_message(tool_calls=[_tool_call("call_9", "list_metrics", "{not json")]),
    )
    assert blocks[0]["input"] == {}


def test_a_turn_survives_a_round_trip_through_both_directions():
    blocks = from_openai_message(
        _openai_message(
            content="checking",
            tool_calls=[_tool_call("call_1", "search_docs", '{"query": "x"}')],
        ),
    )
    messages = to_openai_messages("sys", [{"role": "assistant", "content": blocks}])
    assert messages[1]["content"] == "checking"
    assert messages[1]["tool_calls"][0]["id"] == "call_1"
    assert json.loads(messages[1]["tool_calls"][0]["function"]["arguments"]) == {
        "query": "x",
    }
