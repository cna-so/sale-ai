from __future__ import annotations

from backend.app.api.routers.openai_compat import (
    OAIChatRequest,
    OAIMessage,
    _build_prior_messages,
    _stable_conversation_id,
)


def test_stable_conversation_id_reuses_first_user_turn():
    first = [
        OAIMessage(role="user", content="I need a gift for my friend"),
    ]
    second = [
        OAIMessage(role="user", content="I need a gift for my friend"),
        OAIMessage(role="assistant", content="Here are some options..."),
        OAIMessage(role="user", content="Which one was cheaper?"),
    ]

    assert _stable_conversation_id(first) == _stable_conversation_id(second)
    assert _stable_conversation_id(first).startswith("lc-")


def test_build_prior_messages_excludes_current_user_turn():
    messages = [
        OAIMessage(role="user", content="Find a keyboard"),
        OAIMessage(role="assistant", content="I recommend the Redragon."),
        OAIMessage(role="user", content="Tell me about that one"),
    ]
    prior = _build_prior_messages(messages)

    assert len(prior) == 2
    assert prior[0].role == "user"
    assert prior[0].content == "Find a keyboard"
    assert prior[1].role == "assistant"
    assert "Redragon" in prior[1].content


def test_openai_compat_remembers_prior_turns(client):
    first = client.post(
        "/v1/chat/completions",
        json={
            "model": "sale-ai",
            "stream": False,
            "messages": [{"role": "user", "content": "I want to buy a mechanical keyboard"}],
        },
    )
    assert first.status_code == 200
    first_answer = first.json()["choices"][0]["message"]["content"]

    second = client.post(
        "/v1/chat/completions",
        json={
            "model": "sale-ai",
            "stream": False,
            "messages": [
                {"role": "user", "content": "I want to buy a mechanical keyboard"},
                {"role": "assistant", "content": first_answer},
                {"role": "user", "content": "Tell me about the first option"},
            ],
        },
    )
    assert second.status_code == 200
    body = second.json()
    assert body["object"] == "chat.completion"
    content = body["choices"][0]["message"]["content"]
    assert content
    # Follow-up should resolve against prior product context / history.
    assert "keyboard" in content.lower() or "کیبورد" in content or "## " in content
