# Job Alert Bot

A serverless pipeline that watches LinkedIn's public job listings, filters postings
against keyword rules, and emails me the matches. Built during my MSDS job search so
I would stop refreshing job boards by hand.

It runs every 15 minutes on AWS Lambda and costs nothing — the whole thing fits inside
the free tier.

## Architecture

```
EventBridge (rate: 15 min)
        │
        ▼
   Lambda (Python 3.12)
        │
        ├─ 1. Fetch LinkedIn guest jobs API for each configured search
        ├─ 2. Parse job cards out of the HTML response (BeautifulSoup)
        ├─ 3. Deduplicate within the batch, then against DynamoDB
        ├─ 4. Apply include / exclude keyword filters
        ├─ 5. Write every new job ID to DynamoDB (30-day TTL)
        └─ 6. Publish matches to SNS
                    │
                    ▼
              Email subscription
```

Everything is defined in `template.yaml` and deployed with AWS SAM — Lambda, the
EventBridge schedule, the DynamoDB table, the SNS topic, and the email subscription.

**Deduplication** is the part that matters. Every new job ID gets written to DynamoDB
whether or not it matched the filters, so a posting is only ever evaluated once. Rows
carry a 30-day TTL, which keeps the table from growing without bound and lets DynamoDB
do the cleanup for free.

## Layout

| Path | Responsibility |
|------|----------------|
| `src/handler.py` | Lambda entry point; orchestrates the pipeline |
| `src/feed_parser.py` | Fetches feeds, parses job cards, strips HTML and tracking params |
| `src/job_filter.py` | Include/exclude keyword matching |
| `src/notifier.py` | Formats and publishes SNS messages |
| `template.yaml` | SAM template for all AWS resources |
| `tests/` | 31 pytest cases; AWS calls stubbed with `moto` |

## Configuration

All behavior is driven by environment variables set through SAM parameters:

| Variable | Purpose |
|----------|---------|
| `FEED_URLS` | Comma-separated LinkedIn search URLs to poll |
| `INCLUDE_KEYWORDS` | Comma-separated; a job must match at least one (empty = match all) |
| `EXCLUDE_KEYWORDS` | Comma-separated; any match rejects the job |
| `SNS_TOPIC_ARN` | Topic to publish alerts to |
| `DYNAMODB_TABLE` | Table holding seen job IDs |

## Running it

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install pytest moto

pytest                      # run the test suite (31 tests)

cp samconfig.toml.example samconfig.toml   # then edit keywords, feeds, and email
sam build && sam deploy --guided
```

Tear down with `sam delete --stack-name job-alert-bot`.

## Notes

`samconfig.toml` is gitignored because it holds the notification email address; the
committed `.example` shows the shape. No credentials live in this repo — Lambda gets
its DynamoDB and SNS permissions from the IAM policies in `template.yaml`.

