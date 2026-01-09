"""
Comprehensive unit tests for The Refactoring Swarm tools.

This test suite validates all tool functionality including:
- Sandbox security
- File operations
- Pylint integration
- Pytest integration  
- Code parsing

Run with: pytest tests/test_tools.py -v
"""

import pytest
import tempfile
import shutil
from pathlib import Path

# Import all tools
from src.tools import (
    # Exceptions
    ToolError, SecurityError, FileOpError, AnalysisError, TestError, ParsingError,
    # Sandbox
    SandboxManager, initialize_sandbox, get_sandbox, get_safe_path,
    # File ops
    FileOperations, read_file, write_file, list_python_files,
    # Analysis
    PylintAnalyzer, run_pylint,
    # Testing
    PytestRunner, run_pytest,
    # Parsing
    CodeParser, extract_functions, extract_classes, get_imports
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def temp_sandbox():
    """Create a temporary sandbox directory."""
    temp_dir = tempfile.mkdtemp(prefix="sandbox_test_")
    yield temp_dir
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def sandbox(temp_sandbox):
    """Create a SandboxManager instance."""
    return SandboxManager(temp_sandbox)


@pytest.fixture
def sample_python_file(temp_sandbox):
    """Create a sample Python file in the sandbox."""
    filepath = Path(temp_sandbox) / "sample.py"
    code = '''"""Sample module."""

def hello(name):
    """Greet someone."""
    return f"Hello, {name}!"

class Calculator:
    """Simple calculator."""
    
    def add(self, a, b):
        """Add two numbers."""
        return a + b
'''
    filepath.write_text(code)
    return filepath


@pytest.fixture
def bad_python_file(temp_sandbox):
    """Create a Python file with quality issues."""
    filepath = Path(temp_sandbox) / "bad_code.py"
    code = 'x=1\ny=2\nprint(x+y)'  # No spaces, no docstring
    filepath.write_text(code)
    return filepath


@pytest.fixture
def sample_test_file(temp_sandbox):
    """Create a sample test file."""
    test_dir = Path(temp_sandbox) / "tests"
    test_dir.mkdir()
    test_file = test_dir / "test_sample.py"
    code = '''def test_pass():
    assert 1 + 1 == 2

def test_fail():
    assert 1 + 1 == 3
'''
    test_file.write_text(code)
    return test_dir


# ============================================================================
# SANDBOX TESTS
# ============================================================================

class TestSandboxSecurity:
    """Test sandbox security features."""
    
    def test_sandbox_creation(self, temp_sandbox):
        """Test sandbox directory creation."""
        sandbox = SandboxManager(temp_sandbox)
        assert sandbox.sandbox_root.exists()
        assert sandbox.sandbox_root.is_dir()
    
    def test_path_traversal_blocked(self, sandbox):
        """Test that path traversal is blocked."""
        with pytest.raises(SecurityError):
            sandbox.validate_path("../../etc/passwd")
    
    def test_absolute_path_outside_blocked(self, sandbox):
        """Test that absolute paths outside sandbox are blocked."""
        with pytest.raises(SecurityError):
            sandbox.validate_path("/etc/passwd")
    
    def test_relative_path_allowed(self, sandbox, temp_sandbox):
        """Test that relative paths within sandbox are allowed."""
        safe_path = sandbox.validate_path("code.py")
        assert str(safe_path).startswith(str(temp_sandbox))
    
    def test_is_safe_method(self, sandbox):
        """Test the is_safe convenience method."""
        assert sandbox.is_safe("code.py") is True
        assert sandbox.is_safe("../../etc/passwd") is False
    
    def test_get_safe_path(self, sandbox, temp_sandbox):
        """Test get_safe_path method."""
        safe_path = sandbox.get_safe_path("subfolder/code.py")
        expected = Path(temp_sandbox) / "subfolder" / "code.py"
        assert safe_path == expected.resolve()
    
    def test_list_python_files(self, sandbox, sample_python_file):
        """Test listing Python files."""
        files = sandbox.list_python_files()
        assert len(files) > 0
        assert any(f.name == "sample.py" for f in files)


# ============================================================================
# FILE OPERATIONS TESTS
# ============================================================================

class TestFileOperations:
    """Test file operation functionality."""
    
    def test_read_file_success(self, sandbox, sample_python_file):
        """Test successful file reading."""
        file_ops = FileOperations(sandbox)
        result = file_ops.read_file("sample.py")
        
        assert result.success is True
        assert result.content is not None
        assert "def hello" in result.content
        assert result.metadata["line_count"] > 0
    
    def test_read_nonexistent_file(self, sandbox):
        """Test reading a file that doesn't exist."""
        file_ops = FileOperations(sandbox)
        result = file_ops.read_file("nonexistent.py")
        
        assert result.success is False
        assert result.error is not None