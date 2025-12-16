"""Tests for PlanningLoop."""

from bioquery_agents import PlanningLoop, Todo, TodoStatus


class TestTodo:
    """Tests for Todo dataclass."""

    def test_to_dict(self):
        """Test serialization to dict."""
        todo = Todo(
            id="todo-1",
            description="Test task",
            status=TodoStatus.COMPLETED,
            result={"key": "value"},
        )

        data = todo.to_dict()

        assert data["id"] == "todo-1"
        assert data["description"] == "Test task"
        assert data["status"] == "completed"
        assert data["result"] == {"key": "value"}

    def test_from_dict(self):
        """Test deserialization from dict."""
        data = {
            "id": "todo-1",
            "description": "Test task",
            "status": "in_progress",
            "result": None,
            "error": None,
            "metadata": {"priority": "high"},
        }

        todo = Todo.from_dict(data)

        assert todo.id == "todo-1"
        assert todo.description == "Test task"
        assert todo.status == TodoStatus.IN_PROGRESS
        assert todo.metadata == {"priority": "high"}


class TestPlanningLoop:
    """Tests for PlanningLoop class."""

    def test_add_todo(self):
        """Test adding a todo."""
        loop = PlanningLoop()
        todo = loop.add_todo("Test task")

        assert todo.description == "Test task"
        assert todo.status == TodoStatus.PENDING
        assert len(loop) == 1

    def test_set_todos(self):
        """Test setting multiple todos."""
        loop = PlanningLoop()
        todos = loop.set_todos(["Task 1", "Task 2", "Task 3"])

        assert len(todos) == 3
        assert len(loop) == 3
        assert all(t.status == TodoStatus.PENDING for t in todos)

    def test_set_todos_replaces_existing(self):
        """Test that set_todos replaces existing todos."""
        loop = PlanningLoop()
        loop.add_todo("Old task")
        loop.set_todos(["New task"])

        assert len(loop) == 1
        assert loop.todos[0].description == "New task"

    def test_get_todo(self):
        """Test getting todo by ID."""
        loop = PlanningLoop()
        todo = loop.add_todo("Test task")

        found = loop.get_todo(todo.id)
        assert found is todo

        not_found = loop.get_todo("nonexistent")
        assert not_found is None

    def test_get_next_pending(self):
        """Test getting next pending todo."""
        loop = PlanningLoop()
        loop.set_todos(["Task 1", "Task 2"])

        first = loop.get_next_pending()
        assert first.description == "Task 1"

        loop.mark_complete(first.id)
        second = loop.get_next_pending()
        assert second.description == "Task 2"

        loop.mark_complete(second.id)
        none = loop.get_next_pending()
        assert none is None

    def test_mark_transitions(self):
        """Test status transitions."""
        loop = PlanningLoop()
        todo = loop.add_todo("Test task")

        loop.mark_in_progress(todo.id)
        assert todo.status == TodoStatus.IN_PROGRESS

        loop.mark_complete(todo.id, {"output": "done"})
        assert todo.status == TodoStatus.COMPLETED
        assert todo.result == {"output": "done"}

    def test_mark_failed(self):
        """Test marking as failed."""
        loop = PlanningLoop()
        todo = loop.add_todo("Test task")

        loop.mark_failed(todo.id, "Something went wrong")
        assert todo.status == TodoStatus.FAILED
        assert todo.error == "Something went wrong"

    def test_mark_skipped(self):
        """Test marking as skipped."""
        loop = PlanningLoop()
        todo = loop.add_todo("Test task")

        loop.mark_skipped(todo.id, "Not needed")
        assert todo.status == TodoStatus.SKIPPED
        assert todo.error == "Not needed"

    def test_all_complete(self):
        """Test all_complete check."""
        loop = PlanningLoop()
        loop.set_todos(["Task 1", "Task 2"])

        assert not loop.all_complete()

        loop.mark_complete(loop.todos[0].id)
        assert not loop.all_complete()

        loop.mark_failed(loop.todos[1].id, "error")
        assert loop.all_complete()  # Failed counts as complete

    def test_any_failed(self):
        """Test any_failed check."""
        loop = PlanningLoop()
        loop.set_todos(["Task 1", "Task 2"])

        assert not loop.any_failed()

        loop.mark_failed(loop.todos[0].id, "error")
        assert loop.any_failed()

    def test_can_continue(self):
        """Test can_continue logic."""
        loop = PlanningLoop(max_iterations=3)
        loop.add_todo("Test task")

        assert loop.can_continue()

        loop.mark_complete(loop.todos[0].id)
        assert not loop.can_continue()  # All complete

    def test_can_continue_max_iterations(self):
        """Test max iterations limit."""
        loop = PlanningLoop(max_iterations=2)
        loop.add_todo("Infinite task")  # Never completed

        assert loop.can_continue()
        loop.increment_iteration()
        assert loop.can_continue()
        loop.increment_iteration()
        assert not loop.can_continue()  # Max reached

    def test_to_state(self):
        """Test serialization to state."""
        loop = PlanningLoop()
        loop.set_todos(["Task 1", "Task 2"])
        loop.mark_complete(loop.todos[0].id, {"result": 1})

        state = loop.to_state()

        assert len(state) == 2
        assert state[0]["status"] == "completed"
        assert state[1]["status"] == "pending"

    def test_from_state(self):
        """Test deserialization from state."""
        state = [
            {"id": "todo-1", "description": "Task 1", "status": "completed", "result": {"x": 1}},
            {"id": "todo-2", "description": "Task 2", "status": "pending"},
        ]

        loop = PlanningLoop.from_state(state)

        assert len(loop) == 2
        assert loop.todos[0].status == TodoStatus.COMPLETED
        assert loop.todos[1].status == TodoStatus.PENDING

    def test_summary(self):
        """Test summary generation."""
        loop = PlanningLoop()
        loop.set_todos(["T1", "T2", "T3", "T4"])
        loop.mark_complete(loop.todos[0].id)
        loop.mark_failed(loop.todos[1].id, "error")
        loop.mark_in_progress(loop.todos[2].id)

        summary = loop.summary()

        assert summary["completed"] == 1
        assert summary["failed"] == 1
        assert summary["in_progress"] == 1
        assert summary["pending"] == 1

    def test_get_in_progress(self):
        """Test getting in-progress todos."""
        loop = PlanningLoop()
        loop.set_todos(["T1", "T2", "T3"])
        loop.mark_in_progress(loop.todos[0].id)
        loop.mark_in_progress(loop.todos[2].id)

        in_progress = loop.get_in_progress()

        assert len(in_progress) == 2
        assert all(t.status == TodoStatus.IN_PROGRESS for t in in_progress)
