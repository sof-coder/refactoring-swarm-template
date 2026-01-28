"""
Public API for The Refactoring Swarm Tools.

This module exports all tools needed by agents. Import only from this module,
never from submodules directly.

Example Usage:
    >>> from src.tools import initialize_sandbox, run_pylint, run_pytest
    >>> 
    >>> # Initialize sandbox at start of application
    >>> sandbox = initialize_sandbox("./sandbox")
    >>> 
    >>> # Use tools
    >>> analysis = run_pylint("code.py")
    >>> print(f"Quality score: {analysis.score}/10")
    >>> 
    >>> test_result = run_pytest("tests/")
    >>> if test_result.all_tests_passed:
    ...     print("All tests passed!")

Module Organization:
    - Exceptions: Custom error types
    - Sandbox: Security and path validation
    - File Operations: Safe file I/O
    - Analysis: Pylint integration
    - Testing: Pytest integration
    - Parsing: AST-based code parsing
"""

# ============================================================================
# EXCEPTIONS
# ============================================================================
from .exceptions import (
    ToolError,
    SecurityError,
    FileOpError,
    AnalysisError,
    TestError,
    ParsingError
)

# ============================================================================
# SANDBOX & SECURITY
# ============================================================================
from .sandbox import (
    SandboxManager,
    initialize_sandbox,
    get_sandbox,
    get_safe_path
)

# ============================================================================
# FILE OPERATIONS
# ============================================================================
from .file_ops import (
    FileOperations,
    FileOperationResult,
    read_file,
    write_file,
    list_python_files
)

# ============================================================================
# STATIC ANALYSIS (PYLINT)
# ============================================================================
from .analyzer import (
    PylintAnalyzer,
    AnalysisResult,
    Issue,
    run_pylint,
    get_quality_score,
)

# ============================================================================
# TESTING (PYTEST)
# ============================================================================
from .tester import (
    PytestRunner,
    TestResult,
    FailedTest,
    run_pytest,
    get_test_status
)

# ============================================================================
# CODE PARSING
# ============================================================================
from .parser import (
    CodeParser,
    FunctionInfo,
    ClassInfo,
    ImportInfo,
    CodeMetrics,
    extract_functions,
    extract_classes,
    get_imports
)

# ============================================================================
# CODE FIXING
# ============================================================================
from .function_fixer import (
    FunctionFixer,
    FixResult,
    FixedIssue,
    fix_code
)


# ============================================================================
# PUBLIC API EXPORTS
# ============================================================================
__all__ = [
    # Exceptions
    'ToolError',
    'SecurityError',
    'FileOpError',
    'AnalysisError',
    'TestError',
    'ParsingError',
    
    # Sandbox (Core)
    'SandboxManager',
    'initialize_sandbox',
    'get_sandbox',
    'get_safe_path',
    
    # File Operations
    'FileOperations',
    'FileOperationResult',
    'read_file',
    'write_file',
    'list_python_files',
    
    # Analysis (Pylint)
    'PylintAnalyzer',
    'AnalysisResult',
    'Issue',
    'run_pylint',
    'get_quality_score',
    'extract_issues',  # Add this
    
    # Testing (Pytest)
    'PytestRunner',
    'TestResult',
    'FailedTest',
    'run_pytest',
    'get_test_status',
    
    # Parsing
    'CodeParser',
    'FunctionInfo',
    'ClassInfo',
    'ImportInfo',
    'CodeMetrics',
    'extract_functions',
    'extract_classes',
    'get_imports',
    
    # Code Fixing
    'FunctionFixer',
    'FixResult',
    'FixedIssue',
    'fix_code',
]


# ============================================================================
# VERSION INFO
# ============================================================================
__version__ = '1.0.0'
__author__ = 'The Refactoring Swarm - Toolsmith'
__description__ = 'Autonomous code refactoring tools for LLM agents'


# ============================================================================
# QUICK START HELPER
# ============================================================================
def quick_start(sandbox_path: str = "./sandbox"):
    """Quick start helper for interactive sessions.
    
    Initializes the sandbox and returns commonly used tools.
    
    Args:
        sandbox_path: Path to sandbox directory (default: ./sandbox)
        
    Returns:
        Dictionary with initialized tools
        
    Example:
        >>> from src.tools import quick_start
        >>> tools = quick_start()
        >>> result = tools['analyze']("code.py")
        >>> print(result.score)
    """
    sandbox = initialize_sandbox(sandbox_path)
    
    return {
        'sandbox': sandbox,
        'read_file': lambda path: read_file(path, sandbox),
        'write_file': lambda path, content: write_file(path, content, sandbox),
        'analyze': lambda path: run_pylint(path, sandbox),
        'test': lambda path: run_pytest(path, sandbox),
        'parse': lambda path: CodeParser(sandbox).parse_file(path),
        'extract_functions': lambda path: extract_functions(path, sandbox),
        'extract_classes': lambda path: extract_classes(path, sandbox),
        'fix_code': lambda code, issues: fix_code(code, issues, sandbox),
    }
