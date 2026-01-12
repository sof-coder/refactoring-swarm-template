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
    
    def write_file(self, filepath: Union[str, Path], content: str,
                   encoding: str = "utf-8", create_backup: bool = True) -> FileOperationResult:
        """Write content to a file atomically.
        
        This method performs atomic writes to prevent data corruption:
        1. Validates the path is within sandbox
        2. Creates backup of existing file (if requested)
        3. Writes to temporary file
        4. Renames temp file to target (atomic operation)
        
        Args:
            filepath: Path to file (relative to sandbox or absolute within sandbox)
            content: Content to write
            encoding: Character encoding (default: utf-8)
            create_backup: Whether to backup existing file (default: True)
            
        Returns:
            FileOperationResult with success status
            
        Example:
            >>> result = file_ops.write_file("output.py", "print('hello')")
            >>> if result.success:
            ...     print(f"Wrote to {result.filepath}")
        """
        try:
            # Validate path
            safe_path = self._sandbox.validate_path(filepath)
            
            # Create parent directories if needed
            safe_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create backup if file exists
            backup_path = None
            if create_backup and safe_path.exists():
                backup_result = self.create_backup(safe_path)
                if backup_result.success:
                    backup_path = backup_result.metadata.get("backup_path")
            
            # Write to temporary file first (atomic operation)
            temp_path = safe_path.with_suffix(safe_path.suffix + ".tmp")
            temp_path.write_text(content, encoding=encoding)
            
            # Atomic rename
            temp_path.replace(safe_path)
            
            # Get file metadata
            stat = safe_path.stat()
            metadata = {
                "size_bytes": stat.st_size,
                "encoding": encoding,
                "line_count": content.count('\n') + 1,
                "backup_created": backup_path is not None,
                "backup_path": backup_path
            }
            
            return FileOperationResult(
                success=True,
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
                error=f"Write failed: {type(e).__name__}: {str(e)}"
            )
    
    def create_backup(self, filepath: Union[str, Path]) -> FileOperationResult:
        """Create a backup copy of a file.
        
        Backup filename format: original_name.bak.TIMESTAMP
        
        Args:
            filepath: Path to file to backup
            
        Returns:
            FileOperationResult with backup path in metadata
            
        Example:
            >>> result = file_ops.create_backup("important.py")
            >>> print(result.metadata["backup_path"])
            /sandbox/important.py.bak.20260109_143022
        """
        try:
            # Validate path
            safe_path = self._sandbox.validate_path(filepath)
            
            # Check file exists
            if not safe_path.exists():
                return FileOperationResult(
                    success=False,
                    filepath=str(safe_path),
                    error="Cannot backup: file does not exist"
                )
            
            # Generate backup filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = safe_path.with_suffix(f"{safe_path.suffix}.bak.{timestamp}")
            
            # Copy file
            shutil.copy2(safe_path, backup_path)
            
            return FileOperationResult(
                success=True,
                filepath=str(safe_path),
                metadata={
                    "backup_path": str(backup_path),
                    "timestamp": timestamp
                }
            )
            
        except Exception as e:
            return FileOperationResult(
                success=False,
                filepath=str(filepath),
                error=f"Backup failed: {type(e).__name__}: {str(e)}"
            )
    
    def list_python_files(self, directory: Optional[Union[str, Path]] = None) -> FileOperationResult:
        """List all Python files in a directory (recursively).
        
        Args:
            directory: Directory to search (defaults to sandbox root)
            
        Returns:
            FileOperationResult with list of file paths in metadata
            
        Example:
            >>> result = file_ops.list_python_files()
            >>> for filepath in result.metadata["files"]:
            ...     print(filepath)
        """
        try:
            if directory:
                search_dir = self._sandbox.validate_path(directory)
            else:
                search_dir = self._sandbox.sandbox_root
            
            # Find all .py files
            python_files = sorted([str(f) for f in search_dir.rglob("*.py")])
            
            return FileOperationResult(
                success=True,
                filepath=str(search_dir),
                metadata={
                    "files": python_files,
                    "count": len(python_files)
                }
            )
            
        except Exception as e:
            return FileOperationResult(
                success=False,
                filepath=str(directory) if directory else "sandbox root",
                error=f"List failed: {type(e).__name__}: {str(e)}"
            )
    
    def file_exists(self, filepath: Union[str, Path]) -> bool:
        """Check if a file exists within the sandbox.
        
        Args:
            filepath: Path to check
            
        Returns:
            True if file exists, False otherwise
        """
        try:
            safe_path = self._sandbox.validate_path(filepath)
            return safe_path.exists() and safe_path.is_file()
        except:
            return False
    
    def get_file_info(self, filepath: Union[str, Path]) -> FileOperationResult:
        """Get detailed information about a file.
        
        Args:
            filepath: Path to file
            
        Returns:
            FileOperationResult with file metadata
            
        Example:
            >>> result = file_ops.get_file_info("code.py")
            >>> print(result.metadata)
            {'size_bytes': 1234, 'modified': '2026-01-09T14:30:22', ...}
        """
        try:
            safe_path = self._sandbox.validate_path(filepath)
            
            if not safe_path.exists():
                return FileOperationResult(
                    success=False,
                    filepath=str(safe_path),
                    error="File not found"
                )
            
            stat = safe_path.stat()
            metadata = {
                "exists": True,
                "is_file": safe_path.is_file(),
                "is_directory": safe_path.is_dir(),
                "size_bytes": stat.st_size,
                "created_time": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "extension": safe_path.suffix,
                "filename": safe_path.name
            }
            
            return FileOperationResult(
                success=True,
                filepath=str(safe_path),
                metadata=metadata
            )
            
        except Exception as e:
            return FileOperationResult(
                success=False,
                filepath=str(filepath),
                error=f"Failed to get file info: {str(e)}"
            )
    
    def delete_file(self, filepath: Union[str, Path], 
                    create_backup: bool = True) -> FileOperationResult:
        """Delete a file (with optional backup).
        
        Args:
            filepath: Path to file to delete
            create_backup: Whether to create backup before deletion
            
        Returns:
            FileOperationResult with deletion status
        """
        try:
            safe_path = self._sandbox.validate_path(filepath)
            
            if not safe_path.exists():
                return FileOperationResult(
                    success=False,
                    filepath=str(safe_path),
                    error="File not found"
                )
            
            # Create backup if requested
            backup_path = None
            if create_backup:
                backup_result = self.create_backup(safe_path)
                if backup_result.success:
                    backup_path = backup_result.metadata.get("backup_path")
            
            # Delete the file
            safe_path.unlink()
            
            return FileOperationResult(
                success=True,
                filepath=str(safe_path),
                metadata={
                    "deleted": True,
                    "backup_created": backup_path is not None,
                    "backup_path": backup_path
                }
            )
            
        except Exception as e:
            return FileOperationResult(
                success=False,
                filepath=str(filepath),
                error=f"Delete failed: {str(e)}"
            )


# Module-level convenience functions (use global sandbox)
def read_file(filepath: Union[str, Path], 
              sandbox: Optional[SandboxManager] = None) -> FileOperationResult:
    """Convenience function to read a file.
    
    Args:
        filepath: Path to file
        sandbox: Optional SandboxManager (uses global if None)
        
    Returns:
        FileOperationResult
    """
    from .sandbox import get_sandbox
    sandbox = sandbox or get_sandbox()
    file_ops = FileOperations(sandbox)
    return file_ops.read_file(filepath)


def write_file(filepath: Union[str, Path], content: str,
               sandbox: Optional[SandboxManager] = None) -> FileOperationResult:
    """Convenience function to write a file.
    
    Args:
        filepath: Path to file
        content: Content to write
        sandbox: Optional SandboxManager (uses global if None)
        
    Returns:
        FileOperationResult
    """
    from .sandbox import get_sandbox
    sandbox = sandbox or get_sandbox()
    file_ops = FileOperations(sandbox)
    return file_ops.write_file(filepath, content)


def list_python_files(directory: Optional[Union[str, Path]] = None,
                      sandbox: Optional[SandboxManager] = None) -> List[str]:
    """Convenience function to list Python files.
    
    Args:
        directory: Directory to search (defaults to sandbox root)
        sandbox: Optional SandboxManager (uses global if None)
        
    Returns:
        List of file paths
    """
    from .sandbox import get_sandbox
    sandbox = sandbox or get_sandbox()
    file_ops = FileOperations(sandbox)
    result = file_ops.list_python_files(directory)
    return result.metadata.get("files", []) if result.success else []
