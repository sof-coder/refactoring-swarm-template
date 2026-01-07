"""Code quality analysis using Pylint."""

from dataclasses import dataclass
from typing import List, Optional
import subprocess
from .sandbox import get_sandbox
from .exceptions import AnalysisError


@dataclass
class Issue:
    """A single code issue."""
    type: str
    line: int
    column: int
    message: str
    symbol: str


@dataclass
class AnalysisResult:
    """Result of code analysis."""
    success: bool
    score: Optional[float] = None
    issues: List[Issue] = None
    error: Optional[str] = None


class PylintAnalyzer:
    """Analyze code quality with Pylint."""
    
    def __init__(self, sandbox_manager=None):
        self.sandbox = sandbox_manager or get_sandbox()
