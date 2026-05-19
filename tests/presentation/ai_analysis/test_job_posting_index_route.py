from uuid import uuid4

import pytest


@pytest.mark.asyncio
async def test_post_job_posting_index_stores_embedding(ai_client, auth_headers_for, fake_vector_store):
    user_id = uuid4()
    job_posting_id = uuid4()

    response = await ai_client.post(
        f"/api/v1/job-postings/{job_posting_id}/index",
        headers=auth_headers_for(user_id),
        json={"description": "Senior Python engineer with FastAPI experience."},
    )

    assert response.status_code == 202
    assert response.json() == {"message": "indexing started"}
    assert await fake_vector_store.get_job(job_posting_id) is not None


@pytest.mark.asyncio
async def test_post_job_posting_index_rejects_empty_description(ai_client, auth_headers_for):
    response = await ai_client.post(
        f"/api/v1/job-postings/{uuid4()}/index",
        headers=auth_headers_for(uuid4()),
        json={"description": ""},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"
