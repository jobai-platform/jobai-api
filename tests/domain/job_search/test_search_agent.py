import pytest
from uuid import uuid4
from datetime import datetime, timezone

from app.domain.job_search.search_agent import SearchAgent


def _make_agent(**kwargs) -> SearchAgent:
    defaults = dict(candidate_id=uuid4(), keywords="python developer", location="Zurich")
    return SearchAgent(**{**defaults, **kwargs})


# ---------------------------------------------------------------------------
# Creation
# ---------------------------------------------------------------------------

def test_search_agent_created_with_defaults():
    agent = _make_agent()
    assert agent.remote_only is False
    assert agent.date_posted_within_days == 7
    assert agent.limit == 25
    assert agent.is_active is True
    assert agent.last_run_at is None
    assert agent.id is None


def test_search_agent_requires_candidate_id():
    agent = _make_agent(candidate_id=uuid4())
    assert agent.candidate_id is not None


def test_search_agent_timestamps_set_on_creation():
    before = datetime.now(timezone.utc)
    agent = _make_agent()
    after = datetime.now(timezone.utc)
    assert before <= agent.created_at <= after
    assert before <= agent.updated_at <= after


# ---------------------------------------------------------------------------
# Validation — keywords
# ---------------------------------------------------------------------------

def test_empty_keywords_raises():
    with pytest.raises(ValueError, match="keywords cannot be empty"):
        _make_agent(keywords="")


def test_whitespace_only_keywords_raises():
    with pytest.raises(ValueError, match="keywords cannot be empty"):
        _make_agent(keywords="   ")


# ---------------------------------------------------------------------------
# Validation — location
# ---------------------------------------------------------------------------

def test_empty_location_raises():
    with pytest.raises(ValueError, match="location cannot be empty"):
        _make_agent(location="")


def test_whitespace_only_location_raises():
    with pytest.raises(ValueError, match="location cannot be empty"):
        _make_agent(location="   ")


# ---------------------------------------------------------------------------
# Validation — limit
# ---------------------------------------------------------------------------

def test_limit_below_1_raises():
    with pytest.raises(ValueError, match="limit must be between 1 and 100"):
        _make_agent(limit=0)


def test_limit_above_100_raises():
    with pytest.raises(ValueError, match="limit must be between 1 and 100"):
        _make_agent(limit=101)


def test_limit_boundary_1_is_valid():
    agent = _make_agent(limit=1)
    assert agent.limit == 1


def test_limit_boundary_100_is_valid():
    agent = _make_agent(limit=100)
    assert agent.limit == 100


# ---------------------------------------------------------------------------
# Validation — date_posted_within_days
# ---------------------------------------------------------------------------

def test_date_posted_within_days_below_1_raises():
    with pytest.raises(ValueError, match="date_posted_within_days must be between 1 and 30"):
        _make_agent(date_posted_within_days=0)


def test_date_posted_within_days_above_30_raises():
    with pytest.raises(ValueError, match="date_posted_within_days must be between 1 and 30"):
        _make_agent(date_posted_within_days=31)


def test_date_posted_within_days_boundary_1_is_valid():
    agent = _make_agent(date_posted_within_days=1)
    assert agent.date_posted_within_days == 1


def test_date_posted_within_days_boundary_30_is_valid():
    agent = _make_agent(date_posted_within_days=30)
    assert agent.date_posted_within_days == 30


# ---------------------------------------------------------------------------
# update() method
# ---------------------------------------------------------------------------

def test_update_keywords():
    agent = _make_agent()
    agent.update(keywords="data engineer")
    assert agent.keywords == "data engineer"


def test_update_location():
    agent = _make_agent()
    agent.update(location="Geneva")
    assert agent.location == "Geneva"


def test_update_remote_only():
    agent = _make_agent()
    agent.update(remote_only=True)
    assert agent.remote_only is True


def test_update_limit():
    agent = _make_agent()
    agent.update(limit=50)
    assert agent.limit == 50


def test_update_date_posted_within_days():
    agent = _make_agent()
    agent.update(date_posted_within_days=14)
    assert agent.date_posted_within_days == 14


def test_update_sets_updated_at():
    agent = _make_agent()
    before = agent.updated_at
    agent.update(keywords="backend engineer")
    assert agent.updated_at >= before


def test_update_none_values_do_not_overwrite():
    agent = _make_agent(keywords="python", location="Zurich", limit=10)
    agent.update(remote_only=True)
    assert agent.keywords == "python"
    assert agent.location == "Zurich"
    assert agent.limit == 10


def test_update_invalid_keywords_raises():
    agent = _make_agent()
    with pytest.raises(ValueError, match="keywords cannot be empty"):
        agent.update(keywords="")


def test_update_invalid_limit_raises():
    agent = _make_agent()
    with pytest.raises(ValueError, match="limit must be between 1 and 100"):
        agent.update(limit=200)


# ---------------------------------------------------------------------------
# mark_ran() method
# ---------------------------------------------------------------------------

def test_mark_ran_sets_last_run_at():
    agent = _make_agent()
    assert agent.last_run_at is None
    before = datetime.now(timezone.utc)
    agent.mark_ran()
    after = datetime.now(timezone.utc)
    assert agent.last_run_at is not None
    assert before <= agent.last_run_at <= after


def test_mark_ran_updates_updated_at():
    agent = _make_agent()
    before = agent.updated_at
    agent.mark_ran()
    assert agent.updated_at >= before
