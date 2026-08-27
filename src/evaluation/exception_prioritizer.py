import os
import pandas as pd


EXCEPTION_PATH = "data/generated/exception_report.csv"
OUTPUT_PATH = "data/generated/prioritized_exceptions.csv"

PRIORITY_ORDER = {
    "P0_CRITICAL": 0,
    "P1_HIGH": 1,
    "P2_MEDIUM": 2,
    "P4_NORMAL": 3,
}

OUTPUT_COLUMNS = [
    "priority",
    "risk_score",
    "invoice_id",
    "status",
    "final_status",
    "expected_status",
    "confidence",
    "risk_reason",
    "ai_investigated",
    "ai_decision",
    "ai_confidence",
    "ai_action",
    "ai_reason",
    "ai_time_seconds",
]


def _number(value, default=0.0):
    number = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    return default if pd.isna(number) else float(number)


def _classify_exception(row):
    status = str(row["status"])
    final_status = str(row["final_status"])
    expected_status = str(row["expected_status"])
    confidence = _number(row.get("confidence"))
    ai_investigated = row["ai_investigated"]

    if status == "MATCHED" and expected_status != "MATCHED":
        return (
            "P0_CRITICAL",
            90 + min(max(confidence, 0.0), 100.0) / 10,
            "High-confidence MATCHED prediction conflicts with the expected status.",
        )

    if status != expected_status:
        return (
            "P1_HIGH",
            75 + min(max(confidence, 0.0), 100.0) / 100 * 14,
            f"System status {status} disagrees with expected status {expected_status}.",
        )

    if status == "REVIEW_REQUIRED" or confidence < 70:
        if status == "REVIEW_REQUIRED":
            reason = "Deterministic reconciliation explicitly requires review."
        else:
            reason = f"Deterministic confidence is below 70 ({confidence:.2f})."
        return (
            "P2_MEDIUM",
            50 + max(0.0, min(70.0, 70.0 - confidence)) / 70 * 24,
            reason,
        )

    return (
        "P4_NORMAL",
        0 + min(max(confidence, 0.0), 100.0) / 100 * 24,
        f"Unresolved {final_status} exception remains for operational review.",
    )


def prioritize_exceptions(exceptions):
    """Rank unresolved exceptions without changing reconciliation results."""

    prioritized = exceptions.copy()
    actions = prioritized.get(
        "ai_action",
        pd.Series("NOT_REQUIRED", index=prioritized.index),
    ).fillna("NOT_REQUIRED").astype(str)
    prioritized["ai_investigated"] = actions != "NOT_REQUIRED"

    if prioritized.empty:
        for column in OUTPUT_COLUMNS:
            if column not in prioritized:
                prioritized[column] = pd.Series(dtype=object)
        return prioritized[OUTPUT_COLUMNS]

    classifications = prioritized.apply(_classify_exception, axis=1)
    prioritized[["priority", "risk_score", "risk_reason"]] = pd.DataFrame(
        classifications.tolist(),
        index=prioritized.index,
    )
    prioritized["risk_score"] = prioritized["risk_score"].round(2)
    prioritized["_priority_order"] = prioritized["priority"].map(PRIORITY_ORDER)
    prioritized["_confidence_sort"] = pd.to_numeric(
        prioritized.get("confidence", 0.0),
        errors="coerce",
    ).fillna(0.0)
    prioritized["_confidence_sort"] = prioritized.apply(
        lambda row: row["_confidence_sort"]
        if row["priority"] in {"P0_CRITICAL", "P1_HIGH"}
        else -row["_confidence_sort"],
        axis=1,
    )

    prioritized = prioritized.sort_values(
        by=["_priority_order", "risk_score", "_confidence_sort", "invoice_id"],
        ascending=[True, False, False, True],
        kind="mergesort",
    )
    prioritized = prioritized.drop(
        columns=["_priority_order", "_confidence_sort"],
    )

    for column in OUTPUT_COLUMNS:
        if column not in prioritized:
            prioritized[column] = "" if column not in {
                "ai_investigated",
                "risk_score",
            } else (False if column == "ai_investigated" else 0.0)

    return prioritized[OUTPUT_COLUMNS]


def print_summary(prioritized):
    counts = prioritized["priority"].value_counts()

    print("=" * 60)
    print("AI FINANCE CONTROLLER")
    print("EXCEPTION PRIORITIZATION")
    print("=" * 60)
    print(f"\nTotal exceptions: {len(prioritized)}")
    print(f"\nP0 Critical: {int(counts.get('P0_CRITICAL', 0))}")
    print(f"P1 High: {int(counts.get('P1_HIGH', 0))}")
    print(f"P2 Medium: {int(counts.get('P2_MEDIUM', 0))}")
    print(f"P4 Normal: {int(counts.get('P4_NORMAL', 0))}")
    print(f"\nAI investigated: {int(prioritized['ai_investigated'].sum())}")
    print(f"AI auto-resolved: {int((prioritized['ai_action'] == 'AUTO_RESOLVE').sum())}")
    print(f"AI human-review: {int((prioritized['ai_action'] == 'HUMAN_REVIEW').sum())}")
    investigated = prioritized[prioritized["ai_investigated"]]
    confidence_zero = pd.to_numeric(
        investigated["ai_confidence"],
        errors="coerce",
    ).fillna(0) <= 0
    reasons = investigated["ai_reason"].fillna("").astype(str).str.lower()
    failure_terms = (
        "timeout|timed out|invalid json|could not connect|request failed|"
        "unexpected investigator error|empty response|did not provide usable confidence"
        "|could not provide a usable confidence"
    )
    ai_failures = (confidence_zero & reasons.str.contains(failure_terms, regex=True)).sum()
    print(f"AI failures: {int(ai_failures)}")

    display = prioritized.head(10).rename(columns={
        "invoice_id": "Invoice",
        "priority": "Priority",
        "risk_score": "Risk Score",
        "status": "System Status",
        "expected_status": "Expected Status",
        "confidence": "Confidence",
        "risk_reason": "Risk Reason",
        "ai_decision": "AI Status",
    })
    display_columns = [
        "Invoice",
        "Priority",
        "Risk Score",
        "System Status",
        "Expected Status",
        "Confidence",
        "Risk Reason",
        "AI Status",
    ]
    print("\nTop 10 highest-risk exceptions:")
    print(display[display_columns].to_string(index=False))


def main():
    if not os.path.exists(EXCEPTION_PATH):
        print(f"ERROR: Missing file: {EXCEPTION_PATH}")
        return

    exceptions = pd.read_csv(EXCEPTION_PATH)
    prioritized = prioritize_exceptions(exceptions)
    prioritized.to_csv(OUTPUT_PATH, index=False)
    print_summary(prioritized)
    print(f"\nPrioritized exceptions saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
