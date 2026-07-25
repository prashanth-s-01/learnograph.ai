"""
Tests for backend/agents/comprehension.py
Contract rules covered: R1, R2, R3, R4, R5
"""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.models.dag import ComprehensionResult

SUCCESS_CRITERIA = "Can explain what useEffect's dependency array does and why it matters"


def _mock_llm(verdict: str, feedback: str):
    mock = MagicMock()
    mock.choices = [MagicMock()]
    mock.choices[0].message.content = json.dumps({"verdict": verdict, "feedback": feedback})
    return mock


@pytest.mark.asyncio
async def test_R1_pass_for_substantive_answer():
    """R1: Returns 'pass' when answer substantively addresses success_criteria."""
    with patch("backend.agents.comprehension._client") as mock_client:
        mock_client.chat.completions.create = AsyncMock(
            return_value=_mock_llm("pass", "Great job explaining the stale closure problem.")
        )
        from backend.agents.comprehension import score_comprehension
        result = await score_comprehension(
            SUCCESS_CRITERIA,
            "The dependency array tells React when to re-run the effect. If you put a variable in "
            "there, the effect runs again whenever that variable changes. Without it, you get stale "
            "closures or infinite loops.",
        )
        assert result.verdict == "pass"
        assert isinstance(result, ComprehensionResult)


@pytest.mark.asyncio
async def test_R2_needs_review_for_empty_answer():
    """R2: Returns 'needs_review' for empty answer without calling MiniMax."""
    from backend.agents.comprehension import score_comprehension
    result = await score_comprehension(SUCCESS_CRITERIA, "")
    assert result.verdict == "needs_review"


@pytest.mark.asyncio
async def test_R2_needs_review_for_offtopic_answer():
    """R2: Returns 'needs_review' for off-topic or incoherent answer."""
    with patch("backend.agents.comprehension._client") as mock_client:
        mock_client.chat.completions.create = AsyncMock(
            return_value=_mock_llm("needs_review", "Your answer was about cooking, not React.")
        )
        from backend.agents.comprehension import score_comprehension
        result = await score_comprehension(SUCCESS_CRITERIA, "I love pasta carbonara.")
        assert result.verdict == "needs_review"


@pytest.mark.asyncio
async def test_R3_feedback_is_one_sentence():
    """R3: Feedback is exactly one sentence."""
    with patch("backend.agents.comprehension._client") as mock_client:
        mock_client.chat.completions.create = AsyncMock(
            return_value=_mock_llm("pass", "You correctly explained the re-run trigger behaviour.")
        )
        from backend.agents.comprehension import score_comprehension
        result = await score_comprehension(SUCCESS_CRITERIA, "The array controls re-runs.")
        sentences = [s.strip() for s in result.feedback.split(".") if s.strip()]
        assert len(sentences) <= 2, f"Feedback has more than one sentence: {result.feedback!r}"


@pytest.mark.asyncio
async def test_R4_verbatim_repeat_does_not_pass():
    """R4: Verbatim repetition of success_criteria does not earn 'pass'."""
    with patch("backend.agents.comprehension._client") as mock_client:
        mock_client.chat.completions.create = AsyncMock(
            return_value=_mock_llm(
                "needs_review",
                "Try explaining this in your own words to show real understanding.",
            )
        )
        from backend.agents.comprehension import score_comprehension
        result = await score_comprehension(SUCCESS_CRITERIA, SUCCESS_CRITERIA)
        assert result.verdict == "needs_review"


@pytest.mark.asyncio
async def test_R5_imperfect_phrasing_does_not_penalise():
    """R5: Filler words and imperfect grammar don't block 'pass'."""
    with patch("backend.agents.comprehension._client") as mock_client:
        mock_client.chat.completions.create = AsyncMock(
            return_value=_mock_llm("pass", "Your core understanding is correct despite informal phrasing.")
        )
        from backend.agents.comprehension import score_comprehension
        result = await score_comprehension(
            SUCCESS_CRITERIA,
            "um, so like, the array thing, uh, it tells React when to redo the effect, yeah.",
        )
        assert result.verdict == "pass"
