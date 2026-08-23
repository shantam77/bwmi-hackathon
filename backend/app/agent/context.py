from dataclasses import dataclass


@dataclass
class AgentContext:
    """Passed as RunContextWrapper[AgentContext].context to every tool call.
    session_id is the only identity a tool may act on -- never read or write
    another session's data."""

    session_id: str
