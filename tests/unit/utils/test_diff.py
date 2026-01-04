"""Unit tests for diff utility."""

from adw.utils.diff import DiffResult, json_diff


class TestDiffResult:
    """Tests for DiffResult class."""

    def test_empty_result_is_falsy(self) -> None:
        """Empty diff result is falsy."""
        result = DiffResult()
        assert not result

    def test_result_with_changes_is_truthy(self) -> None:
        """Diff result with changes is truthy."""
        result = DiffResult()
        result.added["key"] = "value"
        assert result

    def test_repr(self) -> None:
        """Repr shows counts."""
        result = DiffResult()
        result.added["a"] = 1
        result.removed["b"] = 2
        result.changed["c"] = (3, 4)
        assert "added=1" in repr(result)
        assert "removed=1" in repr(result)
        assert "changed=1" in repr(result)

    def test_to_changes_list(self) -> None:
        """Converts to list of tuples."""
        result = DiffResult()
        result.added["b"] = 2
        result.removed["a"] = 1
        result.changed["c"] = (3, 4)

        changes = result.to_changes_list()
        assert len(changes) == 3

        # Check types
        types = [c[0] for c in changes]
        assert "+" in types
        assert "-" in types
        assert "~" in types


class TestJsonDiff:
    """Tests for json_diff function."""

    def test_identical_dicts(self) -> None:
        """No differences for identical dicts."""
        old = {"a": 1, "b": 2}
        new = {"a": 1, "b": 2}
        result = json_diff(old, new)
        assert not result

    def test_addition(self) -> None:
        """Detects added keys."""
        old = {"a": 1}
        new = {"a": 1, "b": 2}
        result = json_diff(old, new)
        assert "b" in result.added
        assert result.added["b"] == 2

    def test_removal(self) -> None:
        """Detects removed keys."""
        old = {"a": 1, "b": 2}
        new = {"a": 1}
        result = json_diff(old, new)
        assert "b" in result.removed
        assert result.removed["b"] == 2

    def test_change(self) -> None:
        """Detects changed values."""
        old = {"a": 1}
        new = {"a": 2}
        result = json_diff(old, new)
        assert "a" in result.changed
        assert result.changed["a"] == (1, 2)

    def test_nested_dict_addition(self) -> None:
        """Detects additions in nested dicts."""
        old = {"outer": {"a": 1}}
        new = {"outer": {"a": 1, "b": 2}}
        result = json_diff(old, new)
        assert "outer.b" in result.added

    def test_nested_dict_removal(self) -> None:
        """Detects removals in nested dicts."""
        old = {"outer": {"a": 1, "b": 2}}
        new = {"outer": {"a": 1}}
        result = json_diff(old, new)
        assert "outer.b" in result.removed

    def test_nested_dict_change(self) -> None:
        """Detects changes in nested dicts."""
        old = {"outer": {"inner": 1}}
        new = {"outer": {"inner": 2}}
        result = json_diff(old, new)
        assert "outer.inner" in result.changed
        assert result.changed["outer.inner"] == (1, 2)

    def test_array_element_added(self) -> None:
        """Detects added array elements."""
        old = {"items": [1, 2]}
        new = {"items": [1, 2, 3]}
        result = json_diff(old, new)
        assert "items[2]" in result.added
        assert result.added["items[2]"] == 3

    def test_array_element_removed(self) -> None:
        """Detects removed array elements."""
        old = {"items": [1, 2, 3]}
        new = {"items": [1, 2]}
        result = json_diff(old, new)
        assert "items[2]" in result.removed

    def test_array_element_changed(self) -> None:
        """Detects changed array elements."""
        old = {"items": [1, 2, 3]}
        new = {"items": [1, 5, 3]}
        result = json_diff(old, new)
        assert "items[1]" in result.changed
        assert result.changed["items[1]"] == (2, 5)

    def test_nested_array_of_dicts(self) -> None:
        """Handles arrays of dicts."""
        old = {"items": [{"id": 1, "name": "old"}]}
        new = {"items": [{"id": 1, "name": "new"}]}
        result = json_diff(old, new)
        assert "items[0].name" in result.changed
        assert result.changed["items[0].name"] == ("old", "new")

    def test_complex_nested_structure(self) -> None:
        """Handles complex nested structures."""
        old = {
            "run_id": "123",
            "phases": {
                "plan": {"status": "complete"},
                "build": {"status": "running"},
            },
            "errors": [],
        }
        new = {
            "run_id": "123",
            "phases": {
                "plan": {"status": "complete"},
                "build": {"status": "complete"},
            },
            "errors": ["timeout"],
        }
        result = json_diff(old, new)

        # Build status changed
        assert "phases.build.status" in result.changed

        # Error added
        assert "errors[0]" in result.added

    def test_empty_dicts(self) -> None:
        """Handles empty dicts."""
        result = json_diff({}, {})
        assert not result

    def test_one_empty_dict(self) -> None:
        """Handles one empty dict."""
        result = json_diff({}, {"a": 1})
        assert "a" in result.added

        result = json_diff({"a": 1}, {})
        assert "a" in result.removed
