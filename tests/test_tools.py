"""Tests for tools module."""

import pytest
from pathlib import Path
import tempfile
from src.tools import initialize_sandbox, SecurityError


class TestSandbox:
    """Test sandbox security."""
    
    def test_path_traversal_blocked(self):
        """Test that path traversal is blocked."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sandbox = initialize_sandbox(tmpdir)
            with pytest.raises(SecurityError):
                sandbox.validate_path("../../etc/passwd")
