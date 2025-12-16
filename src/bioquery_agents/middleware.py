"""
Middleware base class for agent composition.

Inspired by deepagents middleware pattern.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


class AgentMiddleware:
    """
    Base class for agent middleware.

    Middleware can:
    - Add tools to the agent
    - Inject system prompt text
    - Intercept pre/post invocation
    - Handle tool calls

    Example:
        ```python
        class LoggingMiddleware(AgentMiddleware):
            async def pre_invoke(self, state: dict) -> dict:
                print(f"Starting with state keys: {state.keys()}")
                return state

            async def post_invoke(self, state: dict) -> dict:
                print(f"Finished with status: {state.get('_node_status')}")
                return state
        ```
    """

    @property
    def tools(self) -> list[Callable[..., Any]]:
        """
        Tools this middleware provides.

        Override to add tools that get registered with the agent.
        """
        return []

    @property
    def system_prompt_addition(self) -> str:
        """
        Additional system prompt text.

        Override to inject context into the agent's system prompt.
        """
        return ""

    async def pre_invoke(self, state: dict[str, Any]) -> dict[str, Any]:
        """
        Called before agent invocation.

        Override to modify state before processing.
        """
        return state

    async def post_invoke(self, state: dict[str, Any]) -> dict[str, Any]:
        """
        Called after agent invocation.

        Override to modify state after processing.
        """
        return state

    async def pre_tool_call(
        self,
        tool_name: str,
        args: dict[str, Any],
    ) -> dict[str, Any] | None:
        """
        Called before a tool is executed.

        Override to intercept tool calls. Return None to proceed,
        or return a dict to interrupt (e.g., for human-in-the-loop).
        """
        return None

    async def post_tool_call(
        self,
        tool_name: str,
        args: dict[str, Any],
        result: Any,
    ) -> Any:
        """
        Called after a tool is executed.

        Override to process or modify tool results.
        """
        return result


class MiddlewareStack:
    """
    Stack of middleware to apply to an agent.

    Middleware is applied in order for pre_* hooks and
    reverse order for post_* hooks.
    """

    def __init__(self, middlewares: list[AgentMiddleware] | None = None):
        self._middlewares = middlewares or []

    def add(self, middleware: AgentMiddleware) -> None:
        """Add middleware to the stack."""
        self._middlewares.append(middleware)

    @property
    def tools(self) -> list[Callable[..., Any]]:
        """Collect tools from all middleware."""
        all_tools = []
        for mw in self._middlewares:
            all_tools.extend(mw.tools)
        return all_tools

    @property
    def system_prompt_additions(self) -> str:
        """Collect system prompt additions from all middleware."""
        additions = []
        for mw in self._middlewares:
            if mw.system_prompt_addition:
                additions.append(mw.system_prompt_addition)
        return "\n\n".join(additions)

    async def apply_pre_invoke(self, state: dict[str, Any]) -> dict[str, Any]:
        """Apply pre_invoke hooks in order."""
        for mw in self._middlewares:
            state = await mw.pre_invoke(state)
        return state

    async def apply_post_invoke(self, state: dict[str, Any]) -> dict[str, Any]:
        """Apply post_invoke hooks in reverse order."""
        for mw in reversed(self._middlewares):
            state = await mw.post_invoke(state)
        return state

    async def apply_pre_tool_call(
        self,
        tool_name: str,
        args: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Apply pre_tool_call hooks. Return first non-None result."""
        for mw in self._middlewares:
            result = await mw.pre_tool_call(tool_name, args)
            if result is not None:
                return result
        return None

    async def apply_post_tool_call(
        self,
        tool_name: str,
        args: dict[str, Any],
        result: Any,
    ) -> Any:
        """Apply post_tool_call hooks in reverse order."""
        for mw in reversed(self._middlewares):
            result = await mw.post_tool_call(tool_name, args, result)
        return result
