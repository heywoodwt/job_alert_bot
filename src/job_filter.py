def matches_keywords(
    job: dict,
    include: list[str],
    exclude: list[str],
) -> bool:
    """Check if a job matches include/exclude keyword filters.

    Args:
        job: Dict with 'title' and 'description' keys.
        include: Keywords where at least one must be present. Empty list means no include filter.
        exclude: Keywords where none may be present. Empty list means no exclude filter.

    Returns:
        True if the job passes both filters.
    """
    text = (job.get("title", "") + " " + job.get("description", "")).lower()

    if include and not any(kw.lower() in text for kw in include):
        return False

    if exclude and any(kw.lower() in text for kw in exclude):
        return False

    return True
