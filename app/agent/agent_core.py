"""
Custom Agent Core for OutreachIQ V2.

Implements the tool-calling agent loop WITHOUT using LangChain AgentExecutor
or any other framework-level agent executor.

The loop:

    messages = [system, user]
    for turn in range(MAX_TURNS):
        response = llm.invoke(messages)
        if response has tool_calls:
            for each tool_call:
                validate arguments
                find tool in AVAILABLE_TOOLS
                execute tool (or return structured error)
            append AIMessage + ToolMessages to conversation
            continue
        else:
            return final response text

The LLM decides which tool to call.
Python validates, dispatches, and appends results.
The loop runs until the LLM produces a final answer or MAX_TURNS is exhausted.

Public API:

    agent = OutreachAgent()
    result: OutreachMessage = agent.run(request)

Or use the module-level convenience function:

    result = generate_outreach(request)
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import ValidationError

from app.agent.exceptions import AgentError, AgentMaxTurnsError
from app.agent.prompts import SYSTEM_PROMPT
from app.agent.tools import AVAILABLE_TOOLS, TOOL_LIST, GenerateMessageArgs, ScrapeProfileArgs
from app.config import settings
from app.models.request_models import OutreachRequest, Tone
from app.models.response_models import OutreachMessage

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Argument schemas keyed by tool name — used for per-call validation
# ---------------------------------------------------------------------------

_ARG_SCHEMAS: dict[str, type] = {
    "scrape_profile": ScrapeProfileArgs,
    "generate_message": GenerateMessageArgs,
}


# ---------------------------------------------------------------------------
# OutreachAgent — the custom loop
# ---------------------------------------------------------------------------

class OutreachAgent:
    """
    Custom tool-calling agent for OutreachIQ.

    Manages the full conversation lifecycle:
    - Builds and maintains the message history
    - Sends messages to the LLM with bound tool schemas
    - Detects tool calls in the LLM response
    - Validates tool arguments
    - Dispatches to AVAILABLE_TOOLS
    - Appends tool results back to the conversation
    - Repeats until the LLM produces a final answer or max turns is reached

    Args:
        llm: A ChatGoogleGenerativeAI instance (or compatible LangChain chat model).
              If None, a default instance is created from settings.
        max_turns: Maximum number of LLM calls before raising AgentMaxTurnsError.
                   Defaults to settings.AGENT_MAX_TURNS.
    """

    def __init__(
        self,
        llm: ChatGoogleGenerativeAI | None = None,
        max_turns: int | None = None,
    ) -> None:
        if llm is None:
            llm = ChatGoogleGenerativeAI(
                model=settings.MODEL_NAME,
                google_api_key=settings.GOOGLE_API_KEY,
                temperature=0.3,
            )
        self._max_turns = max_turns if max_turns is not None else settings.AGENT_MAX_TURNS
        # Bind tools once so the LLM knows which tools are available
        self._llm = llm.bind_tools(TOOL_LIST)

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def run(self, request: OutreachRequest) -> OutreachMessage:
        """
        Execute the agent loop for a single OutreachRequest.

        Args:
            request: Validated OutreachRequest with profile_url,
                     product_description, and tone.

        Returns:
            OutreachMessage produced by the generate_message tool.

        Raises:
            AgentMaxTurnsError: Turn budget exhausted without a final answer.
            AgentError: Any other agent-level failure.
        """
        logger.info("[Agent] Started for profile_url=%s", request.profile_url)

        messages: list[BaseMessage] = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=self._build_user_message(request)),
        ]

        turn = 0
        while turn < self._max_turns:
            turn += 1
            logger.info("[Agent] Turn %d / %d", turn, self._max_turns)

            # --- Call the LLM ---
            response: AIMessage = self._llm.invoke(messages)

            # --- Does the LLM want to call tools? ---
            if response.tool_calls:
                logger.info(
                    "[Agent] Turn %d: %d tool call(s) requested",
                    turn,
                    len(response.tool_calls),
                )
                # Append the assistant's tool-call message first
                messages.append(response)

                # Dispatch each tool call and append its result
                for tc in response.tool_calls:
                    tool_result_msg = self._dispatch_tool_call(tc)
                    messages.append(tool_result_msg)

                # Continue the loop — give the LLM the results
                continue

            # --- No tool calls: the LLM produced a final response ---
            final_text = response.content
            logger.info("[Agent] Turn %d: final response received", turn)
            return self._parse_final_response(final_text)

        # Turn budget exhausted
        logger.error("[Agent] Maximum turns (%d) reached without final response", self._max_turns)
        raise AgentMaxTurnsError(
            f"Agent reached the maximum turn limit ({self._max_turns}) "
            "without producing a final response."
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_user_message(request: OutreachRequest) -> str:
        return (
            "Generate a personalized LinkedIn outreach message.\n\n"
            f"Profile URL: {request.profile_url}\n\n"
            f"Product / Service:\n{request.product_description}\n\n"
            f"Tone: {request.tone.value}"
        )

    def _dispatch_tool_call(self, tool_call: dict[str, Any]) -> ToolMessage:
        """
        Validate and execute a single tool call from the LLM.

        Returns a ToolMessage containing the JSON-serialized result
        (or a structured error if the call was invalid or the tool failed).
        """
        tool_name: str = tool_call.get("name", "")
        tool_args: dict = tool_call.get("args", {})
        tool_call_id: str = tool_call.get("id", "unknown")

        logger.info("[Agent] Tool call: %s  args_keys=%s", tool_name, list(tool_args.keys()))

        # 1. Unknown tool
        if tool_name not in AVAILABLE_TOOLS:
            logger.warning("[Agent] Unknown tool requested: %s", tool_name)
            result = {
                "success": False,
                "error": {
                    "type": "unknown_tool",
                    "message": (
                        f"Tool '{tool_name}' is not available. "
                        f"Available tools: {list(AVAILABLE_TOOLS.keys())}"
                    ),
                },
            }
            return ToolMessage(
                content=json.dumps(result),
                tool_call_id=tool_call_id,
                name=tool_name,
            )

        # 2. Validate arguments against the tool's Pydantic schema
        schema_cls = _ARG_SCHEMAS.get(tool_name)
        if schema_cls is not None:
            try:
                validated = schema_cls(**tool_args)
                # Use the validated (coerced) args for execution
                exec_args = validated.model_dump()
            except ValidationError as exc:
                logger.warning(
                    "[Agent] Invalid args for tool '%s': %s", tool_name, exc
                )
                result = {
                    "success": False,
                    "error": {
                        "type": "invalid_tool_arguments",
                        "message": str(exc),
                    },
                }
                return ToolMessage(
                    content=json.dumps(result),
                    tool_call_id=tool_call_id,
                    name=tool_name,
                )
        else:
            exec_args = tool_args

        # 3. Execute the tool
        tool_fn = AVAILABLE_TOOLS[tool_name]
        try:
            raw_result = tool_fn(**exec_args)
        except Exception as exc:
            logger.error(
                "[Agent] Tool '%s' raised an unexpected exception: %s",
                tool_name,
                type(exc).__name__,
            )
            raw_result = {
                "success": False,
                "error": {
                    "type": "tool_execution_error",
                    "message": f"Tool '{tool_name}' encountered an error.",
                },
            }

        # 4. Serialize result to JSON for the conversation
        try:
            content = json.dumps(raw_result)
        except (TypeError, ValueError):
            content = json.dumps({"success": False, "error": {"type": "serialization_error"}})

        logger.info(
            "[Tool] %s → %s",
            tool_name,
            "success" if raw_result.get("success") else "error",
        )

        return ToolMessage(
            content=content,
            tool_call_id=tool_call_id,
            name=tool_name,
        )

    @staticmethod
    def _parse_final_response(text: str) -> OutreachMessage:
        """
        Parse the LLM's final text response into an OutreachMessage.

        The LLM is instructed to return valid JSON.  If it doesn't,
        we attempt to extract JSON from the response, then fall back to
        a structured representation.

        Raises:
            AgentError: If the final response cannot be parsed into
                        a valid OutreachMessage.
        """
        if not text or not text.strip():
            raise AgentError("Agent produced an empty final response.")

        # Try direct JSON parse
        try:
            data = json.loads(text.strip())
            return OutreachMessage.model_validate(data)
        except (json.JSONDecodeError, ValidationError):
            pass

        # Try to extract the first JSON object from the text
        import re
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group())
                return OutreachMessage.model_validate(data)
            except (json.JSONDecodeError, ValidationError):
                pass

        # The LLM produced non-JSON text — wrap it into the response model.
        # This is a best-effort fallback for when the LLM doesn't follow the
        # JSON-only instruction.  It will fail Pydantic validation if the text
        # is too short to meet the message field min_length.
        try:
            return OutreachMessage(
                recipient_name="Unknown",
                message=text.strip()[:1000],
                reason_for_outreach="Generated by agent (non-JSON response).",
            )
        except ValidationError as exc:
            raise AgentError(
                f"Agent final response could not be parsed into OutreachMessage: {exc}\n"
                f"Raw response: {text[:200]!r}"
            ) from exc


# ---------------------------------------------------------------------------
# Module-level convenience API (preserves the public interface used by routes)
# ---------------------------------------------------------------------------

_default_agent: OutreachAgent | None = None


def _get_default_agent() -> OutreachAgent:
    """Lazily create the default agent instance."""
    global _default_agent
    if _default_agent is None:
        _default_agent = OutreachAgent()
    return _default_agent


def generate_outreach(request: OutreachRequest) -> OutreachMessage:
    """
    Public entry point — preserves the existing API surface consumed by routes.py.

    Delegates to the OutreachAgent custom loop.

    Args:
        request: Validated OutreachRequest.

    Returns:
        OutreachMessage.

    Raises:
        AgentError, AgentMaxTurnsError on failure.
    """
    return _get_default_agent().run(request)