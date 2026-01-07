"""
File operations module for The Refactoring Swarm.

This module provides safe, atomic file I/O operations with comprehensive
error handling and logging. All operations respect sandbox security.

Features:
- Atomic writes (temp file + rename)
- Automatic backup creation
- UTF-8 encoding with fallback
- Structured error reporting
"""

import os
import shutil
from pathlib import Path
from typing import Union, Optional, Tuple, List
from dataclasses import dataclass, field
from datetime import datetime

from .exceptions import FileOpError, SecurityError
from .sandbox import SandboxManager


@dataclass
class FileOperationResult:
    """Result of a file operation.
    
    This class provides a structured way to return success/failure
    information without using exceptions for flow control.
    
    Attributes:
        success: Whether the operation succeeded
        content: File content (for read operations)
        filepath: The file that was operated on
        error: Error message if operation failed
        metadata: Additional information (size, encoding, timestamp, etc.)
    """
    success: bool
    content: Optional[str] = None
    filepath: Optional[str] = None
    error: Optional[str] = None
    metadata: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Convert result to dictionary for logging.
        
        Returns:
            Dictionary representation suitable for JSON serialization
        """
        return {
            "success": self.success,
            "filepath": self.filepath,
            "error": self.error,
            "metadata": self.metadata,
            "has_content": self.content is not None
        }


class FileOperations:
    """File operations manager with sandbox security.
    
    This class provides safe file I/O operations that respect sandbox boundaries.
    All operations are atomic and include comprehensive error handling.
    
    Example:
        >>> sandbox = SandboxManager("/workspace/sandbox")
        >>> file_ops = FileOperations(sandbox)
        >>> result = file_ops.read_file("code.py")
        >>> if result.success:
        ...     print(result.content)
    """
    
    def __init__(self, sandbox: SandboxManager):
        """Initialize FileOperations.
        
        Args:
            sandbox: SandboxManager instance for path validation
        """
        self._sandbox = sandbox
    
    def read_file(self, filepath: Union[str, Path], 
                  encoding: str = "utf-8") -> FileOperationResult:
        """Read a file safely with encoding handling.
        
        This method:
        1. Validates the path is within sandbox
        2. Checks file exists
        3. Reads with specified encoding
        4. Falls back to latin-1 if UTF-8 fails
        5. Returns structured result
        
        Args:
            filepath: Path to file (relative to sandbox or absolute within sandbox)
            encoding: Character encoding (default: utf-8)
            
        Returns:
            FileOperationResult with content or error
            
        Example:
            >>> result = file_ops.read_file("code.py")
            >>> if result.success:
            ...     print(f"Read {len(result.content)} characters")
        """
        try:
            # Validate path
            safe_path = self._sandbox.validate_path(filepath)
            
            # Check file exists
            if not safe_path.exists():
                return FileOperationResult(
                    success=False,
                    filepath=str(safe_path),
                    error=f"File not found: {safe_path}"
                )
            
            # Check it's a file (not directory)
            if not safe_path.is_file():
                return FileOperationResult(
                    success=False,
                    filepath=str(safe_path),
                    error=f"Not a file: {safe_path}"
                )
            
            # Try to read with specified encoding
            try:
                content = safe_path.read_text(encoding=encoding)
                actual_encoding = encoding
            except UnicodeDecodeError:
                # Fallback to latin-1 (never fails)
                content = safe_path.read_text(encoding="latin-1")
                actual_encoding = "latin-1"
            
            # Get file metadata
            stat = safe_path.stat()
            metadata = {
                "size_bytes": stat.st_size,
                "encoding": actual_encoding,
                "line_count": content.count('\n') + 1,
                "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat()
            }
            
            return FileOperationResult(
                success=True,
                content=content,
                filepath=str(safe_path),
                metadata=metadata
            )
            
        except SecurityError as e:
            return FileOperationResult(
                success=False,
                filepath=str(filepath),
                error=f"Security violation: {e.message}"
            )
        except Exception as e:
            return FileOperationResult(
                success=False,
                filepath=str(filepath),
                error=f"Unexpected error: {type(e).__name__}: {str(e)}"
            )
    