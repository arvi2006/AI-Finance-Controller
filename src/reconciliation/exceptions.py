import pandas as pd


def filter_unresolved(exceptions):
    """Filter exceptions that are not yet resolved."""
    if exceptions.empty:
        return exceptions
    return exceptions[exceptions["final_status"].isna() | (exceptions["final_status"] == "")]


def filter_by_priority(exceptions, min_priority="P2_MEDIUM"):
    """Keep only exceptions at or above the given priority level.

    Priority order (highest to lowest): P0_CRITICAL > P1_HIGH > P2_MEDIUM > P3_AI_INVESTIGATED > P4_NORMAL
    """
    priority_order = {"P0_CRITICAL": 0, "P1_HIGH": 1, "P2_MEDIUM": 2, "P3_AI_INVESTIGATED": 3, "P4_NORMAL": 4}
    min_level = priority_order.get(min_priority, 4)
    if "priority" not in exceptions.columns:
        return exceptions
    return exceptions[exceptions["priority"].map(priority_order).fillna(4) <= min_level]


def exception_summary(exceptions):
    """Generate a summary statistics dict for exception set."""
    if exceptions.empty:
        return {
            "total": 0,
            "by_priority": {},
            "ai_investigated": 0,
            "ai_auto_resolved": 0,
            "human_review": 0,
        }
    by_priority = exceptions["priority"].value_counts().to_dict()
    ai_inv = (exceptions["ai_investigated"] == True).sum()
    ai_auto = ((exceptions["ai_action"] == "AUTO_RESOLVE") & (exceptions["ai_investigated"] == True)).sum()
    human = ((exceptions["ai_action"] == "HUMAN_REVIEW") | (exceptions["status"] == "REVIEW_REQUIRED")).sum()
    return {
        "total": len(exceptions),
        "by_priority": by_priority,
        "ai_investigated": int(ai_inv),
        "ai_auto_resolved": int(ai_auto),
        "human_review": int(human),
    }