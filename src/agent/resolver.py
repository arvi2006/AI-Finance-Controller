import math
import time
import pandas as pd

from src.agent.investigator import investigate
from src.normalizer import (
    normalize_invoices,
    normalize_bank_transactions
)
from src.reconciliation.matcher import (
    find_candidates
)


AI_CONFIDENCE_THRESHOLD = 0.80
MAX_AI_CASES = 5


def should_use_ai(result, candidates):
    """
    Decide whether a reconciliation case is genuinely ambiguous.

    The deterministic matcher should handle obvious cases.
    Ollama should only investigate uncertain cases.
    """

    status = str(
        result["status"]
    )

    # --------------------------------------------------------
    # These statuses are already handled well by the
    # deterministic reconciliation engine.
    # --------------------------------------------------------

    if status in {
        "MATCHED",
        "DUPLICATE",
        "TIMING_DIFFERENCE",
        "SPLIT_PAYMENT",
    }:
        return False

    try:
        confidence = float(result.get("confidence", 0.0))
    except (TypeError, ValueError, OverflowError):
        confidence = 0.0

    if status == "AMOUNT_MISMATCH" and confidence >= 82:
        return False

    if status == "REVIEW_REQUIRED":
        return True

    if status in {
        "AMOUNT_MISMATCH",
        "MISSING_PAYMENT",
    }:
        return True

    if candidates is None or candidates.empty or len(candidates) < 2:
        return False

    top_confidence = float(candidates.iloc[0].get("confidence", 0.0))
    next_confidence = float(candidates.iloc[1].get("confidence", 0.0))
    return abs(top_confidence - next_confidence) < 0.10


def _candidate_priority(result, candidates):
    status_priority = {
        "REVIEW_REQUIRED": 100,
        "AMOUNT_MISMATCH": 90,
        "MISSING_PAYMENT": 80,
    }
    priority = status_priority.get(str(result["status"]), 50)

    if candidates.empty:
        return priority + 20

    confidence = float(candidates.iloc[0].get("confidence", 0.0))
    return priority + (1.0 - confidence) * 20 + min(len(candidates), 5)


def _investigation_failed(decision, confidence):
    if confidence > 0:
        return False

    reason = str(decision.get("reason", "")).lower()
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
    return any(term in reason for term in failure_terms)


def resolve_exceptions(
    invoices,
    bank_transactions,
    reconciliation_results
):
    """
    Run deterministic reconciliation first.

    Send only genuinely ambiguous cases to Ollama.
    """

    start_time = time.time()

    results = reconciliation_results.copy()

    ai_results = []

    # --------------------------------------------------------
    # Statistics
    # --------------------------------------------------------

    total_records = len(results)

    ai_candidates = 0

    ai_failed = 0
    ai_investigations = 0

    # Select unique deterministic exceptions before doing any candidate
    # search or AI work. Lower-confidence exceptions are harder cases.
    exceptions = results.loc[
        results.apply(
            lambda result: str(result["status"]) in {
                "REVIEW_REQUIRED",
                "AMOUNT_MISMATCH",
                "MISSING_PAYMENT",
            }
            and not (
                str(result["status"]) == "AMOUNT_MISMATCH"
                and float(result.get("confidence", 0.0)) >= 82
            ),
            axis=1,
        )
    ].copy()
    exceptions["_status_priority"] = exceptions["status"].map({
        "REVIEW_REQUIRED": 0,
        "AMOUNT_MISMATCH": 1,
        "MISSING_PAYMENT": 2,
    }).fillna(3)
    exceptions = exceptions.sort_values(
        ["_status_priority", "confidence"],
        ascending=[True, True],
    ).drop_duplicates(
        subset=["invoice_id"],
        keep="first",
    ).head(MAX_AI_CASES).drop(
        columns=["_status_priority"]
    )

    # --------------------------------------------------------
    # Process the selected unique exceptions
    # --------------------------------------------------------

    ai_candidates = len(exceptions)
    processed_invoice_ids = set()

    for _, result in exceptions.iterrows():

        invoice_id = result["invoice_id"]

        if invoice_id in processed_invoice_ids:
            continue
        processed_invoice_ids.add(invoice_id)

        invoice_rows = invoices[
            invoices["invoice_id"]
            == invoice_id
        ]

        if invoice_rows.empty:
            continue

        invoice = invoice_rows.iloc[0]

        candidates = find_candidates(
            invoice,
            bank_transactions,
            top_k=5
        )

        investigation_number = len(processed_invoice_ids)
        ai_investigations += 1

        print(
            f"\n[{investigation_number}/{MAX_AI_CASES}] "
            f"Investigating {invoice_id}..."
        )

        # ----------------------------------------------------
        # Call Ollama
        # ----------------------------------------------------

        ai_start = time.time()

        decision = investigate(
            invoice,
            candidates
        )

        ai_time = (
            time.time()
            - ai_start
        )

        ai_decision = decision.get(
            "decision",
            "HUMAN_REVIEW"
        )

        try:
            ai_confidence = float(decision.get("confidence", 0.0))
        except (TypeError, ValueError, OverflowError):
            ai_confidence = 0.0
        if not math.isfinite(ai_confidence):
            ai_confidence = 0.0
        ai_confidence = max(0.0, min(1.0, ai_confidence))

        ai_reason = decision.get(
            "reason",
            ""
        )

        print(
            f"Decision   : "
            f"{ai_decision}"
        )

        print(
            f"Confidence : "
            f"{ai_confidence:.2f}"
        )

        print(
            f"Time       : "
            f"{ai_time:.2f}s"
        )

        # ----------------------------------------------------
        # Determine AI action
        # ----------------------------------------------------

        if (
            ai_confidence
            >= AI_CONFIDENCE_THRESHOLD
        ):

            ai_action = "AUTO_RESOLVE"

        else:

            ai_action = "HUMAN_REVIEW"

        # ----------------------------------------------------
        # Track failures
        # ----------------------------------------------------

        if _investigation_failed(decision, ai_confidence):

            ai_failed += 1

        ai_results.append({
            "invoice_id":
                invoice_id,

            "ai_decision":
                ai_decision,

            "ai_confidence":
                ai_confidence,

            "ai_reason":
                ai_reason,

            "ai_action":
                ai_action,

            "ai_time_seconds":
                round(
                    ai_time,
                    2
                )
        })

    results["final_status"] = results["status"]
    results["ai_decision"] = ""
    results["ai_confidence"] = 0.0
    results["ai_reason"] = ""
    results["ai_action"] = "NOT_REQUIRED"
    results["ai_time_seconds"] = 0.0

    if not ai_results:
        elapsed = (
            time.time()
            - start_time
        )

        print(
            "\nNo cases required AI investigation."
        )

        print(
            f"Total records: {total_records}"
        )

        print(f"AI candidates       : {ai_candidates}")
        print(f"AI investigations   : {ai_investigations}")
        print(f"Total runtime       : {elapsed:.2f}s")

        return results

    # --------------------------------------------------------
    # Merge AI results
    # --------------------------------------------------------

    ai_df = pd.DataFrame(ai_results)
    ai_columns = [
        "final_status",
        "ai_decision",
        "ai_confidence",
        "ai_reason",
        "ai_action",
        "ai_time_seconds",
    ]
    results = results.drop(
        columns=[column for column in ai_columns if column in results],
        errors="ignore",
    )

    results = results.merge(
        ai_df,
        on="invoice_id",
        how="left"
    )

    for column, default in {
        "ai_decision": "",
        "ai_confidence": 0.0,
        "ai_reason": "",
        "ai_action": "NOT_REQUIRED",
        "ai_time_seconds": 0.0,
    }.items():
        results[column] = results[column].fillna(default)

    results["final_status"] = results["status"]

    # --------------------------------------------------------
    # Final decision
    # --------------------------------------------------------

    ai_mask = (
        results["ai_action"]
        == "AUTO_RESOLVE"
    )

    results.loc[
        ai_mask,
        "final_status"
    ] = results.loc[
        ai_mask,
        "ai_decision"
    ]

    # --------------------------------------------------------
    # Statistics
    # --------------------------------------------------------

    elapsed = (
        time.time()
        - start_time
    )

    auto_resolved = int(
        (
            results["ai_action"]
            == "AUTO_RESOLVE"
        ).sum()
    )

    human_review = int(
        (
            results["ai_action"]
            == "HUMAN_REVIEW"
        ).sum()
    )

    print("\n" + "=" * 60)
    print(
        "AI FINANCE CONTROLLER"
    )
    print(
        "AI Investigation Summary"
    )
    print("=" * 60)

    print(
        f"\nTotal records       : "
        f"{total_records}"
    )

    print(
        f"AI candidates       : "
        f"{ai_candidates}"
    )

    print(
        f"AI failed           : "
        f"{ai_failed}"
    )

    print(
        f"AI auto-resolved    : "
        f"{auto_resolved}"
    )

    print(
        f"Human review        : "
        f"{human_review}"
    )

    print(
        f"Total runtime       : "
        f"{elapsed:.2f}s"
    )

    investigated_times = results.loc[
        results["ai_time_seconds"] > 0,
        "ai_time_seconds",
    ]
    average_ai_time = investigated_times.mean() if not investigated_times.empty else 0.0
    print(f"Average AI time     : {average_ai_time:.2f}s")

    print(
        "\nFinal Status Distribution:"
    )

    print(
        results[
            "final_status"
        ].value_counts()
    )

    return results


if __name__ == "__main__":

    print(
        "AI Finance Controller - "
        "Ollama Resolver"
    )

    # --------------------------------------------------------
    # Load financial data
    # --------------------------------------------------------

    invoices = pd.read_csv(
        "data/generated/invoices.csv"
    )

    bank_transactions = pd.read_csv(
        "data/generated/bank_transactions.csv"
    )

    reconciliation = pd.read_csv(
        "data/generated/"
        "reconciliation_results.csv"
    )

    print(
        f"\nInvoices: "
        f"{len(invoices)}"
    )

    print(
        f"Bank transactions: "
        f"{len(bank_transactions)}"
    )

    # --------------------------------------------------------
    # Normalize
    # --------------------------------------------------------

    invoices = normalize_invoices(
        invoices
    )

    bank_transactions = (
        normalize_bank_transactions(
            bank_transactions
        )
    )

    # --------------------------------------------------------
    # Run AI-assisted resolution
    # --------------------------------------------------------

    results = resolve_exceptions(
        invoices,
        bank_transactions,
        reconciliation
    )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    output_path = (
        "data/generated/"
        "ai_reconciliation_results.csv"
    )

    results.to_csv(
        output_path,
        index=False
    )

    print(
        f"\nAI reconciliation saved to:"
    )

    print(
        output_path
    )