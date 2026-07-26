"""
Generated from: prompts/comprehension_check.prompt
Contract rules: R1–R7
"""
from __future__ import annotations

import logging

from openai import AsyncOpenAI

from backend.config import settings
from backend.models.dag import ComprehensionResult

log = logging.getLogger(__name__)

_client = AsyncOpenAI(api_key=settings.LLM_API_KEY, base_url=settings.LLM_BASE_URL)

_SYSTEM = """
You are a comprehension evaluator for a developer learning platform.

You receive a learning node's success_criteria (a conceptual question) and a learner's
spoken answer (already transcribed to text). Return a JSON object with exactly two fields:
  verdict: "pass" | "needs_review"
  feedback: one sentence of forward-pointing feedback

Rules:
- "pass" only when the answer SUBSTANTIVELY addresses the success_criteria in the
  learner's own words, even if imperfectly phrased or accented.
- "needs_review" when the answer is empty, off-topic, incoherent, or merely repeats
  the success_criteria verbatim without demonstrating understanding.
- Feedback must be exactly ONE sentence, specific to what was actually said.
- Do NOT include the success_criteria text in the feedback.
- Do NOT ask follow-up questions in the feedback.
- Do NOT penalise filler words, grammar, or non-native phrasing — assess concept only.

Return ONLY the JSON object, no prose.
""".strip()


async def score_comprehension(
    success_criteria: str,
    transcribed_answer: str,
) -> ComprehensionResult:
    """
    R1: "pass" only for substantive understanding.
    R2: "needs_review" for empty/off-topic/incoherent answers.
    R3: Feedback is exactly one sentence, specific to what was said.
    R4: Verbatim repeats → "needs_review".
    R5: Imperfect phrasing/filler/non-native English not penalised.
    R6: success_criteria text not included in feedback.
    R7: No follow-up questions in feedback.
    """
    if not transcribed_answer.strip():
        return ComprehensionResult(
            verdict="needs_review",
            feedback="Try explaining the concept in your own words before submitting.",
        )

    response = await _client.chat.completions.create(
        model=settings.LLM_MODEL,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {
                "role": "user",
                "content": (
                    f"success_criteria: {success_criteria}\n\n"
                    f"learner answer: {transcribed_answer}"
                ),
            },
        ],
    )

    import json
    import re

    raw = (response.choices[0].message.content or "{}").strip()
    raw = re.sub(r"^```[a-z]*\n?", "", raw).rstrip("`").strip()
    data = json.loads(raw)

    return ComprehensionResult(
        verdict=data.get("verdict", "needs_review"),
        feedback=data.get("feedback", "Keep practising and try again."),
    )
