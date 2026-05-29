import os
import time
from datetime import datetime, timezone

import boto3

from src.feed_parser import fetch_and_parse_feeds
from src.job_filter import matches_keywords
from src.notifier import publish_job_alert


def _parse_keywords(env_var: str) -> list[str]:
    """Parse a comma-separated env var into a list of stripped, non-empty strings."""
    raw = os.environ.get(env_var, "")
    return [kw.strip() for kw in raw.split(",") if kw.strip()]


def _get_new_jobs(jobs: list[dict], table) -> list[dict]:
    """Filter out jobs that are already in DynamoDB."""
    new_jobs = []
    for job in jobs:
        response = table.get_item(Key={"job_id": job["job_id"]})
        if "Item" not in response:
            new_jobs.append(job)
    return new_jobs


def _store_jobs(jobs: list[dict], table) -> None:
    """Write job IDs to DynamoDB with a 30-day TTL."""
    now = datetime.now(timezone.utc)
    ttl = int(time.time()) + 86400 * 30  # 30 days from now
    with table.batch_writer() as batch:
        for job in jobs:
            batch.put_item(Item={
                "job_id": job["job_id"],
                "title": job["title"],
                "link": job["link"],
                "first_seen_at": now.isoformat(),
                "ttl": ttl,
            })


def lambda_handler(event, context):
    """Lambda entry point. Fetches feeds, filters, and notifies."""
    feed_urls = [u.strip() for u in os.environ["FEED_URLS"].split(",") if u.strip()]
    include_keywords = _parse_keywords("INCLUDE_KEYWORDS")
    exclude_keywords = _parse_keywords("EXCLUDE_KEYWORDS")
    topic_arn = os.environ["SNS_TOPIC_ARN"]
    table_name = os.environ["DYNAMODB_TABLE"]

    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(table_name)

    # Fetch and parse all feeds
    all_jobs = fetch_and_parse_feeds(feed_urls)
    print(f"Fetched {len(all_jobs)} jobs from {len(feed_urls)} feed(s)")

    # Filter out already-seen jobs
    new_jobs = _get_new_jobs(all_jobs, table)
    print(f"Found {len(new_jobs)} new jobs")

    # Apply keyword filters
    matching_jobs = [
        job for job in new_jobs
        if matches_keywords(job, include=include_keywords, exclude=exclude_keywords)
    ]
    print(f"Matched {len(matching_jobs)} jobs after keyword filtering")

    # Store ALL new jobs (matching or not) to prevent re-processing
    if new_jobs:
        _store_jobs(new_jobs, table)

    # Send notifications for matching jobs
    for job in matching_jobs:
        publish_job_alert(job, topic_arn)
        print(f"Notified: {job['title']}")

    return {
        "fetched": len(all_jobs),
        "new": len(new_jobs),
        "matched": len(matching_jobs),
    }
