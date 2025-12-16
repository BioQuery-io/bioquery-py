"""Tests for AgentMiddleware."""

import pytest

from bioquery_agents import AgentMiddleware
from bioquery_agents.middleware import MiddlewareStack


class SampleMiddleware(AgentMiddleware):
    """Sample middleware implementation for testing."""

    def __init__(self, name: str):
        self.name = name
        self.pre_invoke_called = False
        self.post_invoke_called = False

    @property
    def system_prompt_addition(self) -> str:
        return f"Addition from {self.name}"

    async def pre_invoke(self, state: dict) -> dict:
        self.pre_invoke_called = True
        state[f"pre_{self.name}"] = True
        return state

    async def post_invoke(self, state: dict) -> dict:
        self.post_invoke_called = True
        state[f"post_{self.name}"] = True
        return state


class InterruptMiddleware(AgentMiddleware):
    """Middleware that interrupts on specific tools."""

    def __init__(self, interrupt_tools: list[str]):
        self.interrupt_tools = interrupt_tools

    async def pre_tool_call(self, tool_name: str, args: dict) -> dict | None:
        if tool_name in self.interrupt_tools:
            return {"__interrupt__": True, "tool": tool_name}
        return None


class TestAgentMiddleware:
    """Tests for AgentMiddleware base class."""

    @pytest.mark.asyncio
    async def test_default_implementations(self):
        """Test default method implementations."""
        mw = AgentMiddleware()

        assert mw.tools == []
        assert mw.system_prompt_addition == ""

        state = {"key": "value"}
        assert await mw.pre_invoke(state) == state
        assert await mw.post_invoke(state) == state
        assert await mw.pre_tool_call("test", {}) is None
        assert await mw.post_tool_call("test", {}, "result") == "result"


class TestMiddlewareStack:
    """Tests for MiddlewareStack class."""

    def test_add_middleware(self):
        """Test adding middleware to stack."""
        stack = MiddlewareStack()
        mw = SampleMiddleware("test")
        stack.add(mw)

        assert len(stack._middlewares) == 1

    def test_system_prompt_additions(self):
        """Test collecting system prompt additions."""
        stack = MiddlewareStack(
            [
                SampleMiddleware("a"),
                SampleMiddleware("b"),
            ]
        )

        additions = stack.system_prompt_additions
        assert "Addition from a" in additions
        assert "Addition from b" in additions

    @pytest.mark.asyncio
    async def test_apply_pre_invoke(self):
        """Test pre_invoke is applied in order."""
        mw1 = SampleMiddleware("first")
        mw2 = SampleMiddleware("second")
        stack = MiddlewareStack([mw1, mw2])

        state = await stack.apply_pre_invoke({})

        assert mw1.pre_invoke_called
        assert mw2.pre_invoke_called
        assert state["pre_first"] is True
        assert state["pre_second"] is True

    @pytest.mark.asyncio
    async def test_apply_post_invoke(self):
        """Test post_invoke is applied in reverse order."""
        mw1 = SampleMiddleware("first")
        mw2 = SampleMiddleware("second")
        stack = MiddlewareStack([mw1, mw2])

        state = await stack.apply_post_invoke({})

        assert mw1.post_invoke_called
        assert mw2.post_invoke_called
        assert state["post_first"] is True
        assert state["post_second"] is True

    @pytest.mark.asyncio
    async def test_apply_pre_tool_call(self):
        """Test pre_tool_call returns first non-None result."""
        mw1 = InterruptMiddleware(["dangerous_tool"])
        mw2 = InterruptMiddleware(["other_tool"])
        stack = MiddlewareStack([mw1, mw2])

        # Should interrupt
        result = await stack.apply_pre_tool_call("dangerous_tool", {})
        assert result is not None
        assert result["__interrupt__"] is True

        # Should not interrupt
        result = await stack.apply_pre_tool_call("safe_tool", {})
        assert result is None

    @pytest.mark.asyncio
    async def test_apply_post_tool_call(self):
        """Test post_tool_call transforms result."""

        class TransformMiddleware(AgentMiddleware):
            async def post_tool_call(self, tool_name: str, args: dict, result):
                if isinstance(result, int):
                    return result * 2
                return result

        stack = MiddlewareStack([TransformMiddleware(), TransformMiddleware()])

        # Should double twice
        result = await stack.apply_post_tool_call("test", {}, 5)
        assert result == 20  # 5 * 2 * 2

    def test_collect_tools(self):
        """Test collecting tools from middleware."""

        def tool_a():
            pass

        def tool_b():
            pass

        class ToolMiddleware(AgentMiddleware):
            def __init__(self, tools: list):
                self._tools = tools

            @property
            def tools(self):
                return self._tools

        stack = MiddlewareStack(
            [
                ToolMiddleware([tool_a]),
                ToolMiddleware([tool_b]),
            ]
        )

        all_tools = stack.tools
        assert tool_a in all_tools
        assert tool_b in all_tools
