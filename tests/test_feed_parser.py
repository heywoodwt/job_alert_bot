import pytest
from src.feed_parser import parse_job_cards, strip_html, _clean_job_url


SAMPLE_HTML = """<!DOCTYPE html>
<li>
  <div class="base-card base-search-card job-search-card"
       data-entity-urn="urn:li:jobPosting:111">
    <a class="base-card__full-link"
       href="https://www.linkedin.com/jobs/view/data-scientist-at-acme-corp-111?position=1&amp;pageNum=0&amp;refId=abc123">
      <span class="sr-only">Data Scientist</span>
    </a>
    <div class="base-search-card__info">
      <h3 class="base-search-card__title">Data Scientist</h3>
      <h4 class="base-search-card__subtitle">
        <a href="https://www.linkedin.com/company/acme-corp">Acme Corp</a>
      </h4>
      <div class="base-search-card__metadata">
        <span class="job-search-card__location">New York, NY</span>
        <time class="job-search-card__listdate" datetime="2026-05-29">1 day ago</time>
      </div>
    </div>
  </div>
</li>
<li>
  <div class="base-card base-search-card job-search-card"
       data-entity-urn="urn:li:jobPosting:222">
    <a class="base-card__full-link"
       href="https://www.linkedin.com/jobs/view/ml-engineer-at-beta-inc-222?position=2&amp;pageNum=0">
      <span class="sr-only">ML Engineer</span>
    </a>
    <div class="base-search-card__info">
      <h3 class="base-search-card__title">ML Engineer</h3>
      <h4 class="base-search-card__subtitle">
        <a href="https://www.linkedin.com/company/beta-inc">Beta Inc</a>
      </h4>
      <div class="base-search-card__metadata">
        <span class="job-search-card__location">San Francisco, CA</span>
        <time class="job-search-card__listdate--new" datetime="2026-05-28">2 days ago</time>
      </div>
    </div>
  </div>
</li>
"""


class TestStripHtml:
    def test_removes_tags(self):
        assert strip_html("<p>Hello <b>world</b></p>") == "Hello world"

    def test_plain_text_unchanged(self):
        assert strip_html("no tags here") == "no tags here"

    def test_empty_string(self):
        assert strip_html("") == ""

    def test_nested_tags(self):
        assert strip_html("<div><p><span>text</span></p></div>") == "text"


class TestCleanJobUrl:
    def test_removes_tracking_params(self):
        url = "https://www.linkedin.com/jobs/view/data-scientist-111?position=1&pageNum=0&refId=abc"
        assert _clean_job_url(url) == "https://www.linkedin.com/jobs/view/data-scientist-111"

    def test_clean_url_unchanged(self):
        url = "https://www.linkedin.com/jobs/view/data-scientist-111"
        assert _clean_job_url(url) == url


class TestParseJobCards:
    def test_parses_correct_number_of_cards(self):
        entries = parse_job_cards(SAMPLE_HTML)
        assert len(entries) == 2

    def test_first_entry_fields(self):
        entries = parse_job_cards(SAMPLE_HTML)
        entry = entries[0]
        assert entry["job_id"] == "urn:li:jobPosting:111"
        assert entry["title"] == "Data Scientist"
        assert entry["link"] == "https://www.linkedin.com/jobs/view/data-scientist-at-acme-corp-111"
        assert "Acme Corp" in entry["description"]
        assert "New York, NY" in entry["description"]
        assert entry["pub_date"] == "2026-05-29"

    def test_second_entry_fields(self):
        entries = parse_job_cards(SAMPLE_HTML)
        entry = entries[1]
        assert entry["job_id"] == "urn:li:jobPosting:222"
        assert entry["title"] == "ML Engineer"
        assert "Beta Inc" in entry["description"]
        assert "San Francisco, CA" in entry["description"]
        assert entry["pub_date"] == "2026-05-28"

    def test_tracking_params_stripped_from_link(self):
        entries = parse_job_cards(SAMPLE_HTML)
        assert "position=" not in entries[0]["link"]
        assert "refId=" not in entries[0]["link"]

    def test_empty_html_returns_empty_list(self):
        entries = parse_job_cards("<html><body></body></html>")
        assert entries == []

    def test_html_with_no_job_cards_returns_empty(self):
        entries = parse_job_cards("<div class='other-content'>Hello</div>")
        assert entries == []
