"""
Custom exceptions for the Refactoring Swarm tools.

This module defines all custom exceptions used by the tools layer.
All exceptions inherit from ToolError for easy catching.
"""

from typing import Optional, Dict, Any


class ToolError(Exception):
    """Base exception for all tool-related errors.
    
    All custom exceptions in the tools layer inherit from this class.
    This allows agents to catch all tool errors with a single except clause.
    
    Attributes:
        message: Human-readable error description
        context: Additional context information (file paths, commands, etc.)
    """
    
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Initialize the ToolError.
        
        Args:
            message: Error description
            context: Optional dict with additional error context
        """
        self.message = message
        self.context = context or {}
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging.
        
        Returns:
            Dictionary with error details suitable for JSON serialization
        """
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "context": self.context
        }


class SecurityError(ToolError):
    """Raised when a security violation is detected.
    
    This exception is raised when:
    - Path traversal attempts are detected (../)
    - Attempts to access files outside the sandbox
    - Absolute paths pointing outside allowed directories
    
    Example:
        >>> sandbox.validate_path("../../etc/passwd")
        SecurityError: Path traversal detected
    """
    
    def __init__(self, message: str, attempted_path: Optional[str] = None):
        """Initialize SecurityError.
        
        Args:
            message: Error description
            attempted_path: The path that triggered the security violation
        """
        context = {"attempted_path": attempted_path} if attempted_path else {}
        super().__init__(message, context)


class FileOpError(ToolError):
    """Raised when file operations fail.
    
    This exception is raised when:
    - File not found
    - Permission denied
    - Encoding errors
    - I/O errors during read/write
    
    Example:
        >>> read_file("nonexistent.py")
        FileOpError: File not found: nonexistent.py
    """
    
    def __init__(self, message: str, filepath: Optional[str] = None, 
                 original_error: Optional[Exception] = None):
        """Initialize FileOpError.
        
        Args:
            message: Error description
            filepath: The file that caused the error
            original_error: The underlying exception that was caught
        """
        context = {}
        if filepath:
            context["filepath"] = filepath
        if original_error:
            context["original_error"] = str(original_error)
            context["error_type"] = type(original_error).__name__
        super().__init__(message, context)


class AnalysisError(ToolError):
    """Raised when static analysis tools fail.
    
    This exception is raised when:
    - Pylint execution fails
    - Output parsing fails
    - Timeout occurs
    - Invalid configuration
    
    Example:
        >>> run_pylint("invalid.py")
        AnalysisError: Pylint execution timeout after 30s
    """
    
    def __init__(self, message: str, tool: Optional[str] = None, 
                 command: Optional[str] = None):
        """Initialize AnalysisError.
        
        Args:
            message: Error description
            tool: Name of the analysis tool (e.g., "pylint")
            command: The command that failed
        """
        context = {}
        if tool:
            context["tool"] = tool
        if command:
            context["command"] = command
        super().__init__(message, context)


class TestError(ToolError):
    """Raised when test execution fails.
    
    This exception is raised when:
    - Pytest execution fails
    - Test result parsing fails
    - Timeout occurs
    - Test directory not found
    
    Example:
        >>> run_pytest("nonexistent_tests/")
        TestError: Test directory not found
    """
    
    def __init__(self, message: str, test_path: Optional[str] = None,
                 command: Optional[str] = None):
        """Initialize TestError.
        
        Args:
            message: Error description
            test_path: Path to tests that failed
            command: The pytest command that failed
        """
        context = {}
        if test_path:
            context["test_path"] = test_path
        if command:
            context["command"] = command
        super().__init__(message, context)


class ParsingError(ToolError):
    """Raised when code parsing fails.
    
    This exception is raised when:
    - AST parsing fails (syntax errors)
    - Invalid Python code
    - Encoding issues
    
    Example:
        >>> extract_functions("bad syntax here")
        ParsingError: Failed to parse Python code
    """
    
    def __init__(self, message: str, code_snippet: Optional[str] = None,
                 line_number: Optional[int] = None):
        """Initialize ParsingError.
        
        Args:
            message: Error description
            code_snippet: The code that failed to parse
            line_number: Line number where parsing failed
        """
        context = {}
        if code_snippet:
            # Truncate long snippets
            context["code_snippet"] = code_snippet[:200] + "..." if len(code_snippet) > 200 else code_snippet
        if line_number:
            context["line_number"] = line_number
        super().__init__(message, context)
