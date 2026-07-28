from __future__ import annotations

from backend.app.graph.state import AgentState


def route_by_intent(state: AgentState) -> str:
    intent = state.get("intent")
    if intent is None:
        return "execute_rag"
    return intent.intent
