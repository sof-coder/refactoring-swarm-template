
import os
from dotenv import load_dotenv
from mistralai import Mistral

from src.tools import (
    run_pylint,
    get_quality_score,
    run_pytest,
    get_test_status
)

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
    return {
        "issues": [issue.to_dict() for issue in analysis.issues],
        "score": analysis.score,
        "success": analysis.success,
        "error": analysis.error,
        "metadata": analysis.metadata,
    }


def fixer_agent(code: str, issues: list) -> str:
    """
    This agent is now a placeholder, as automated fixing is not implemented in tools.
    Returns the original code unchanged.
    """
    # In a real system, you could implement auto-fixes using analysis results.
    return code


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
    # Optionally, run tests if available (not implemented here)
    os.unlink(tmp_path)
    return {
        "score": analysis.score,
        "issues": [issue.to_dict() for issue in analysis.issues],
        "success": analysis.success,
        "error": analysis.error,
        "metadata": analysis.metadata,
    }
