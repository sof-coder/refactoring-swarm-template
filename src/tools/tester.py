"""
Test execution module for The Refactoring Swarm.

This module provides integration with Pytest for automated testing.
It executes tests via subprocess and parses results into structured format.

Features:
- Subprocess isolation (test failures don't crash main process)
- Timeout protection (60s default)
- Detailed failure information
- Test statistics and success rate calculation
"""

import subprocess
import json
import re
from pathlib import Path
from typing import Union, Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime

from .exceptions import TestError, SecurityError
from .sandbox import SandboxManager


@dataclass
class FailedTest:
    """Information about a failed test.
    
    Attributes:
        test_name: Name of the test function
        test_file: File containing the test
        line_number: Line where test is defined
        error_type: Type of error (AssertionError, etc.)
        error_message: Error message
        traceback: Full traceback
    """
    test_name: str
    test_file: str
    line_number: int = 0
    error_type: str = ""
    error_message: str = ""
    traceback: str = ""
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "test_name": self.test_name,
            "test_file": self.test_file,
            "line_number": self.line_number,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "traceback": self.traceback
        }


@dataclass
class TestResult:
    """Result of test execution.
    
    Attributes:
        success: Whether test execution completed (not whether tests passed!)
        all_tests_passed: Whether all tests passed
        stats: Test statistics (total, passed, failed, skipped, errors)
        failed_tests: List of failed test details
        error: Error message if execution failed
        metadata: Additional info (execution time, etc.)
    """
    success: bool
    all_tests_passed: bool = False
    stats: dict = field(default_factory=dict)
    failed_tests: List[FailedTest] = field(default_factory=list)
    error: Optional[str] = None
    metadata: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "success": self.success,
            "all_tests_passed": self.all_tests_passed,
            "stats": self.stats,
            "failed_tests": [ft.to_dict() for ft in self.failed_tests],
            "error": self.error,
            "metadata": self.metadata
        }
    
    def get_success_rate(self) -> float:
        """Calculate test success rate as percentage.
        
        Returns:
            Success rate (0.0 - 100.0)
        """
        total = self.stats.get("total", 0)
        if total == 0:
            return 0.0
        passed = self.stats.get("passed", 0)
        return (passed / total) * 100.0


class PytestRunner:
    """Pytest integration for test execution.
    
    This class executes Pytest via subprocess and parses the output
    into structured TestResult objects.
    
    Example:
        >>> runner = PytestRunner(sandbox, timeout=60)
        >>> result = runner.run_tests("tests/")
        >>> if result.all_tests_passed:
        ...     print("All tests passed!")
        >>> else:
        ...     for failed in result.failed_tests:
        ...         print(f"FAILED: {failed.test_name}")
    """
    
    def __init__(self, sandbox: SandboxManager, timeout: int = 60):
        """Initialize PytestRunner.
        
        Args:
            sandbox: SandboxManager for path validation
            timeout: Maximum execution time in seconds (default: 60)
        """
        self._sandbox = sandbox
        self._timeout = timeout
    
    def run_tests(self, test_path: Union[str, Path]) -> TestResult:
        """Run tests with Pytest.
        
        This method:
        1. Validates the test path
        2. Constructs Pytest command
        3. Executes Pytest with timeout
        4. Parses output
        5. Returns structured result
        
        Args:
            test_path: Path to test file or directory
            
        Returns:
            TestResult with pass/fail status and details
            
        Example:
            >>> result = runner.run_tests("tests/")
            >>> print(f"Pass rate: {result.get_success_rate():.1f}%")
        """
        start_time = datetime.now()
        
        try:
            # Validate path
            safe_path = self._sandbox.validate_path(test_path)
            
            # Check path exists
            if not safe_path.exists():
                return TestResult(
                    success=False,
                    error=f"Test path not found: {safe_path}"
                )
            
            # Run pytest
            raw_output, return_code = self._run_pytest(safe_path)
            
            # Parse output
            stats, failed_tests = self._parse_output(raw_output)
            
            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Determine if all tests passed
            all_passed = stats.get("failed", 0) == 0 and stats.get("errors", 0) == 0
            
            # Build metadata
            metadata = {
                "test_path": str(safe_path),
                "execution_time": execution_time,
                "return_code": return_code,
                "timestamp": datetime.now().isoformat(),
                "success_rate": self._calculate_success_rate(stats)
            }
            
            return TestResult(
                success=True,
                all_tests_passed=all_passed,
                stats=stats,
                failed_tests=failed_tests,
                metadata=metadata
            )
            
        except subprocess.TimeoutExpired:
            return TestResult(
                success=False,
                error=f"Test execution timeout after {self._timeout}s"
            )
        except SecurityError as e:
            return TestResult(
                success=False,
                error=f"Security violation: {e.message}"
            )
        except Exception as e:
            return TestResult(
                success=False,
                error=f"Test execution failed: {type(e).__name__}: {str(e)}"
            )
    
    def _run_pytest(self, test_path: Path) -> tuple[str, int]:
        """Execute Pytest as subprocess.
        
        Args:
            test_path: Validated path to tests
            
        Returns:
            Tuple of (combined output, return code)
            
        Raises:
            subprocess.TimeoutExpired: If execution exceeds timeout
        """
        # Build command
        cmd = [
            "pytest",
            str(test_path),
            "-v",                    # Verbose output
            "--tb=short",            # Short traceback format
            "--no-header",           # No header (cleaner output)
            "--no-summary",          # We'll parse our own summary
        ]
        
        # Execute with timeout
        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=self._timeout,
            cwd=str(self._sandbox.sandbox_root)
        )
        
        # Combine stdout and stderr
        combined_output = process.stdout + "\n" + process.stderr
        
        return combined_output, process.returncode
    
    def _parse_output(self, raw_output: str) -> tuple[dict, List[FailedTest]]:
        """Parse Pytest output.
        
        Args:
            raw_output: Raw Pytest output
            
        Returns:
            Tuple of (stats dict, list of failed tests)
        """
        stats = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "errors": 0
        }
        failed_tests: List[FailedTest] = []
        
        try:
            # Parse summary line
            # Format: "5 passed, 2 failed, 1 skipped in 3.2s"
            summary_pattern = r"(\d+)\s+(passed|failed|skipped|error)"
            matches = re.findall(summary_pattern, raw_output, re.IGNORECASE)
            
            for count, status in matches:
                count = int(count)
                status = status.lower()
                
                if status == "passed":
                    stats["passed"] = count
                elif status == "failed":
                    stats["failed"] = count
                elif status == "skipped":
                    stats["skipped"] = count
                elif status == "error":
                    stats["errors"] = count
            
            # Calculate total
            stats["total"] = sum([
                stats["passed"],
                stats["failed"],
                stats["skipped"],
                stats["errors"]
            ])
            
            # Parse failed test details
            # Look for FAILED test_file.py::test_name - AssertionError
            failed_pattern = r"FAILED\s+([\w\/\.]+)::([\w_]+)\s*-\s*(.+)"
            failed_matches = re.findall(failed_pattern, raw_output)
            
            for test_file, test_name, error_info in failed_matches:
                failed_test = FailedTest(
                    test_name=test_name,
                    test_file=test_file,
                    error_message=error_info.strip()
                )
                
                # Try to extract error type
                error_type_match = re.search(r"(\w+Error|\w+Exception)", error_info)
                if error_type_match:
                    failed_test.error_type = error_type_match.group(1)
                
                failed_tests.append(failed_test)
            
            # If we couldn't parse summary, try alternative format
            if stats["total"] == 0:
                # Try: "1 failed, 1 passed in 0.12s"
                alt_pattern = r"=+\s*([\d\s\w,]+)\s+in\s+[\d\.]+s"
                alt_match = re.search(alt_pattern, raw_output)
                if alt_match:
                    summary_text = alt_match.group(1)
                    # Re-parse from this text
                    for count, status in re.findall(r"(\d+)\s+(\w+)", summary_text):
                        count = int(count)
                        if status in stats:
                            stats[status] = count
                    stats["total"] = sum([v for k, v in stats.items() if k != "total"])
        
        except Exception as e:
            # If parsing fails, return what we have
            pass
        
        return stats, failed_tests
    
    def _calculate_success_rate(self, stats: dict) -> float:
        """Calculate success rate from stats.
        
        Args:
            stats: Stats dictionary
            
        Returns:
            Success rate percentage (0.0 - 100.0)
        """
        total = stats.get("total", 0)
        if total == 0:
            return 0.0
        passed = stats.get("passed", 0)
        return (passed / total) * 100.0
    
    def check_tests_exist(self, test_path: Union[str, Path]) -> bool:
        """Check if test files exist at the given path.
        
        Args:
            test_path: Path to check
            
        Returns:
            True if test files found, False otherwise
        """
        try:
            safe_path = self._sandbox.validate_path(test_path)
            
            if safe_path.is_file():
                return safe_path.name.startswith("test_") and safe_path.suffix == ".py"
            elif safe_path.is_dir():
                # Check for any test files in directory
                test_files = list(safe_path.rglob("test_*.py"))
                return len(test_files) > 0
            
            return False
        except:
            return False


# Module-level convenience function
def run_pytest(test_path: Union[str, Path],
               sandbox: Optional[SandboxManager] = None,
               timeout: int = 60) -> TestResult:
    """Convenience function to run Pytest.
    
    Args:
        test_path: Path to test file or directory
        sandbox: Optional SandboxManager (uses global if None)
        timeout: Timeout in seconds
        
    Returns:
        TestResult
        
    Example:
        >>> from src.tools import run_pytest
        >>> result = run_pytest("tests/")
        >>> if result.all_tests_passed:
        ...     print("Success!")
    """
    from .sandbox import get_sandbox
    sandbox = sandbox or get_sandbox()
    runner = PytestRunner(sandbox, timeout=timeout)
    return runner.run_tests(test_path)


def get_test_status(test_path: Union[str, Path],
                    sandbox: Optional[SandboxManager] = None) -> bool:
    """Get test pass/fail status (convenience function).
    
    Args:
        test_path: Path to tests
        sandbox: Optional SandboxManager
        
    Returns:
        True if all tests passed, False otherwise
    """
    result = run_pytest(test_path, sandbox)
    return result.all_tests_passed if result.success else False
