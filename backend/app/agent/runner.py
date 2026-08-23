"""Builds the Agent, runs it streamed, and maps the SDK's stream events onto
the frozen SSE contract: token, tool_call, component, alert, done. This
mapping is defined ONCE here and must not drift -- frontend/lib/stream.ts
expects exactly these five event types and nothing else."""

import json
from collections.abc import AsyncIterator

from agents import Agent, ItemHelpers, Runner, set_default_openai_key
from agents.items import ToolCallItem, ToolCallOutputItem

from app import store
from app.agent.context import AgentContext
from app.agent.prompt import INSTRUCTIONS
from app.agent.session import PostgresSession
from app.agent.tools import ALL_TOOLS
from app.config import OPENAI_API_KEY, OPENAI_MODEL

# Tool name -> frontend component name, for the `component` SSE event. Tools
# not listed here (e.g. get_pnr_status) never trigger a component -- their
# result is just narrated in text.
TOOL_COMPONENTS = {
    "search_trains": "OptionCard",
    "quote_booking": "PaymentSheet",
    "confirm_booking": "PNRConfirmation",
}

_configured = False


def _ensure_configured() -> None:
    global _configured
    if not _configured:
        set_default_openai_key(OPENAI_API_KEY)
        _configured = True


def build_agent() -> Agent:
    _ensure_configured()
    return Agent(
        name="Saarthi",
        instructions=INSTRUCTIONS,
        tools=ALL_TOOLS,
        model=OPENAI_MODEL,
    )


def sse(event_type: str, **payload) -> str:
    return f"data: {json.dumps({'type': event_type, **payload})}\n\n"


async def stream_chat(session_id: str, user_message: str) -> AsyncIterator[str]:
    store.append_message(session_id, "user", user_message)

    agent = build_agent()
    session = PostgresSession(session_id)
    context = AgentContext(session_id=session_id)

    result = Runner.run_streamed(agent, input=user_message, context=context, session=session)

    final_text_parts: list[str] = []
    last_tool_name: str | None = None
    last_component: dict | None = None

    try:
        async for event in result.stream_events():
            if event.type == "raw_response_event":
                data = event.data
                if getattr(data, "type", None) == "response.output_text.delta":
                    delta = data.delta
                    final_text_parts.append(delta)
                    yield sse("token", content=delta)

            elif event.type == "run_item_stream_event":
                item = event.item

                if event.name == "tool_called" and isinstance(item, ToolCallItem):
                    last_tool_name = getattr(item.raw_item, "name", None)
                    if last_tool_name:
                        yield sse("tool_call", name=last_tool_name)

                elif event.name == "tool_output" and isinstance(item, ToolCallOutputItem):
                    output = item.output
                    if (
                        last_tool_name in TOOL_COMPONENTS
                        and isinstance(output, dict)
                        and "error" not in output
                    ):
                        component_name = TOOL_COMPONENTS[last_tool_name]
                        last_component = {"component": component_name, "props": output}
                        yield sse("component", component=component_name, props=output)

                elif event.name == "message_output_created":
                    text = ItemHelpers.text_message_output(item)
                    if text and not final_text_parts:
                        # Fallback for models/paths that don't stream token
                        # deltas -- still surface the text as one token event
                        # so the frontend always receives something to render.
                        final_text_parts.append(text)
                        yield sse("token", content=text)
    finally:
        final_text = "".join(final_text_parts)
        store.append_message(
            session_id,
            "agent",
            final_text,
            component=last_component,
        )
        yield sse("done")
