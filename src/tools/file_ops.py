"""File operations with safety and backup."""

from pathlib import Path
from dataclasses import dataclass
from typing import Optional
from .sandbox import get_sandbox
from .exceptions import FileOpError


@dataclass
class FileOperationResult:
    """Result of a file operation."""
    success: bool
    content: Optional[str] = None
    filepath: Optional[str] = None
    error: Optional[str] = None
    metadata: Optional[dict] = None


class FileOperations:
    """Safe file operations with backup."""
    
    def __init__(self, sandbox_manager=None):
        self.sandbox = sandbox_manager or get_sandbox()
