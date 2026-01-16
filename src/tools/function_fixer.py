"""
Function fixer module for The Refactoring Swarm.

This module provides automated code fixing capabilities based on Pylint analysis results.
It implements transformations to address common code quality issues:
- Missing docstrings
- Naming convention violations
- Unused imports
- Code complexity reduction
- Line length violations

Note: This is a tool-layer implementation for agent consumption.
The fixer applies structured transformations without executing code.
"""

import ast
import re
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

from .exceptions import ParsingError, FileOpError
from .parser import CodeParser, FunctionInfo, ClassInfo
from .file_ops import FileOperations
from .sandbox import SandboxManager


@dataclass
class FixedIssue:
    """Represents a successfully applied fix."""
    issue_type: str           # Issue symbol (e.g., 'missing-docstring')
    line_number: int
    original_code: str
    fixed_code: str
    fix_type: str            # 'insertion', 'replacement', 'deletion'
    description: str


@dataclass
class FixResult:
    """Result of attempting to fix code."""
    success: bool
    fixed_code: Optional[str] = None
    fixes_applied: List[FixedIssue] = None
    error: Optional[str] = None
    metadata: dict = None
    
    def __post_init__(self):
        if self.fixes_applied is None:
            self.fixes_applied = []
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "success": self.success,
            "fixes_applied": len(self.fixes_applied),
            "error": self.error,
            "metadata": self.metadata,
            "has_code": self.fixed_code is not None
        }


class FunctionFixer:
    """Automated code fixer using AST transformations.
    
    This class implements structural fixes for common Pylint issues:
    - Adds missing docstrings to functions and classes
    - Fixes naming violations
    - Removes unused imports
    - Simplifies overly complex code
    - Breaks long lines
    
    Design: Works on AST + text manipulation for precision.
    No code execution occurs.
    
    Example:
        >>> fixer = FunctionFixer(sandbox)
        >>> issues = [{"symbol": "missing-docstring", "line": 5, ...}]
        >>> result = fixer.fix_code(code_text, issues)
        >>> if result.success:
        ...     print(result.fixed_code)
    """
    
    def __init__(self, sandbox: SandboxManager):
        """Initialize FunctionFixer.
        
        Args:
            sandbox: SandboxManager instance for path validation
        """
        self._sandbox = sandbox
        self._parser = CodeParser(sandbox)
        self._file_ops = FileOperations(sandbox)
        
        # Common docstring templates
        self._docstring_templates = {
            "function": '    """Function description.\n    \n    Returns:\n        None\n    """',
            "class": '    """Class description."""',
        }
    
    def fix_code(self, code: str, issues: List[Dict[str, Any]]) -> FixResult:
        """Fix code based on Pylint issues.
        
        This method:
        1. Parses code into AST
        2. Identifies fixable issues
        3. Applies transformations
        4. Returns fixed code or original if no fixes possible
        
        Args:
            code: Source code as string
            issues: List of Pylint issues with 'symbol', 'line', 'message'
            
        Returns:
            FixResult with fixed code and applied fixes list
        """
        try:
            # Validate code is parseable
            tree = ast.parse(code)
        except SyntaxError as e:
            return FixResult(
                success=False,
                error=f"Cannot fix code with syntax errors: {e}",
                metadata={"error_type": "syntax_error", "line": e.lineno}
            )
        
        # Group issues by type for batch processing
        issues_by_type = self._group_issues_by_type(issues)
        
        lines = code.split('\n')
        fixes_applied: List[FixedIssue] = []
        
        # Apply fixes in order of priority (non-conflicting first)
        fix_methods = [
            ("missing-docstring", self._fix_missing_docstring),
            ("unused-import", self._fix_unused_import),
            ("line-too-long", self._fix_line_too_long),
            ("invalid-name", self._fix_invalid_name),
            ("too-many-arguments", self._fix_too_many_arguments),
        ]
        
        for issue_type, fix_method in fix_methods:
            if issue_type in issues_by_type:
                for issue in issues_by_type[issue_type]:
                    try:
                        fixed_issue = fix_method(lines, issue)
                        if fixed_issue:
                            fixes_applied.append(fixed_issue)
                    except Exception as e:
                        # Log failure but continue with other fixes
                        continue
        
        # Reconstruct code
        fixed_code = '\n'.join(lines)
        
        return FixResult(
            success=True,
            fixed_code=fixed_code if fixes_applied else code,
            fixes_applied=fixes_applied,
            metadata={
                "issues_processed": len(issues),
                "issues_fixed": len(fixes_applied),
                "fix_rate": len(fixes_applied) / len(issues) if issues else 0.0
            }
        )
    
    def _group_issues_by_type(self, issues: List[Dict[str, Any]]) -> Dict[str, List[Dict]]:
        """Group issues by their symbol/type.
        
        Args:
            issues: List of issue dictionaries
            
        Returns:
            Dictionary mapping issue type to list of issues
        """
        grouped = {}
        for issue in issues:
            issue_type = issue.get("symbol", "unknown")
            if issue_type not in grouped:
                grouped[issue_type] = []
            grouped[issue_type].append(issue)
        return grouped
    
    def _fix_missing_docstring(self, lines: List[str], issue: Dict) -> Optional[FixedIssue]:
        """Fix missing docstring by adding one.
        
        Adds appropriate docstring template to functions and classes.
        
        Args:
            lines: Code lines (mutable)
            issue: Issue dictionary with 'line', 'message'
            
        Returns:
            FixedIssue if successful, None otherwise
        """
        line_num = issue.get("line", 0) - 1  # Convert to 0-indexed
        if line_num < 0 or line_num >= len(lines):
            return None
        
        line = lines[line_num]
        
        # Check if this is a function or class definition
        if line.strip().startswith("def "):
            docstring_type = "function"
        elif line.strip().startswith("class "):
            docstring_type = "class"
        else:
            return None
        
        # Calculate indentation
        indent = len(line) - len(line.lstrip())
        indent_str = ' ' * indent
        
        # Get template and adjust indentation
        template = self._docstring_templates[docstring_type]
        if docstring_type == "function":
            docstring = f'{indent_str}"""\n{indent_str}Function description.\n{indent_str}\n{indent_str}Returns:\n{indent_str}    None\n{indent_str}"""'
        else:
            docstring = f'{indent_str}"""Class description."""'
        
        # Find the colon and next line (where docstring should go)
        colon_idx = line.find(":")
        if colon_idx == -1:
            return None
        
        # Check if next line is already a docstring
        if line_num + 1 < len(lines):
            next_line = lines[line_num + 1].strip()
            if next_line.startswith('"""') or next_line.startswith("'''"):
                return None  # Already has docstring
        
        original_code = line
        
        # Insert docstring on next line
        lines.insert(line_num + 1, docstring)
        
        return FixedIssue(
            issue_type="missing-docstring",
            line_number=line_num + 1,
            original_code=original_code,
            fixed_code=f"{original_code}\n{docstring}",
            fix_type="insertion",
            description=f"Added docstring to {docstring_type}"
        )
    
    def _fix_unused_import(self, lines: List[str], issue: Dict) -> Optional[FixedIssue]:
        """Remove unused import statements.
        
        Removes entire import line or specific import from 'from X import Y'.
        
        Args:
            lines: Code lines (mutable)
            issue: Issue dictionary with 'line', 'message'
            
        Returns:
            FixedIssue if successful, None otherwise
        """
        line_num = issue.get("line", 0) - 1  # Convert to 0-indexed
        if line_num < 0 or line_num >= len(lines):
            return None
        
        line = lines[line_num]
        original_code = line
        
        # Check if it's an import statement
        if not (line.strip().startswith("import ") or line.strip().startswith("from ")):
            return None
        
        # Extract unused module name from message
        # Message format: "Unused import module_name"
        unused_match = re.search(r"Unused import (\w+)", issue.get("message", ""))
        if not unused_match:
            return None
        
        unused_name = unused_match.group(1)
        
        # Handle "from X import Y" statements
        if "from " in line and " import " in line:
            # Parse and rebuild without the unused import
            # For simplicity, if only one import, remove whole line
            import_match = re.search(r"from .+ import (.+)", line)
            if import_match:
                imports_str = import_match.group(1)
                imports = [i.strip() for i in imports_str.split(",")]
                
                if len(imports) == 1:
                    # Remove entire line
                    del lines[line_num]
                    return FixedIssue(
                        issue_type="unused-import",
                        line_number=line_num + 1,
                        original_code=original_code,
                        fixed_code="",
                        fix_type="deletion",
                        description=f"Removed unused import: {unused_name}"
                    )
                else:
                    # Remove specific import from list
                    imports = [i for i in imports if unused_name not in i]
                    new_line = re.sub(
                        r"from .+ import .+",
                        f"from {import_match.group(0).split()[1]} import {', '.join(imports)}",
                        line
                    )
                    lines[line_num] = new_line
                    return FixedIssue(
                        issue_type="unused-import",
                        line_number=line_num + 1,
                        original_code=original_code,
                        fixed_code=new_line,
                        fix_type="replacement",
                        description=f"Removed {unused_name} from imports"
                    )
        else:
            # Simple import statement
            del lines[line_num]
            return FixedIssue(
                issue_type="unused-import",
                line_number=line_num + 1,
                original_code=original_code,
                fixed_code="",
                fix_type="deletion",
                description=f"Removed unused import: {unused_name}"
            )
        
        return None
    
    def _fix_line_too_long(self, lines: List[str], issue: Dict) -> Optional[FixedIssue]:
        """Break overly long lines into multiple lines.
        
        Applies intelligent line breaking for long lines while preserving syntax.
        
        Args:
            lines: Code lines (mutable)
            issue: Issue dictionary with 'line'
            
        Returns:
            FixedIssue if successful, None otherwise
        """
        line_num = issue.get("line", 0) - 1  # Convert to 0-indexed
        if line_num < 0 or line_num >= len(lines):
            return None
        
        line = lines[line_num]
        original_code = line
        
        # Only break very long lines (> 100 chars)
        if len(line) <= 100:
            return None
        
        # Try to break at logical points
        indent = len(line) - len(line.lstrip())
        indent_str = ' ' * indent
        
        # Strategy 1: Break at function call arguments
        if "(" in line and ")" in line:
            # Find function call
            match = re.search(r'(\w+)\((.+)\)', line)
            if match:
                func_name = match.group(1)
                args_str = match.group(2)
                args = [arg.strip() for arg in args_str.split(",")]
                
                if len(args) > 1:
                    # Rebuild with each arg on new line
                    new_lines = [f"{indent_str}{func_name}("]
                    for i, arg in enumerate(args):
                        if i < len(args) - 1:
                            new_lines.append(f"{indent_str}    {arg},")
                        else:
                            new_lines.append(f"{indent_str}    {arg}")
                    new_lines[-1] += ")"
                    
                    lines[line_num:line_num+1] = new_lines
                    
                    return FixedIssue(
                        issue_type="line-too-long",
                        line_number=line_num + 1,
                        original_code=original_code,
                        fixed_code='\n'.join(new_lines),
                        fix_type="replacement",
                        description="Broke long line into multiple lines"
                    )
        
        return None
    
    def _fix_invalid_name(self, lines: List[str], issue: Dict) -> Optional[FixedIssue]:
        """Fix invalid naming conventions.
        
        Converts naming violations to PEP 8 compliant names.
        
        Args:
            lines: Code lines (mutable)
            issue: Issue dictionary with 'line', 'message'
            
        Returns:
            FixedIssue if successful, None otherwise
        """
        line_num = issue.get("line", 0) - 1
        if line_num < 0 or line_num >= len(lines):
            return None
        
        line = lines[line_num]
        original_code = line
        
        # Extract invalid name from message
        # Message format: "Invalid name \"CamelCase\" (invalid-name)"
        name_match = re.search(r'Invalid name "(\w+)"', issue.get("message", ""))
        if not name_match:
            return None
        
        invalid_name = name_match.group(1)
        valid_name = self._to_snake_case(invalid_name)
        
        if valid_name == invalid_name:
            return None  # Already valid
        
        # Replace the invalid name with valid one
        new_line = re.sub(rf'\b{invalid_name}\b', valid_name, line)
        
        if new_line != line:
            lines[line_num] = new_line
            
            return FixedIssue(
                issue_type="invalid-name",
                line_number=line_num + 1,
                original_code=original_code,
                fixed_code=new_line,
                fix_type="replacement",
                description=f"Renamed {invalid_name} to {valid_name}"
            )
        
        return None
    
    def _fix_too_many_arguments(self, lines: List[str], issue: Dict) -> Optional[FixedIssue]:
        """Suggest refactoring for functions with too many arguments.
        
        Note: This is a structure suggestion, not an automatic fix.
        The fixer adds a comment suggesting the use of a config object.
        
        Args:
            lines: Code lines (mutable)
            issue: Issue dictionary with 'line'
            
        Returns:
            FixedIssue if successful, None otherwise
        """
        line_num = issue.get("line", 0) - 1
        if line_num < 0 or line_num >= len(lines):
            return None
        
        line = lines[line_num]
        original_code = line
        
        # Only add comment suggestion for function definitions
        if not line.strip().startswith("def "):
            return None
        
        # Extract indentation
        indent = len(line) - len(line.lstrip())
        indent_str = ' ' * indent
        
        # Add helpful comment before function
        comment = f'{indent_str}# Consider using a config object instead of many arguments'
        
        lines.insert(line_num, comment)
        
        return FixedIssue(
            issue_type="too-many-arguments",
            line_number=line_num + 1,
            original_code=original_code,
            fixed_code=f"{comment}\n{line}",
            fix_type="insertion",
            description="Added refactoring suggestion for too many arguments"
        )
    
    @staticmethod
    def _to_snake_case(name: str) -> str:
        """Convert CamelCase to snake_case.
        
        Args:
            name: Name to convert
            
        Returns:
            snake_case version of name
        """
        # Insert underscore before uppercase letters
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        # Handle consecutive uppercase letters
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


# Module-level convenience function
def fix_code(code: str, issues: List[Dict[str, Any]], sandbox: Optional[SandboxManager] = None) -> FixResult:
    """Convenience function to fix code.
    
    Args:
        code: Source code as string
        issues: List of Pylint issues
        sandbox: SandboxManager instance (uses global if not provided)
        
    Returns:
        FixResult with fixed code
        
    Example:
        >>> code = "def my_func():\\n    pass"
        >>> issues = [{"symbol": "missing-docstring", "line": 1, "message": "..."}]
        >>> result = fix_code(code, issues)
        >>> if result.success:
        ...     print(result.fixed_code)
    """
    if sandbox is None:
        from . import get_sandbox
        sandbox = get_sandbox()
    
    fixer = FunctionFixer(sandbox)
    return fixer.fix_code(code, issues)
