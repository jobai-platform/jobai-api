from app.infrastructure.job_search.linkedin_scraper_adapter import _decode_linkedin_safety_url


def test_decode_safety_url_extracts_real_url():
    safety = (
        "https://www.linkedin.com/safety/go/"
        "?url=https%3A%2F%2Fjobs.smartrecruiters.com%2FCERN%2F744000124389628"
        "&urlhash=CuMJ&isSdui=true"
    )
    result = _decode_linkedin_safety_url(safety)
    assert result == "https://jobs.smartrecruiters.com/CERN/744000124389628"


def test_decode_safety_url_with_complex_ats_url():
    real = "https://jobs.greenhouse.io/acme/jobs/123456?gh_jid=123456"
    from urllib.parse import quote
    safety = f"https://www.linkedin.com/safety/go/?url={quote(real)}&urlhash=abc"
    result = _decode_linkedin_safety_url(safety)
    assert result == real


def test_decode_safety_url_passthrough_normal_url():
    normal = "https://www.linkedin.com/jobs/view/4407771045"
    assert _decode_linkedin_safety_url(normal) == normal


def test_decode_safety_url_passthrough_ats_url():
    ats = "https://boards.greenhouse.io/company/jobs/123"
    assert _decode_linkedin_safety_url(ats) == ats


def test_decode_safety_url_handles_empty():
    assert _decode_linkedin_safety_url("") == ""


def test_decode_safety_url_handles_malformed():
    malformed = "https://www.linkedin.com/safety/go/?nourl=foo"
    assert _decode_linkedin_safety_url(malformed) == malformed


def test_decode_safety_url_workday_example():
    real = "https://acme.wd1.myworkdayjobs.com/en-US/acme_careers/job/Software-Engineer_JR-12345"
    from urllib.parse import quote
    safety = f"https://www.linkedin.com/safety/go/?url={quote(real)}&isSdui=true"
    result = _decode_linkedin_safety_url(safety)
    assert result == real
