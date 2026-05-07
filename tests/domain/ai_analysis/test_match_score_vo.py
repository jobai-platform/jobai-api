from dataclasses import FrozenInstanceError

import pytest

from app.domain.ai_analysis.value_objects import MatchScore


def test_match_score_valid_all_dimensions():
    """MatchScore accepte des scores valides pour toutes les dimensions"""
    score = MatchScore(
        overall=0.85,
        skills_score=0.9,
        experience_score=0.8,
        location_score=1.0,
        salary_score=0.75,
        explanation="Strong match on skills and location"
    )
    assert score.overall == 0.85
    assert score.skills_score == 0.9

def test_match_score_rejects_negative_overall():
    """MatchScore refuse overall < 0.0"""
    with pytest.raises(ValueError, match="must be between 0.0 and 1.0"):
        MatchScore(
            overall=-0.1,
            skills_score=0.5,
            experience_score=0.5,
            location_score=0.5,
            salary_score=0.5,
            explanation=""
        )

def test_match_score_rejects_above_one_skills():
    """MatchScore denied skills_score > 1.0"""
    with pytest.raises(ValueError, match="must be between 0.0 and 1.0"):
        MatchScore(
            overall=0.5,
            skills_score=1.1,
            experience_score=0.5,
            location_score=0.5,
            salary_score=0.5,
            explanation=""
        )

def test_match_score_equality():
    """Two MatchScore instances with the same values are equal (Value Object)"""
    score1 = MatchScore(0.8, 0.9, 0.7, 1.0, 0.6, "Good match")
    score2 = MatchScore(0.8, 0.9, 0.7, 1.0, 0.6, "Good match")
    assert score1 == score2

def test_match_score_immutability():
    """MatchScore is immutable (FrozenInstance)"""
    score = MatchScore(0.8, 0.9, 0.7, 1.0, 0.6, "Good match")
    with pytest.raises(FrozenInstanceError):
        score.overall = 0.9

def test_match_score_all_scores_at_zero():
    """MatchScore accept all scores of 0.0 (no match)"""
    score = MatchScore(0.0, 0.0, 0.0, 0.0, 0.0, "No match")
    assert score.overall == 0.0

def test_match_score_all_scores_at_one():
    """MatchScore accept all scores of 1.0 (perfect match)"""
    score = MatchScore(1.0, 1.0, 1.0, 1.0, 1.0, "Perfect match")
    assert score.overall == 1.0
