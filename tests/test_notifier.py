import boto3
import pytest
from moto import mock_aws

from src.notifier import format_message, publish_job_alert


SAMPLE_JOB = {
    "job_id": "123",
    "title": "Senior Data Scientist",
    "link": "https://www.linkedin.com/jobs/view/123",
    "description": "We need a data scientist with Python and ML experience at Acme Corp in New York.",
    "pub_date": "Thu, 29 May 2026 12:00:00 GMT",
}


class TestFormatMessage:
    def test_contains_title(self):
        msg = format_message(SAMPLE_JOB)
        assert "Senior Data Scientist" in msg

    def test_contains_link(self):
        msg = format_message(SAMPLE_JOB)
        assert "https://www.linkedin.com/jobs/view/123" in msg

    def test_contains_description(self):
        msg = format_message(SAMPLE_JOB)
        assert "Python and ML experience" in msg

    def test_contains_pub_date(self):
        msg = format_message(SAMPLE_JOB)
        assert "Thu, 29 May 2026 12:00:00 GMT" in msg


class TestPublishJobAlert:
    @mock_aws
    def test_publishes_to_sns(self):
        sns = boto3.client("sns", region_name="us-east-1")
        topic = sns.create_topic(Name="job-alerts")
        topic_arn = topic["TopicArn"]

        publish_job_alert(SAMPLE_JOB, topic_arn)

        # Verify no exception was raised; moto doesn't store messages
        # for easy retrieval, but the call succeeding is the test.

    @mock_aws
    def test_subject_contains_job_title(self):
        sns = boto3.client("sns", region_name="us-east-1")
        topic = sns.create_topic(Name="job-alerts")
        topic_arn = topic["TopicArn"]

        # Patch to capture the publish call
        import unittest.mock as mock
        with mock.patch("src.notifier.boto3") as mock_boto3:
            mock_sns = mock.MagicMock()
            mock_boto3.client.return_value = mock_sns

            publish_job_alert(SAMPLE_JOB, topic_arn)

            mock_sns.publish.assert_called_once()
            call_kwargs = mock_sns.publish.call_args[1]
            assert call_kwargs["Subject"] == "Job Alert: Senior Data Scientist"
            assert topic_arn in call_kwargs["TopicArn"]
