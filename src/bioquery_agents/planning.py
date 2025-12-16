"""
Planning loop for multi-step agent workflows.

Inspired by deepagents TodoListMiddleware.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4


class TodoStatus(Enum):
    """Status of a todo item."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class Todo:
    """A task in the planning loop."""

    id: str
    description: str
    status: TodoStatus = TodoStatus.PENDING
    result: dict[str, Any] | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "description": self.description,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Todo:
        """Create from dictionary."""
        return cls(
            id=data["id"],
            description=data["description"],
            status=TodoStatus(data["status"]),
            result=data.get("result"),
            error=data.get("error"),
            metadata=data.get("metadata", {}),
        )


class PlanningLoop:
    """
    Planning loop for multi-step queries.

    Manages a list of todos that can be:
    - Created from query decomposition
    - Executed sequentially or in parallel
    - Tracked for completion/failure

    Example:
        ```python
        loop = PlanningLoop()
        loop.set_todos([
            "Get TP53 expression in BRCA",
            "Get TP53 expression in LUAD",
            "Compare the two results",
        ])

        while loop.can_continue():
            todo = loop.get_next_pending()
            if not todo:
                break

            loop.mark_in_progress(todo.id)
            try:
                result = await execute_todo(todo)
                loop.mark_complete(todo.id, result)
            except Exception as e:
                loop.mark_failed(todo.id, str(e))
        ```
    """

    def __init__(self, max_iterations: int = 10):
        """
        Initialize planning loop.

        Args:
            max_iterations: Maximum iterations before forced termination
        """
        self.todos: list[Todo] = []
        self.max_iterations: int = max_iterations
        self._iteration: int = 0

    def add_todo(
        self,
        description: str,
        metadata: dict[str, Any] | None = None,
    ) -> Todo:
        """
        Add a new todo.

        Args:
            description: Task description
            metadata: Optional metadata

        Returns:
            Created todo
        """
        todo = Todo(
            id=f"todo_{uuid4().hex[:8]}",
            description=description,
            metadata=metadata or {},
        )
        self.todos.append(todo)
        return todo

    def set_todos(
        self,
        descriptions: list[str],
    ) -> list[Todo]:
        """
        Set multiple todos at once, replacing existing.

        Args:
            descriptions: List of task descriptions

        Returns:
            List of created todos
        """
        self.todos = []
        return [self.add_todo(desc) for desc in descriptions]

    def get_todo(self, todo_id: str) -> Todo | None:
        """Get todo by ID."""
        for todo in self.todos:
            if todo.id == todo_id:
                return todo
        return None

    def get_next_pending(self) -> Todo | None:
        """Get next pending todo."""
        for todo in self.todos:
            if todo.status == TodoStatus.PENDING:
                return todo
        return None

    def get_in_progress(self) -> list[Todo]:
        """Get all in-progress todos."""
        return [t for t in self.todos if t.status == TodoStatus.IN_PROGRESS]

    def mark_in_progress(self, todo_id: str) -> None:
        """Mark todo as in progress."""
        todo = self.get_todo(todo_id)
        if todo:
            todo.status = TodoStatus.IN_PROGRESS

    def mark_complete(
        self,
        todo_id: str,
        result: dict[str, Any] | None = None,
    ) -> None:
        """Mark todo as completed."""
        todo = self.get_todo(todo_id)
        if todo:
            todo.status = TodoStatus.COMPLETED
            todo.result = result

    def mark_failed(self, todo_id: str, error: str) -> None:
        """Mark todo as failed."""
        todo = self.get_todo(todo_id)
        if todo:
            todo.status = TodoStatus.FAILED
            todo.error = error

    def mark_skipped(self, todo_id: str, reason: str | None = None) -> None:
        """Mark todo as skipped."""
        todo = self.get_todo(todo_id)
        if todo:
            todo.status = TodoStatus.SKIPPED
            if reason:
                todo.error = reason

    def all_complete(self) -> bool:
        """Check if all todos are complete (completed, failed, or skipped)."""
        if not self.todos:
            return True
        return all(
            t.status in (TodoStatus.COMPLETED, TodoStatus.FAILED, TodoStatus.SKIPPED)
            for t in self.todos
        )

    def any_failed(self) -> bool:
        """Check if any todos failed."""
        return any(t.status == TodoStatus.FAILED for t in self.todos)

    def can_continue(self) -> bool:
        """
        Check if loop should continue.

        Returns False if:
        - All todos are complete
        - Max iterations reached
        """
        if self._iteration >= self.max_iterations:
            return False
        return not self.all_complete()

    def increment_iteration(self) -> int:
        """Increment iteration counter and return new value."""
        self._iteration += 1
        return self._iteration

    @property
    def iteration(self) -> int:
        """Current iteration count."""
        return self._iteration

    def to_state(self) -> list[dict[str, Any]]:
        """Convert to state representation for serialization."""
        return [t.to_dict() for t in self.todos]

    @classmethod
    def from_state(
        cls,
        state: list[dict[str, Any]],
        max_iterations: int = 10,
    ) -> PlanningLoop:
        """Create from state representation."""
        loop = cls(max_iterations=max_iterations)
        loop.todos = [Todo.from_dict(t) for t in state]
        return loop

    def summary(self) -> dict[str, int]:
        """Get summary of todo statuses."""
        summary = {status.value: 0 for status in TodoStatus}
        for todo in self.todos:
            summary[todo.status.value] += 1
        return summary

    def __len__(self) -> int:
        """Number of todos."""
        return len(self.todos)
