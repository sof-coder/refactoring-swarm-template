"""
Code parsing utilities for The Refactoring Swarm.

This module provides Python AST (Abstract Syntax Tree) parsing functionality
to extract code structure information without executing the code.

Features:
- Extract function definitions
- Extract class definitions
- List imports
- Detect syntax errors
- Get code metrics
"""

import ast
from pathlib import Path
from typing import Union, Optional, List, Dict, Any
from dataclasses import dataclass, field

from .exceptions import ParsingError, SecurityError
from .sandbox import SandboxManager
from .file_ops import read_file


@dataclass
class FunctionInfo:
    """Information about a function definition.
    
    Attributes:
        name: Function name
        line_number: Line where function is defined
        parameters: List of parameter names
        has_docstring: Whether function has a docstring
        is_async: Whether it's an async function
        decorators: List of decorator names
    """
    name: str
    line_number: int
    parameters: List[str] = field(default_factory=list)
    has_docstring: bool = False
    is_async: bool = False
    decorators: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "line_number": self.line_number,
            "parameters": self.parameters,
            "has_docstring": self.has_docstring,
            "is_async": self.is_async,
            "decorators": self.decorators
        }


@dataclass
class ClassInfo:
    """Information about a class definition.
    
    Attributes:
        name: Class name
        line_number: Line where class is defined
        base_classes: List of base class names
        methods: List of method names
        has_docstring: Whether class has a docstring
    """
    name: str
    line_number: int
    base_classes: List[str] = field(default_factory=list)
    methods: List[str] = field(default_factory=list)
    has_docstring: bool = False
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "line_number": self.line_number,
            "base_classes": self.base_classes,
            "methods": self.methods,
            "has_docstring": self.has_docstring
        }


@dataclass
class ImportInfo:
    """Information about an import statement.
    
    Attributes:
        module: Module name (e.g., 'os', 'sys')
        names: Imported names (e.g., ['path', 'join'] for 'from os import path, join')
        alias: Import alias (e.g., 'np' for 'import numpy as np')
        line_number: Line where import occurs
        is_from_import: Whether it's a 'from X import Y' statement
    """
    module: str
    line_number: int
    names: List[str] = field(default_factory=list)
    alias: Optional[str] = None
    is_from_import: bool = False
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "module": self.module,
            "line_number": self.line_number,
            "names": self.names,
            "alias": self.alias,
            "is_from_import": self.is_from_import
        }


@dataclass
class CodeMetrics:
    """Code complexity metrics.
    
    Attributes:
        total_lines: Total line count
        code_lines: Non-empty, non-comment lines
        comment_lines: Comment line count
        function_count: Number of functions
        class_count: Number of classes
        import_count: Number of import statements
        max_line_length: Longest line length
    """
    total_lines: int = 0
    code_lines: int = 0
    comment_lines: int = 0
    function_count: int = 0
    class_count: int = 0
    import_count: int = 0
    max_line_length: int = 0
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "total_lines": self.total_lines,
            "code_lines": self.code_lines,
            "comment_lines": self.comment_lines,
            "function_count": self.function_count,
            "class_count": self.class_count,
            "import_count": self.import_count,
            "max_line_length": self.max_line_length
        }


class CodeParser:
    """Python code parser using AST.
    
    This class parses Python code and extracts structural information
    without executing the code.
    
    Example:
        >>> parser = CodeParser(sandbox)
        >>> functions = parser.extract_functions("code.py")
        >>> for func in functions:
        ...     print(f"{func.name} at line {func.line_number}")
    """
    
    def __init__(self, sandbox: SandboxManager):
        """Initialize CodeParser.
        
        Args:
            sandbox: SandboxManager for path validation
        """
        self._sandbox = sandbox
    
    def parse_file(self, filepath: Union[str, Path]) -> Optional[ast.Module]:
        """Parse a Python file into an AST.
        
        Args:
            filepath: Path to Python file
            
        Returns:
            AST Module object, or None if parsing fails
            
        Raises:
            ParsingError: If file cannot be parsed
        """
        try:
            # Read file
            result = read_file(filepath, self._sandbox)
            if not result.success:
                raise ParsingError(
                    f"Failed to read file: {result.error}",
                    code_snippet=None
                )
            
            # Parse AST
            tree = ast.parse(result.content, filename=str(filepath))
            return tree
            
        except SyntaxError as e:
            raise ParsingError(
                f"Syntax error: {e.msg}",
                code_snippet=result.content[:200] if result.content else None,
                line_number=e.lineno
            )
        except Exception as e:
            raise ParsingError(
                f"Failed to parse: {str(e)}",
                code_snippet=None
            )
    
    def extract_functions(self, filepath: Union[str, Path]) -> List[FunctionInfo]:
        """Extract all function definitions from a file.
        
        Args:
            filepath: Path to Python file
            
        Returns:
            List of FunctionInfo objects
            
        Example:
            >>> functions = parser.extract_functions("code.py")
            >>> print(f"Found {len(functions)} functions")
        """
        try:
            tree = self.parse_file(filepath)
            if tree is None:
                return []
            
            functions: List[FunctionInfo] = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                    # Extract parameters
                    params = [arg.arg for arg in node.args.args]
                    
                    # Check for docstring
                    has_docstring = (
                        len(node.body) > 0 and
                        isinstance(node.body[0], ast.Expr) and
                        isinstance(node.body[0].value, ast.Constant) and
                        isinstance(node.body[0].value.value, str)
                    )
                    
                    # Extract decorators
                    decorators = []
                    for dec in node.decorator_list:
                        if isinstance(dec, ast.Name):
                            decorators.append(dec.id)
                        elif isinstance(dec, ast.Call) and isinstance(dec.func, ast.Name):
                            decorators.append(dec.func.id)
                    
                    func_info = FunctionInfo(
                        name=node.name,
                        line_number=node.lineno,
                        parameters=params,
                        has_docstring=has_docstring,
                        is_async=isinstance(node, ast.AsyncFunctionDef),
                        decorators=decorators
                    )
                    functions.append(func_info)
            
            return functions
            
        except ParsingError:
            raise
        except Exception as e:
            raise ParsingError(f"Failed to extract functions: {str(e)}")
    
    def extract_classes(self, filepath: Union[str, Path]) -> List[ClassInfo]:
        """Extract all class definitions from a file.
        
        Args:
            filepath: Path to Python file
            
        Returns:
            List of ClassInfo objects
            
        Example:
            >>> classes = parser.extract_classes("code.py")
            >>> for cls in classes:
            ...     print(f"Class {cls.name} with {len(cls.methods)} methods")
        """
        try:
            tree = self.parse_file(filepath)
            if tree is None:
                return []
            
            classes: List[ClassInfo] = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Extract base classes
                    base_classes = []
                    for base in node.bases:
                        if isinstance(base, ast.Name):
                            base_classes.append(base.id)
                        elif isinstance(base, ast.Attribute):
                            base_classes.append(base.attr)
                    
                    # Extract methods
                    methods = []
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            methods.append(item.name)
                    
                    # Check for docstring
                    has_docstring = (
                        len(node.body) > 0 and
                        isinstance(node.body[0], ast.Expr) and
                        isinstance(node.body[0].value, ast.Constant) and
                        isinstance(node.body[0].value.value, str)
                    )
                    
                    class_info = ClassInfo(
                        name=node.name,
                        line_number=node.lineno,
                        base_classes=base_classes,
                        methods=methods,
                        has_docstring=has_docstring
                    )
                    classes.append(class_info)
            
            return classes
            
        except ParsingError:
            raise
        except Exception as e:
            raise ParsingError(f"Failed to extract classes: {str(e)}")
    
    def extract_imports(self, filepath: Union[str, Path]) -> List[ImportInfo]:
        """Extract all import statements from a file.
        
        Args:
            filepath: Path to Python file
            
        Returns:
            List of ImportInfo objects
            
        Example:
            >>> imports = parser.extract_imports("code.py")
            >>> for imp in imports:
            ...     print(f"Imports {imp.module}")
        """
        try:
            tree = self.parse_file(filepath)
            if tree is None:
                return []
            
            imports: List[ImportInfo] = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        import_info = ImportInfo(
                            module=alias.name,
                            line_number=node.lineno,
                            alias=alias.asname,
                            is_from_import=False
                        )
                        imports.append(import_info)
                
                elif isinstance(node, ast.ImportFrom):
                    names = [alias.name for alias in node.names]
                    import_info = ImportInfo(
                        module=node.module or "",
                        line_number=node.lineno,
                        names=names,
                        is_from_import=True
                    )
                    imports.append(import_info)
            
            return imports
            
        except ParsingError:
            raise
        except Exception as e:
            raise ParsingError(f"Failed to extract imports: {str(e)}")
    
    def find_syntax_errors(self, filepath: Union[str, Path]) -> List[Dict[str, Any]]:
        """Find syntax errors in a file without executing it.
        
        Args:
            filepath: Path to Python file
            
        Returns:
            List of syntax error dictionaries
            
        Example:
            >>> errors = parser.find_syntax_errors("bad_code.py")
            >>> for error in errors:
            ...     print(f"Line {error['line']}: {error['message']}")
        """
        try:
            # Try to parse - if it succeeds, no syntax errors
            self.parse_file(filepath)
            return []
            
        except ParsingError as e:
            # Return structured error info
            return [{
                "line": e.context.get("line_number", 0),
                "message": e.message,
                "code_snippet": e.context.get("code_snippet", "")
            }]
    
    def get_code_metrics(self, filepath: Union[str, Path]) -> CodeMetrics:
        """Calculate code metrics for a file.
        
        Args:
            filepath: Path to Python file
            
        Returns:
            CodeMetrics object
            
        Example:
            >>> metrics = parser.get_code_metrics("code.py")
            >>> print(f"{metrics.code_lines} lines of code")
        """
        try:
            # Read file
            result = read_file(filepath, self._sandbox)
            if not result.success:
                return CodeMetrics()
            
            content = result.content
            lines = content.split('\n')
            
            # Count lines
            total_lines = len(lines)
            comment_lines = sum(1 for line in lines if line.strip().startswith('#'))
            code_lines = sum(1 for line in lines if line.strip() and not line.strip().startswith('#'))
            
            # Max line length
            max_line_length = max(len(line) for line in lines) if lines else 0
            
            # Try to parse AST for function/class counts
            function_count = 0
            class_count = 0
            import_count = 0
            
            try:
                tree = self.parse_file(filepath)
                if tree:
                    function_count = len(self.extract_functions(filepath))
                    class_count = len(self.extract_classes(filepath))
                    import_count = len(self.extract_imports(filepath))
            except:
                pass
            
            return CodeMetrics(
                total_lines=total_lines,
                code_lines=code_lines,
                comment_lines=comment_lines,
                function_count=function_count,
                class_count=class_count,
                import_count=import_count,
                max_line_length=max_line_length
            )
            
        except Exception as e:
            return CodeMetrics()


# Module-level convenience functions
def extract_functions(filepath: Union[str, Path],
                     sandbox: Optional[SandboxManager] = None) -> List[FunctionInfo]:
    """Convenience function to extract functions.
    
    Args:
        filepath: Path to Python file
        sandbox: Optional SandboxManager (uses global if None)
        
    Returns:
        List of FunctionInfo objects
    """
    from .sandbox import get_sandbox
    sandbox = sandbox or get_sandbox()
    parser = CodeParser(sandbox)
    return parser.extract_functions(filepath)


def extract_classes(filepath: Union[str, Path],
                   sandbox: Optional[SandboxManager] = None) -> List[ClassInfo]:
    """Convenience function to extract classes.
    
    Args:
        filepath: Path to Python file
        sandbox: Optional SandboxManager (uses global if None)
        
    Returns:
        List of ClassInfo objects
    """
    from .sandbox import get_sandbox
    sandbox = sandbox or get_sandbox()
    parser = CodeParser(sandbox)
    return parser.extract_classes(filepath)


def get_imports(filepath: Union[str, Path],
               sandbox: Optional[SandboxManager] = None) -> List[str]:
    """Get list of imported module names (convenience function).
    
    Args:
        filepath: Path to Python file
        sandbox: Optional SandboxManager
        
    Returns:
        List of module names
    """
    from .sandbox import get_sandbox
    sandbox = sandbox or get_sandbox()
    parser = CodeParser(sandbox)
    imports = parser.extract_imports(filepath)
    return [imp.module for imp in imports if imp.module]
