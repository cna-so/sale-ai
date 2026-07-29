from __future__ import annotations

import json
import logging

from backend.app.core.config import Settings
from backend.app.graph.state import AgentState
from backend.app.schemas.react import ReActDecision, ReActStep
from backend.app.services.llm_service import LLMService

logger = logging.getLogger(__name__)

_HARD_MAX_ITERATIONS = 8
_TOOL_ACTIONS = {"rag_search", "product_search", "image_search"}


def _fallback_decision(state: AgentState) -> ReActDecision:
    """Choose the initial action from the deterministic intent classifier."""
    intent = state.get("intent")
    intent_name = intent.intent if intent else "rag_query"
    query = (intent.search_query if intent else "") or state.get("user_message", "")

    action_by_intent = {
        "rag_query": "rag_search",
        "product_search": "product_search",
        "recommendation": "product_search",
        "gift_recommendation": "product_search",
        "product_comparison": "product_search",
        "product_detail": "product_search",
        "follow_up": "product_search",
        "image_search": "image_search",
    }
    action = action_by_intent.get(intent_name, "answer_directly")
    return ReActDecision(
        next_action=action,
        action_input=query,
        reason="Use the capability selected by intent classification.",
        should_continue=action in _TOOL_ACTIONS,
    )


def _decision_prompt(state: AgentState) -> list[dict[str, str]]:
    intent = state.get("intent")
    language = intent.detected_language if intent else "fa"
    steps = state.get("react_steps", [])
    observation_lines = [
        f"{step.action}: {step.observation or 'pending'}" for step in steps[-3:]
    ]
    observations = "\n".join(observation_lines) or "No actions have run."
    language_instruction = (
        "Respond in Persian-compatible query terms when appropriate."
        if language == "fa"
        else "Respond in English-compatible query terms when appropriate."
    )
    return [
        {
            "role": "system",
            "content": (
                "You are a shopping-agent action controller. Return JSON only with "
                "next_action, action_input, reason, and should_continue. "
                "next_action must be one of rag_search, product_search, image_search, "
                "answer_directly, stop. reason must be a concise action summary, never "
                "private reasoning. Choose one action at a time. Use image_search only "
                "when an image is available. Choose stop or answer_directly when the "
                "available observations are sufficient. "
                + language_instruction
            ),
        },
        {
            "role": "user",
            "content": (
                f"User query: {state.get('user_message', '')}\n"
                f"Intent: {intent.intent if intent else 'unknown'}\n"
                f"Image available: {state.get('image_data') is not None}\n"
                f"Previous observations:\n{observations}"
            ),
        },
    ]


def _normalize_decision(state: AgentState, decision: ReActDecision) -> ReActDecision:
    if decision.next_action == "image_search" and state.get("image_data") is None:
        return ReActDecision(
            next_action="stop",
            reason="Image search is unavailable because no image was provided.",
            should_continue=False,
        )

    if decision.next_action in _TOOL_ACTIONS:
        prior_actions = {
            (step.action, step.action_input)
            for step in state.get("react_steps", [])
            if step.action in _TOOL_ACTIONS
        }
        if (decision.next_action, decision.action_input) in prior_actions:
            return ReActDecision(
                next_action="stop",
                reason="The same action has already been completed.",
                should_continue=False,
            )
        if not decision.should_continue:
            return decision.model_copy(update={"should_continue": True})

    if decision.next_action in {"answer_directly", "stop"}:
        return decision.model_copy(update={"should_continue": False})
    return decision


def route_after_react_controller(state: AgentState) -> str:
    decision = state.get("react_decision")
    if decision is None or not decision.should_continue:
        return "generate_response"
    if decision.next_action in _TOOL_ACTIONS:
        return decision.next_action
    return "generate_response"


def make_react_controller_node(llm_service: LLMService, settings: Settings):
    async def react_controller(state: AgentState) -> AgentState:
        max_iterations = min(settings.react_max_iterations, _HARD_MAX_ITERATIONS)
        iteration = state.get("react_iteration", 0)
        if iteration >= max_iterations:
            decision = ReActDecision(
                next_action="stop",
                reason="Reached the configured action limit.",
                should_continue=False,
            )
        else:
            try:
                content = await llm_service.chat(
                    messages=_decision_prompt(state),
                    temperature=0.0,
                    max_tokens=250,
                    response_format={"type": "json_object"},
                )
                decision = ReActDecision.model_validate(json.loads(content))
            except Exception as exc:
                logger.info("ReAct controller fallback: %s", exc)
                decision = _fallback_decision(state)

            decision = _normalize_decision(state, decision)

        step = ReActStep(
            iteration=iteration + 1,
            action=decision.next_action,
            action_input=decision.action_input,
            reason=decision.reason,
        )
        return {
            **state,
            "react_decision": decision,
            "react_iteration": iteration + 1,
            "react_steps": [*state.get("react_steps", []), step],
        }

    return react_controller


def add_react_observation(state: AgentState, observation: str) -> list[ReActStep]:
    """Attach a compact tool outcome to the active controller step."""
    steps = state.get("react_steps", [])
    if not steps:
        return steps
    return [*steps[:-1], steps[-1].model_copy(update={"observation": observation})]
