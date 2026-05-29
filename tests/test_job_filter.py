import pytest
from src.job_filter import matches_keywords


SAMPLE_JOB = {
    "job_id": "123",
    "title": "Senior Data Scientist",
    "link": "https://example.com/123",
    "description": "We need a data scientist with Python and machine learning experience at Acme Corp in New York.",
    "pub_date": "Thu, 29 May 2026 12:00:00 GMT",
}


class TestMatchesKeywords:
    def test_no_filters_matches_everything(self):
        assert matches_keywords(SAMPLE_JOB, include=[], exclude=[]) is True

    def test_include_match_in_title(self):
        assert matches_keywords(SAMPLE_JOB, include=["data scientist"], exclude=[]) is True

    def test_include_match_in_description(self):
        assert matches_keywords(SAMPLE_JOB, include=["machine learning"], exclude=[]) is True

    def test_include_no_match(self):
        assert matches_keywords(SAMPLE_JOB, include=["blockchain"], exclude=[]) is False

    def test_include_any_match_suffices(self):
        assert matches_keywords(SAMPLE_JOB, include=["blockchain", "python"], exclude=[]) is True

    def test_exclude_rejects_match(self):
        assert matches_keywords(SAMPLE_JOB, include=[], exclude=["acme"]) is False

    def test_exclude_no_match_passes(self):
        assert matches_keywords(SAMPLE_JOB, include=[], exclude=["blockchain"]) is True

    def test_include_and_exclude_together(self):
        # Matches include but also matches exclude -> rejected
        assert matches_keywords(SAMPLE_JOB, include=["data scientist"], exclude=["new york"]) is False

    def test_case_insensitive(self):
        assert matches_keywords(SAMPLE_JOB, include=["DATA SCIENTIST"], exclude=[]) is True
        assert matches_keywords(SAMPLE_JOB, include=[], exclude=["ACME"]) is False

    def test_substring_matching(self):
        # "data" should match "data scientist"
        assert matches_keywords(SAMPLE_JOB, include=["data"], exclude=[]) is True
