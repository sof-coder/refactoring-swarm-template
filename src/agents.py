
import os
from dotenv import load_dotenv
from mistralai import Mistral

from src.tools import (
    run_pylint,
    get_quality_score,
    run_pytest,
)
from src.utils.logger import log_experiment, ActionType

# Load environment variables
load_dotenv()

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
MODEL_NAME = os.getenv("MISTRAL_MODEL", "mistral-large-latest")

# Initialize Mistral client
client = Mistral(api_key=MISTRAL_API_KEY)


def _chat(system_prompt: str, user_prompt: str) -> str:
    """
    Internal helper to query Mistral with a system + user prompt.
    """
    response = client.chat.complete(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
    )
    return response.choices[0].message.content.strip()


def auditor_agent(code: str, task_description: str) -> dict:
    """
    Analyzes code using static analysis tools and returns issues and score.
    """
    # Write code to a temp file in sandbox for analysis
    import tempfile
    from pathlib import Path
    from src.tools import initialize_sandbox

    sandbox = initialize_sandbox("./sandbox")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".py", dir="./sandbox") as tmp:
        tmp.write(code.encode("utf-8"))
        tmp_path = Path(tmp.name)

    analysis = run_pylint(tmp_path, sandbox)
    os.unlink(tmp_path)
    
    # Log the auditor action
    result = {
        "issues": [issue.to_dict() for issue in analysis.issues],
        "score": analysis.score,
        "success": analysis.success,
        "error": analysis.error,
        "metadata": analysis.metadata,
    }
    
    log_experiment(
        agent_name="Auditor",
        model_used="pylint",
        action=ActionType.ANALYSIS,
        details={
            "input_prompt": f"Analyzing code for task: {task_description}",
            "output_response": f"Found {len(result['issues'])} issues. Score: {result['score']}"
        },
        status="SUCCESS" if result["success"] else "FAILURE"
    )
    
    return result


def fixer_agent(code: str, issues: list) -> str:
    """
    Attempts to auto-fix code using tools in the tools folder.
    Currently removes unused imports if detected by issues.
    """
    import tempfile
    from pathlib import Path
    from src.tools import initialize_sandbox, read_file, write_file

    sandbox = initialize_sandbox("./sandbox")
    # Write code to temp file in sandbox
    with tempfile.NamedTemporaryFile(delete=False, suffix=".py", dir="./sandbox") as tmp:
        tmp.write(code.encode("utf-8"))
        tmp_path = Path(tmp.name)

    # Detect unused imports from issues
    unused_import_lines = set()
    for issue in issues:
        if issue.get("symbol") == "unused-import":
            unused_import_lines.add(issue.get("line"))

    # If no unused imports, return code as is
    if not unused_import_lines:
        os.unlink(tmp_path)
        log_experiment(
            agent_name="Fixer",
            model_used="auto-fixer",
            action=ActionType.FIX,
            details={
                "input_prompt": f"Attempting to fix {len(issues)} issues",
                "output_response": "No unused imports to fix. Code returned unchanged."
            },
            status="SUCCESS"
        )
        return code

    # Read code lines
    result = read_file(tmp_path, sandbox)
    if not result.success:
        os.unlink(tmp_path)
        log_experiment(
            agent_name="Fixer",
            model_used="auto-fixer",
            action=ActionType.FIX,
            details={
                "input_prompt": f"Attempting to fix {len(issues)} issues",
                "output_response": f"Failed to read file: {result.error}"
            },
            status="FAILURE"
        )
        return code
    lines = result.content.splitlines()

    # Remove lines with unused imports
    fixed_lines = [line for idx, line in enumerate(lines, 1) if idx not in unused_import_lines]
    fixed_code = "\n".join(fixed_lines)

    os.unlink(tmp_path)
    
    log_experiment(
        agent_name="Fixer",
        model_used="auto-fixer",
        action=ActionType.FIX,
        details={
            "input_prompt": f"Removing {len(unused_import_lines)} unused import(s) from lines {sorted(unused_import_lines)}",
            "output_response": f"Successfully removed unused imports. Fixed code length: {len(fixed_code)} chars"
        },
        status="SUCCESS"
    )
    
    return fixed_code


def judge_agent(original_code: str, fixed_code: str, task_description: str) -> dict:
    """
    Evaluates the fixed code using static analysis and testing tools.
    """
    import tempfile
    from pathlib import Path
    from src.tools import initialize_sandbox

    sandbox = initialize_sandbox("./sandbox")
    # Write fixed code to temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".py", dir="./sandbox") as tmp:
        tmp.write(fixed_code.encode("utf-8"))
        tmp_path = Path(tmp.name)

    analysis = run_pylint(tmp_path, sandbox)
    os.unlink(tmp_path)
    
    result = {
        "score": analysis.score,
        "issues": [issue.to_dict() for issue in analysis.issues],
        "success": analysis.success,
        "error": analysis.error,
        "metadata": analysis.metadata,
    }
    
    log_experiment(
        agent_name="Judge",
        model_used="pylint",
        action=ActionType.DEBUG,
        details={
            "input_prompt": f"Evaluating fixed code for task: {task_description}",
            "output_response": f"Final score: {result['score']}, Issues remaining: {len(result['issues'])}"
        },
        status="SUCCESS" if result["success"] else "FAILURE"
    )
    
    return result