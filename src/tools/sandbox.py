"""
Sandbox security manager for The Refactoring Swarm.

This module provides path validation and security controls to ensure
that agents can only access files within the designated sandbox directory.

Security Features:
- Path traversal prevention (blocks ../)
- Absolute path validation
- Symlink resolution
- Platform-independent path handling
"""

import os
from pathlib import Path
from typing import Union, Optional
from .exceptions import SecurityError


class SandboxManager:
    """Manages sandbox security and path validation.
    
    This class ensures that all file operations are restricted to a specific
    sandbox directory. It prevents path traversal attacks and unauthorized
    file access.
    
    Design Pattern: Single instance per sandbox directory
    Thread Safety: Thread-safe (no mutable state)
    
    Example:
        >>> sandbox = SandboxManager("/workspace/sandbox")
        >>> safe_path = sandbox.validate_path("code.py")
        >>> print(safe_path)
        /workspace/sandbox/code.py
        
        >>> sandbox.validate_path("../../etc/passwd")
        SecurityError: Path traversal detected
    
    Attributes:
        sandbox_root: Absolute path to the sandbox directory
    """
    
    def __init__(self, sandbox_path: Union[str, Path]):
        """Initialize the SandboxManager.
        
        Args:
            sandbox_path: Path to the sandbox directory (relative or absolute)
            
        Raises:
            ValueError: If sandbox_path is empty or None
        """
        if not sandbox_path:
            raise ValueError("Sandbox path cannot be empty")
        
        # Convert to absolute path and resolve symlinks
        self._sandbox_root = Path(sandbox_path).resolve()
        
        # Ensure sandbox directory exists
        self._sandbox_root.mkdir(parents=True, exist_ok=True)
    
    @property
    def sandbox_root(self) -> Path:
        """Get the sandbox root directory.
        
        Returns:
            Absolute path to sandbox root
        """
        return self._sandbox_root
    
    def validate_path(self, path: Union[str, Path]) -> Path:
        """Validate that a path is within the sandbox.
        
        This method performs comprehensive security checks:
        1. Resolves the path to absolute (handles symlinks)
        2. Normalizes the path (removes .., ., redundant separators)
        3. Checks if the resolved path is within sandbox_root
        4. Raises SecurityError if validation fails
        
        Args:
            path: Path to validate (can be relative or absolute)
            
        Returns:
            Validated absolute Path object
            
        Raises:
            SecurityError: If path is outside sandbox or contains traversal attempts
            ValueError: If path is empty or None
            
        Example:
            >>> sandbox = SandboxManager("/workspace/sandbox")
            >>> sandbox.validate_path("subdir/code.py")
            PosixPath('/workspace/sandbox/subdir/code.py')
        """
        if not path:
            raise ValueError("Path cannot be empty")
        
        path = Path(path)
        
        # If path is relative, treat it as relative to sandbox root
        if not path.is_absolute():
            path = self._sandbox_root / path
        
        # Resolve to absolute path (follows symlinks, removes ..)
        try:
            resolved_path = path.resolve()
        except (OSError, RuntimeError) as e:
            raise SecurityError(
                f"Failed to resolve path: {e}",
                attempted_path=str(path)
            )
        
        # Check if resolved path is within sandbox
        try:
            # relative_to() raises ValueError if not a subpath
            resolved_path.relative_to(self._sandbox_root)
        except ValueError:
            raise SecurityError(
                f"Path outside sandbox: {resolved_path} is not within {self._sandbox_root}",
                attempted_path=str(path)
            )
        
        return resolved_path
    
    def is_safe(self, path: Union[str, Path]) -> bool:
        """Check if a path is safe (within sandbox) without raising exceptions.
        
        This is a non-throwing version of validate_path, useful for conditional checks.
        
        Args:
            path: Path to check
            
        Returns:
            True if path is within sandbox, False otherwise
            
        Example:
            >>> sandbox = SandboxManager("/workspace/sandbox")
            >>> sandbox.is_safe("code.py")
            True
            >>> sandbox.is_safe("../../etc/passwd")
            False
        """
        try:
            self.validate_path(path)
            return True
        except (SecurityError, ValueError):
            return False
    
    def get_safe_path(self, relative_path: Union[str, Path]) -> Path:
        """Get a safe path by joining with sandbox root.
        
        This is a convenience method for constructing paths within the sandbox.
        It always treats the input as relative to sandbox root.
        
        Args:
            relative_path: Path relative to sandbox root
            
        Returns:
            Validated absolute path
            
        Raises:
            SecurityError: If resulting path is outside sandbox
            
        Example:
            >>> sandbox = SandboxManager("/workspace/sandbox")
            >>> sandbox.get_safe_path("subfolder/code.py")
            PosixPath('/workspace/sandbox/subfolder/code.py')
        """
        full_path = self._sandbox_root / relative_path
        return self.validate_path(full_path)
    
    def ensure_exists(self) -> None:
        """Ensure the sandbox directory exists.
        
        Creates the sandbox directory if it doesn't exist.
        Safe to call multiple times (idempotent).
        """
        self._sandbox_root.mkdir(parents=True, exist_ok=True)
    
    def list_python_files(self, subdir: Optional[Union[str, Path]] = None) -> list[Path]:
        """List all Python files in the sandbox (or a subdirectory).
        
        Args:
            subdir: Optional subdirectory within sandbox (defaults to sandbox root)
            
        Returns:
            List of absolute paths to Python files
            
        Raises:
            SecurityError: If subdir is outside sandbox
            
        Example:
            >>> sandbox = SandboxManager("/workspace/sandbox")
            >>> files = sandbox.list_python_files()
            >>> print(files)
            [PosixPath('/workspace/sandbox/code.py'), ...]
        """
        if subdir:
            search_dir = self.validate_path(subdir)
        else:
            search_dir = self._sandbox_root
        
        # Find all .py files recursively
        return sorted(search_dir.rglob("*.py"))
    
    def cleanup(self, preserve_structure: bool = False) -> None:
        """Clean up the sandbox directory.
        
        WARNING: This deletes files! Use with caution.
        
        Args:
            preserve_structure: If True, only delete files but keep directories
            
        Example:
            >>> sandbox = SandboxManager("/workspace/sandbox")
            >>> sandbox.cleanup(preserve_structure=True)  # Remove files, keep folders
        """
        if preserve_structure:
            # Only delete files
            for file_path in self._sandbox_root.rglob("*"):
                if file_path.is_file():
                    file_path.unlink()
        else:
            # Delete everything
            import shutil
            if self._sandbox_root.exists():
                shutil.rmtree(self._sandbox_root)
                self._sandbox_root.mkdir(parents=True, exist_ok=True)


# Module-level convenience function
_global_sandbox: Optional[SandboxManager] = None


def initialize_sandbox(sandbox_path: Union[str, Path]) -> SandboxManager:
    """Initialize the global sandbox manager.
    
    This function should be called once at the start of the application
    to set up the sandbox directory for all tools.
    
    Args:
        sandbox_path: Path to the sandbox directory
        
    Returns:
        Initialized SandboxManager instance
        
    Example:
        >>> initialize_sandbox("./sandbox")
        >>> safe_path = get_safe_path("code.py")
    """
    global _global_sandbox
    _global_sandbox = SandboxManager(sandbox_path)
    return _global_sandbox


def get_sandbox() -> SandboxManager:
    """Get the global sandbox manager instance.
    
    Returns:
        Global SandboxManager instance
        
    Raises:
        RuntimeError: If sandbox has not been initialized
    """
    if _global_sandbox is None:
        raise RuntimeError(
            "Sandbox not initialized. Call initialize_sandbox() first."
        )
    return _global_sandbox


def get_safe_path(relative_path: Union[str, Path]) -> Path:
    """Convenience function to get a safe path from the global sandbox.
    
    Args:
        relative_path: Path relative to sandbox root
        
    Returns:
        Validated absolute path
        
    Raises:
        RuntimeError: If sandbox not initialized
        SecurityError: If path is outside sandbox
    """
    return get_sandbox().get_safe_path(relative_path)
