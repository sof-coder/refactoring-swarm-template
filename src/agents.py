
import os
from dotenv import load_dotenv
from mistralai import Mistral

from src.tools import (
    extract_issues,
    apply_fixes,
    score_solution
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
    Analyzes code and identifies bugs, security issues, and deviations
    from the task requirements.
    """
    system_prompt = (
        "You are an expert software auditor. "
        "Your job is to analyze code critically and precisely."
    )

    user_prompt = f"""
Task description:
{task_description}

Code to audit:
{code}

Instructions:
- Identify logical bugs
- Identify security issues
- Identify style or best-practice violations
- Identify mismatches with the task description
- Be concise and structured
"""

    audit_report = _chat(system_prompt, user_prompt)

    # Convert raw audit text into structured issues using tools
    issues = extract_issues(audit_report)

    return {
        "raw_report": audit_report,
        "issues": issues,
    }


def fixer_agent(code: str, issues: list) -> str:
    """
    Fixes the provided code based on issues identified by the auditor.
    """
    system_prompt = (
        "You are a senior software engineer. "
        "You fix code carefully without introducing new bugs."
    )

    user_prompt = f"""
Original code:
{code}

Identified issues:
{issues}

Instructions:
- Fix ALL listed issues
- Preserve existing behavior unless incorrect
- Improve clarity and robustness
- Return ONLY the corrected code
"""

    fixed_code = _chat(system_prompt, user_prompt)

    # Optionally post-process with tools
    fixed_code = apply_fixes(original=code, proposed=fixed_code)

    return fixed_code


def judge_agent(original_code: str, fixed_code: str, task_description: str) -> dict:
    """
    Evaluates whether the fixed code correctly solves the task
    and improves upon the original.
    """
    system_prompt = (
        "You are a strict but fair software judge. "
        "You evaluate correctness, quality, and completeness."
    )

    user_prompt = f"""
Task description:
{task_description}

Original code:
{original_code}

Fixed code:
{fixed_code}

Instructions:
- Compare original vs fixed
- Judge correctness relative to the task
- Judge code quality and safety
- Provide a final verdict
"""

    judgment = _chat(system_prompt, user_prompt)

    score = score_solution(judgment)

    return {
        "verdict": judgment,
        "score": score,
    }
