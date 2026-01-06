"""Sandbox security for file operations."""

from pathlib import Path
from .exceptions import SecurityError


class SandboxManager:
    """Manages sandbox security for file operations."""
    
    def __init__(self, sandbox_path):
        self.sandbox_root = Path(sandbox_path).resolve()
        self.sandbox_root.mkdir(parents=True, exist_ok=True)
    
    def validate_path(self, path):
        """Validate that path is within sandbox."""
        try:
            full_path = Path(path).resolve()
            full_path.relative_to(self.sandbox_root)
            return full_path
        except (ValueError, OSError):
            raise SecurityError(
                f"Path outside sandbox: {path}",
                attempted_path=str(path),
                sandbox_root=str(self.sandbox_root)
            )
