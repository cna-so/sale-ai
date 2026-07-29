from backend.app.prompts.identity import SALE_AI_IDENTITY_EN, SALE_AI_IDENTITY_FA
from backend.app.prompts.intent import INTENT_SYSTEM_PROMPT_EN, INTENT_SYSTEM_PROMPT_FA
from backend.app.prompts.response import RESPONSE_SYSTEM_PROMPT_EN, RESPONSE_SYSTEM_PROMPT_FA


def test_identity_prompt_marks_sale_ai_assistant():
    assert "Sale-AI-Assistant" in SALE_AI_IDENTITY_EN
    assert "Sale-AI-Assistant" in SALE_AI_IDENTITY_FA


def test_identity_prompt_refuses_jailbreak_and_scope_creep():
    assert "jailbreak" in SALE_AI_IDENTITY_EN.lower()
    assert "ignore previous instructions" in SALE_AI_IDENTITY_EN
    assert "خارج از دامنه" in SALE_AI_IDENTITY_FA or "jailbreak" in SALE_AI_IDENTITY_FA


def test_response_prompts_include_identity_and_grounding():
    assert "Sale-AI-Assistant" in RESPONSE_SYSTEM_PROMPT_EN
    assert "Sale-AI-Assistant" in RESPONSE_SYSTEM_PROMPT_FA
    assert "Never invent" in RESPONSE_SYSTEM_PROMPT_EN
    assert "اختراع نکن" in RESPONSE_SYSTEM_PROMPT_FA


def test_intent_prompts_route_out_of_scope_to_general_chat():
    assert "general_chat" in INTENT_SYSTEM_PROMPT_EN
    assert "jailbreak" in INTENT_SYSTEM_PROMPT_EN.lower()
    assert "general_chat" in INTENT_SYSTEM_PROMPT_FA
