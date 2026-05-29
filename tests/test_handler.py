import json
import os
import time
from datetime import datetime, timezone

import boto3
import pytest
from moto import mock_aws

from tests.test_feed_parser import SAMPLE_HTML


@mock_aws
class TestHandler:
    def _setup_aws(self):
        """Create mock DynamoDB table and SNS topic."""
        dynamodb = boto3.client("dynamodb", region_name="us-east-1")
        dynamodb.create_table(
            TableName="job-alert-seen-jobs",
            KeySchema=[{"AttributeName": "job_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "job_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )

        sns = boto3.client("sns", region_name="us-east-1")
        topic = sns.create_topic(Name="job-alerts")
        return topic["TopicArn"]

    def _set_env(self, topic_arn):
        """Set required environment variables."""
        os.environ["FEED_URLS"] = "https://example.com/feed"
        os.environ["INCLUDE_KEYWORDS"] = "data scientist"
        os.environ["EXCLUDE_KEYWORDS"] = ""
        os.environ["SNS_TOPIC_ARN"] = topic_arn
        os.environ["DYNAMODB_TABLE"] = "job-alert-seen-jobs"
        os.environ["AWS_DEFAULT_REGION"] = "us-east-1"

    def test_handler_stores_seen_jobs(self):
        topic_arn = self._setup_aws()
        self._set_env(topic_arn)

        import unittest.mock as mock
        with mock.patch("src.handler.fetch_and_parse_feeds") as mock_fetch:
            mock_fetch.return_value = [
                {
                    "job_id": "job-111",
                    "title": "Data Scientist at Acme",
                    "link": "https://linkedin.com/jobs/view/111",
                    "description": "Data scientist role with Python.",
                    "pub_date": "Thu, 29 May 2026 12:00:00 GMT",
                },
            ]

            from src.handler import lambda_handler
            lambda_handler({}, None)

            # Verify job was stored in DynamoDB
            dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
            table = dynamodb.Table("job-alert-seen-jobs")
            response = table.get_item(Key={"job_id": "job-111"})
            assert "Item" in response

    def test_handler_skips_already_seen_jobs(self):
        topic_arn = self._setup_aws()
        self._set_env(topic_arn)

        # Pre-populate DynamoDB with a seen job
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        table = dynamodb.Table("job-alert-seen-jobs")
        table.put_item(Item={
            "job_id": "job-111",
            "title": "Data Scientist at Acme",
            "link": "https://linkedin.com/jobs/view/111",
            "first_seen_at": datetime.now(timezone.utc).isoformat(),
            "ttl": int(time.time()) + 86400 * 30,
        })

        import unittest.mock as mock
        with mock.patch("src.handler.fetch_and_parse_feeds") as mock_fetch, \
             mock.patch("src.notifier.boto3") as mock_boto3:
            mock_fetch.return_value = [
                {
                    "job_id": "job-111",
                    "title": "Data Scientist at Acme",
                    "link": "https://linkedin.com/jobs/view/111",
                    "description": "Data scientist role with Python.",
                    "pub_date": "Thu, 29 May 2026 12:00:00 GMT",
                },
            ]

            from src.handler import lambda_handler
            lambda_handler({}, None)

            # SNS publish should NOT have been called
            mock_sns = mock_boto3.client.return_value
            mock_sns.publish.assert_not_called()

    def test_handler_filters_non_matching_jobs(self):
        topic_arn = self._setup_aws()
        self._set_env(topic_arn)

        import unittest.mock as mock
        with mock.patch("src.handler.fetch_and_parse_feeds") as mock_fetch, \
             mock.patch("src.notifier.boto3") as mock_boto3:
            mock_fetch.return_value = [
                {
                    "job_id": "job-333",
                    "title": "Blockchain Developer",
                    "link": "https://linkedin.com/jobs/view/333",
                    "description": "Blockchain and crypto role.",
                    "pub_date": "Thu, 29 May 2026 12:00:00 GMT",
                },
            ]

            from src.handler import lambda_handler
            lambda_handler({}, None)

            # SNS publish should NOT have been called (no keyword match)
            mock_sns = mock_boto3.client.return_value
            mock_sns.publish.assert_not_called()

            # But the job should still be stored in DynamoDB
            dynamodb_resource = boto3.resource("dynamodb", region_name="us-east-1")
            table = dynamodb_resource.Table("job-alert-seen-jobs")
            response = table.get_item(Key={"job_id": "job-333"})
            assert "Item" in response
