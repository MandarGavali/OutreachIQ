"""
Agent-specific exceptions for the OutreachIQ custom agent loop.
"""


class AgentError(Exception):
    """Base class for all agent-level failures."""


class AgentMaxTurnsError(AgentError):
    """Raised when the agent loop exhausts the maximum turn budget."""


class UnknownToolError(AgentError):
    """The LLM requested a tool that is not registered."""


class ToolExecutionError(AgentError):
    """A registered tool raised an unexpected exception during execution."""


class ToolArgumentError(AgentError):
    """The LLM supplied malformed or missing arguments for a tool call."""
