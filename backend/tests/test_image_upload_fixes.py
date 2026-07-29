from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest

import backend.app.api.routers.openai_compat as oai
from backend.app.api.routers.openai_compat import (
    OAIChatRequest,
    OAIContentPart,
    OAIImageURL,
    OAIMessage,
    _extract_image_data,
    _extract_user_input,
)
from backend.app.schemas.react import ReActDecision
from backend.app.tools.image_understanding import _parse_vision_json


def test_react_decision_coerces_dict_action_input():
    decision = ReActDecision.model_validate(
        {
            "next_action": "product_search",
            "action_input": {"query": "کیبورد گیمینگ"},
            "reason": "search",
            "should_continue": True,
        }
    )
    assert decision.action_input == "کیبورد گیمینگ"


def test_react_decision_coerces_empty_dict_action_input():
    decision = ReActDecision.model_validate(
        {
            "next_action": "image_search",
            "action_input": {},
            "reason": "look at image",
            "should_continue": True,
        }
    )
    assert decision.action_input == ""


def test_parse_vision_json_from_fenced_markdown():
    raw = """```json
{"product_category": "electronics", "concise_description": "keyboard", "visual_attributes": ["rgb"], "suggested_search_query": "کیبورد", "confidence": 0.9}
```"""
    parsed = _parse_vision_json(raw)
    assert parsed["suggested_search_query"] == "کیبورد"


def test_parse_vision_json_rejects_empty():
    with pytest.raises(json.JSONDecodeError):
        _parse_vision_json("")


def test_extract_image_data_from_nested_librechat_path(tmp_path, monkeypatch):
    nested = tmp_path / "user123" / "photo.png"
    nested.parent.mkdir(parents=True)
    nested.write_bytes(b"png-bytes")
    monkeypatch.setattr(oai, "LIBRECHAT_UPLOAD_ROOT", tmp_path)

    data, ctype = _extract_image_data("http://librechat:3080/images/user123/photo.png")
    assert data == b"png-bytes"
    assert ctype == "image/png"


def test_extract_user_input_reads_data_url_image():
    image_url = "data:image/jpeg;base64," + base64.b64encode(b"image-data").decode()
    req = OAIChatRequest(
        messages=[
            OAIMessage(
                role="user",
                content=[
                    OAIContentPart(type="text", text="شبیه این پیدا کن"),
                    OAIContentPart(type="image_url", image_url=OAIImageURL(url=image_url)),
                ],
            )
        ]
    )
    text, data, ctype = _extract_user_input(req)
    assert text == "شبیه این پیدا کن"
    assert data == b"image-data"
    assert ctype == "image/jpeg"


def test_analysis_from_plain_text():
    from backend.app.tools.image_understanding import _analysis_from_plain_text

    analysis = _analysis_from_plain_text(
        "یک کیبورد گیمینگ مکانیکی مشکی با نور RGB. عبارت جستجو: کیبورد گیمینگ",
        "fa-IR",
    )
    assert "کیبورد" in analysis.suggested_search_query
    assert analysis.concise_description


def test_librechat_title_shortcut(client):
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "sale-ai",
            "stream": False,
            "messages": [
                {"role": "user", "content": "کیبورد گیمینگ پیشنهاد بده"},
                {
                    "role": "user",
                    "content": (
                        "Provide a concise, 5-word-or-less title for the conversation, "
                        "using title case capitalization"
                    ),
                },
            ],
        },
    )
    assert response.status_code == 200
    title = response.json()["choices"][0]["message"]["content"]
    assert "کیبورد" in title
    assert "Provide a concise" not in title
