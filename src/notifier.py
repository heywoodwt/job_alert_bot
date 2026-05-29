import boto3


def format_message(job: dict) -> str:
    """Format a job dict into a human-readable notification message."""
    return (
        f"New Job Alert!\n"
        f"\n"
        f"Title: {job['title']}\n"
        f"Posted: {job['pub_date']}\n"
        f"\n"
        f"Description:\n"
        f"{job['description']}\n"
        f"\n"
        f"Apply: {job['link']}\n"
    )


def publish_job_alert(job: dict, topic_arn: str) -> None:
    """Publish a job alert to the specified SNS topic."""
    sns = boto3.client("sns")
    subject = f"Job Alert: {job['title']}"
    # SNS subject has a 100-character limit
    if len(subject) > 100:
        subject = subject[:97] + "..."
    sns.publish(
        TopicArn=topic_arn,
        Subject=subject,
        Message=format_message(job),
    )
