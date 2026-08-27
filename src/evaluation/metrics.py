import os
import pandas as pd


GROUND_TRUTH_PATH = (
    "data/generated/ground_truth.csv"
)

BASELINE_PATH = (
    "data/generated/reconciliation_results.csv"
)

AI_RESULT_PATH = (
    "data/generated/ai_reconciliation_results.csv"
)

EVALUATION_PATH = (
    "data/generated/final_evaluation.csv"
)

EXCEPTION_PATH = (
    "data/generated/exception_report.csv"
)


def _failed_investigation(actions, confidence, reasons):
    investigated = actions != "NOT_REQUIRED"
    confidence_zero = confidence <= 0
    failure_text = reasons.fillna("").astype(str).str.lower()
    failure_terms = (
        "timeout",
        "timed out",
        "invalid json",
        "could not connect",
        "request failed",
        "unexpected investigator error",
        "empty response",
        "did not provide usable confidence",
        "could not provide a usable confidence",
    )
    return investigated & confidence_zero & failure_text.str.contains(
        "|".join(failure_terms),
        regex=True,
    )


def load_data():
    """Load ground truth, baseline and AI results."""

    ground_truth = pd.read_csv(
        GROUND_TRUTH_PATH
    )

    baseline = pd.read_csv(
        BASELINE_PATH
    )

    ai_results = pd.read_csv(
        AI_RESULT_PATH
    )

    return (
        ground_truth,
        baseline,
        ai_results
    )


def calculate_metrics(
    ground_truth,
    baseline,
    ai_results
):
    """Calculate buildathon evaluation metrics."""

    baseline_eval = ground_truth[
        ["invoice_id", "expected_status"]
    ].merge(
        baseline[
            ["invoice_id", "status", "confidence"]
        ],
        on="invoice_id",
        how="inner",
        validate="one_to_one",
    )
    baseline_correct = (
        baseline_eval["status"].astype(str)
        == baseline_eval["expected_status"].astype(str)
    )

    ai_eval = ground_truth[
        ["invoice_id", "expected_status"]
    ].merge(
        ai_results.drop(
            columns=["expected_status"],
            errors="ignore",
        ),
        on="invoice_id",
        how="inner",
        validate="one_to_one",
    )
    ai_correct = (
        ai_eval["final_status"].astype(str)
        == ai_eval["expected_status"].astype(str)
    )

    baseline_accuracy = float(baseline_correct.mean())
    ai_accuracy = float(ai_correct.mean())
    accuracy_delta = ai_accuracy - baseline_accuracy

    actions = ai_eval.get(
        "ai_action",
        pd.Series("NOT_REQUIRED", index=ai_eval.index),
    ).fillna("NOT_REQUIRED")
    investigated = actions != "NOT_REQUIRED"
    ai_investigations = int(investigated.sum())

    auto_resolved = int((actions == "AUTO_RESOLVE").sum())
    human_review = int((actions == "HUMAN_REVIEW").sum())
    ai_not_investigated = len(ai_eval) - ai_investigations

    ai_confidence = pd.to_numeric(
        ai_eval.get("ai_confidence", 0.0),
        errors="coerce",
    ).fillna(0.0)
    ai_reasons = ai_eval.get(
        "ai_reason",
        pd.Series("", index=ai_eval.index),
    )
    ai_failures = int(
        _failed_investigation(actions, ai_confidence, ai_reasons).sum()
    )

    ai_times = pd.to_numeric(
        ai_eval.get("ai_time_seconds", 0.0),
        errors="coerce",
    ).fillna(0.0)
    investigated_times = ai_times[investigated]
    total_ai_time = float(investigated_times.sum())
    average_ai_time = (
        total_ai_time / ai_investigations
        if ai_investigations
        else 0.0
    )

    metrics = {
        "total_records":
            len(baseline_eval),

        "baseline_correct":
            int(
                baseline_correct.sum()
            ),

        "baseline_accuracy":
            round(
                baseline_accuracy * 100,
                2
            ),

        "ai_correct":
            int(
                ai_correct.sum()
            ),

        "ai_accuracy":
            round(
                ai_accuracy * 100,
                2
            ),

        "accuracy_delta":
            round(
                accuracy_delta * 100,
                2
            ),

        "baseline_exceptions":
            int((~baseline_correct).sum()),

        "ai_not_investigated":
            ai_not_investigated,

        "final_exceptions":
            int((~ai_correct).sum()),

        "ai_investigations":
            ai_investigations,

        "ai_auto_resolved":
            auto_resolved,

        "human_review":
            human_review,

        "ai_failures":
            ai_failures,

        "average_ai_time_seconds":
            round(
                average_ai_time,
                2
            ),

        "total_ai_time_seconds":
            round(
                total_ai_time,
                2
            ),
    }

    return metrics


def create_exception_report(
    ground_truth,
    baseline,
    ai_results
):
    """
    Create an honest exception list.

    Only records where the final result does not match
    ground truth are included.
    """

    report = ground_truth[
        ["invoice_id", "expected_status"]
    ].merge(
        ai_results.drop(
            columns=["expected_status"],
            errors="ignore",
        ),
        on="invoice_id",
        how="inner",
        validate="one_to_one",
    )

    report["is_correct"] = (
        report["final_status"].astype(str)
        == report["expected_status"].astype(str)
    )

    exceptions = report[
        ~report["is_correct"]
    ].copy()

    # --------------------------------------------------------
    # Useful columns
    # --------------------------------------------------------

    preferred_columns = [
        "invoice_id",
        "status",
        "final_status",
        "expected_status",
        "confidence",
        "ai_decision",
        "ai_confidence",
        "ai_action",
        "ai_reason",
        "ai_time_seconds",
    ]

    columns = [
        c for c in preferred_columns
        if c in exceptions.columns
    ]

    exceptions = exceptions[
        columns
    ]

    return exceptions


def print_report(
    metrics,
    exceptions
):
    """Print buildathon-friendly evaluation."""

    print("\n")
    print("=" * 70)
    print("AI FINANCE CONTROLLER")
    print("FINAL BUILDATHON EVALUATION")
    print("=" * 70)

    print(
        f"\nRecords processed       : "
        f"{metrics['total_records']}"
    )

    print(
        f"Baseline accuracy       : "
        f"{metrics['baseline_accuracy']:.2f}%"
    )

    print(
        f"Baseline correct        : "
        f"{metrics['baseline_correct']}"
    )

    print(
        f"Baseline exceptions     : "
        f"{metrics['baseline_exceptions']}"
    )

    print(
        f"\nAI-assisted accuracy    : "
        f"{metrics['ai_accuracy']:.2f}%"
    )

    print(
        f"AI-assisted correct     : "
        f"{metrics['ai_correct']}"
    )

    print(
        f"Accuracy change         : "
        f"{metrics['accuracy_delta']:+.2f}%"
    )

    print(
        f"\nAI investigations       : "
        f"{metrics['ai_investigations']}"
    )

    print(
        f"AI not investigated     : "
        f"{metrics['ai_not_investigated']}"
    )

    print(
        f"AI auto-resolved       : "
        f"{metrics['ai_auto_resolved']}"
    )

    print(
        f"Human review            : "
        f"{metrics['human_review']}"
    )

    print(
        f"AI failures/timeouts    : "
        f"{metrics['ai_failures']}"
    )

    print(
        f"Average AI latency     : "
        f"{metrics['average_ai_time_seconds']:.2f}s"
    )

    print(
        f"Total AI time          : "
        f"{metrics['total_ai_time_seconds']:.2f}s"
    )

    print(
        f"\nFinal unresolved errors: "
        f"{metrics['final_exceptions']}"
    )

    print("\n" + "-" * 70)
    print("EXCEPTION REPORT")
    print("-" * 70)

    if exceptions.empty:

        print(
            "\nNo unresolved exceptions."
        )

    else:

        print(
            exceptions.to_string(
                index=False
            )
        )

    print("\n" + "=" * 70)


def main():

    print(
        "Loading evaluation data..."
    )

    # --------------------------------------------------------
    # Check files
    # --------------------------------------------------------

    required_files = [
        GROUND_TRUTH_PATH,
        BASELINE_PATH,
        AI_RESULT_PATH,
    ]

    for path in required_files:

        if not os.path.exists(path):

            print(
                f"\nERROR: Missing file:"
            )

            print(path)

            return

    # --------------------------------------------------------
    # Load
    # --------------------------------------------------------

    (
        ground_truth,
        baseline,
        ai_results
    ) = load_data()

    print(
        f"Ground truth records : "
        f"{len(ground_truth)}"
    )

    print(
        f"Baseline records     : "
        f"{len(baseline)}"
    )

    print(
        f"AI result records    : "
        f"{len(ai_results)}"
    )

    # --------------------------------------------------------
    # Calculate metrics
    # --------------------------------------------------------

    metrics = calculate_metrics(
        ground_truth,
        baseline,
        ai_results
    )

    # --------------------------------------------------------
    # Exception report
    # --------------------------------------------------------

    exceptions = create_exception_report(
        ground_truth,
        baseline,
        ai_results
    )

    # --------------------------------------------------------
    # Save evaluation
    # --------------------------------------------------------

    metrics_df = pd.DataFrame(
        [
            metrics
        ]
    )

    metrics_df.to_csv(
        EVALUATION_PATH,
        index=False
    )

    exceptions.to_csv(
        EXCEPTION_PATH,
        index=False
    )

    # --------------------------------------------------------
    # Print
    # --------------------------------------------------------

    print_report(
        metrics,
        exceptions
    )

    print(
        "\nFiles created:"
    )

    print(
        f"  {EVALUATION_PATH}"
    )

    print(
        f"  {EXCEPTION_PATH}"
    )


if __name__ == "__main__":

    main()