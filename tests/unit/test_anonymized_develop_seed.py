from app.infrastructure.seeding.anonymized_develop import build_anonymized_develop_seed


def test_anonymized_develop_seed_is_deterministic_and_synthetic() -> None:
    seed = build_anonymized_develop_seed()

    assert len(seed.users) == 1
    assert len(seed.candidate_profiles) == 1
    assert len(seed.billing_prices) == 1
    assert len(seed.subscriptions) == 1
    assert len(seed.search_agents) == 1
    assert len(seed.job_postings) == 2
    assert len(seed.candidate_embeddings) == 1
    assert len(seed.job_embeddings) == 2
    assert len(seed.ai_analyses) == 1

    user = seed.users[0]
    assert user.email == "candidate.001@example.test"
    assert user.username == "candidate_001"
    assert user.linkedin_id is None
    assert user.stripe_customer_id is None
    assert user.avatar_url is None

    profile = seed.candidate_profiles[0]
    assert profile.current_title == "Backend Engineer"
    assert profile.remote_preference == "hybrid"
    assert profile.skills == ["python", "fastapi", "postgresql", "docker"]

    search_agent = seed.search_agents[0]
    assert search_agent.keywords == "python fastapi postgresql"
    assert search_agent.location == "Zurich, Switzerland"

    job_titles = {job.title for job in seed.job_postings}
    assert job_titles == {"Backend Engineer", "Frontend Engineer"}
    assert all(len(embedding.vector) == 768 for embedding in seed.candidate_embeddings)
    assert all(len(embedding.vector) == 768 for embedding in seed.job_embeddings)
    assert seed.ai_analyses[0].status == "completed"
    assert seed.ai_analyses[0].quality_tier == "balanced"

