"""Unit tests for DependencyChecker."""

from __future__ import annotations

import pytest

from pdf_tool.exceptions import MissingDependencyError
from pdf_tool.utils.dependency_checker import (
    DependencyStatus,
    check,
    check_all,
    verify,
)


class TestCheck:
    def test_known_present_binary(self) -> None:
        """python3 (or python) should be found on any system running these tests."""
        import sys

        binary = "python3" if sys.platform != "win32" else "python"
        status = check(binary)
        assert isinstance(status, DependencyStatus)
        assert status.name == binary
        assert status.found is True
        assert status.path is not None

    def test_nonexistent_binary(self) -> None:
        """A clearly fake binary should not be found."""
        status = check("nonexistent_binary_xyz_12345")
        assert isinstance(status, DependencyStatus)
        assert status.found is False
        assert status.path is None

    def test_returns_dataclass(self) -> None:
        """check() must return a DependencyStatus dataclass."""
        status = check("python3")
        assert hasattr(status, "name")
        assert hasattr(status, "found")
        assert hasattr(status, "path")


class TestCheckAll:
    def test_returns_list(self) -> None:
        statuses = check_all(["python3", "nonexistent_xyz"])
        assert len(statuses) == 2
        assert all(isinstance(s, DependencyStatus) for s in statuses)

    def test_does_not_raise_on_missing(self) -> None:
        """check_all should NOT raise even if a binary is missing."""
        result = check_all(["nonexistent_abc_123"])
        assert result[0].found is False


class TestVerify:
    def test_verify_present_binary_does_not_raise(self) -> None:
        """Verifying a present binary should not raise."""
        verify(["python3"])  # Should not raise

    def test_verify_missing_binary_raises(self) -> None:
        """Verifying a missing binary should raise MissingDependencyError."""
        with pytest.raises(MissingDependencyError) as exc_info:
            verify(["nonexistent_binary_xyz_99"])
        assert exc_info.value.dep_name == "nonexistent_binary_xyz_99"

    def test_missing_dependency_error_has_dep_name(self) -> None:
        err = MissingDependencyError("gs", {"macos": "brew install ghostscript"})
        assert err.dep_name == "gs"
        assert "gs" in str(err)
        assert err.install_hints["macos"] == "brew install ghostscript"
