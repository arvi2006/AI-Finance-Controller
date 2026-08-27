import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix
)


def evaluate_reconciliation(
    results_path="data/generated/reconciliation_results.csv",
    ground_truth_path="data/generated/ground_truth.csv"
):
    results = pd.read_csv(results_path)
    ground_truth = pd.read_csv(ground_truth_path)

    # Keep only the columns required for evaluation
    predictions = results[
        ["invoice_id", "status"]
    ].copy()

    actual = ground_truth[
        ["invoice_id", "expected_status"]
    ].copy()

    # Merge prediction with ground truth
    evaluation = actual.merge(
        predictions,
        on="invoice_id",
        how="left"
    )

    # Calculate accuracy
    accuracy = accuracy_score(
        evaluation["expected_status"],
        evaluation["status"]
    )

    print("\n" + "=" * 60)
    print("AI FINANCE CONTROLLER - RECONCILIATION EVALUATION")
    print("=" * 60)

    print(f"\nTotal records: {len(evaluation)}")

    print(
        f"Correct classifications: "
        f"{(evaluation['expected_status'] == evaluation['status']).sum()}"
    )

    print(
        f"Incorrect classifications: "
        f"{(evaluation['expected_status'] != evaluation['status']).sum()}"
    )

    print(f"\nOverall Accuracy: {accuracy * 100:.2f}%")

    print("\nClassification Report:")
    print(
        classification_report(
            evaluation["expected_status"],
            evaluation["status"],
            zero_division=0
        )
    )

    labels = sorted(
        evaluation["expected_status"].unique()
    )

    matrix = confusion_matrix(
        evaluation["expected_status"],
        evaluation["status"],
        labels=labels
    )

    print("Confusion Matrix:")
    print(
        pd.DataFrame(
            matrix,
            index=[
                f"Actual_{label}"
                for label in labels
            ],
            columns=[
                f"Predicted_{label}"
                for label in labels
            ]
        )
    )

    # Save detailed evaluation
    evaluation["correct"] = (
        evaluation["expected_status"]
        == evaluation["status"]
    )

    evaluation.to_csv(
        "data/generated/evaluation_results.csv",
        index=False
    )

    print(
        "\nDetailed evaluation saved to:"
        "\ndata/generated/evaluation_results.csv"
    )

    return evaluation


if __name__ == "__main__":
    evaluate_reconciliation()