# Sandbox Guidelines

## Purpose

The `sandbox/` directory is the target folder for code analysis and refactoring experiments.

## File Structure

Each experiment requires two files:

| File | Naming Convention | Description |
|------|-------------------|-------------|
| Source code | `<name>.py` | The buggy or suboptimal code to analyze |
| Test file | `test_<name>.py` | Corresponding tests that validate the fix |

## Example

```
sandbox/
├── bad_code.py          # Contains the bug (e.g., division by zero)
└── test_bad_code.py     # Tests that will fail until the bug is fixed
```