import pandas as pd
from difflib import SequenceMatcher


# ============================================================
# CONFIGURATION
# ============================================================

EXACT_AMOUNT_TOLERANCE = 0.01

STRONG_MATCH_THRESHOLD = 85
REVIEW_THRESHOLD = 65

DATE_MATCH_DAYS = 2
TIMING_DIFFERENCE_DAYS = 2


# ============================================================
# TEXT SIMILARITY
# ============================================================

def text_similarity(text1, text2):
    """Calculate similarity between two strings."""

    if not text1 or not text2:
        return 0.0

    return SequenceMatcher(
        None,
        str(text1),
        str(text2)
    ).ratio()


# ============================================================
# CANDIDATE FILTERING
# ============================================================

def find_candidates(invoice, bank_transactions, top_k=10):
    """
    Quickly find potentially relevant bank transactions.

    We use amount and date to reduce the search space before
    performing fuzzy text comparison.
    """

    invoice_amount = float(
        invoice["amount"]
    )

    invoice_date = pd.Timestamp(
        invoice["invoice_date"]
    )

    candidates = bank_transactions.copy()

    # --------------------------------------------------------
    # Amount-based candidate filtering
    # --------------------------------------------------------

    amount_tolerance = max(
        2500,
        invoice_amount * 0.10
    )

    normal_candidates = candidates[
        candidates["amount"].between(
            invoice_amount - amount_tolerance,
            invoice_amount + amount_tolerance
        )
    ].copy()

    # --------------------------------------------------------
    # Split-payment candidates
    #
    # Individual payments may be substantially smaller.
    # --------------------------------------------------------

    split_candidates = candidates[
        candidates["amount"].between(
            invoice_amount * 0.20,
            invoice_amount * 0.70
        )
    ].copy()

    candidates = pd.concat(
        [
            normal_candidates,
            split_candidates
        ]
    ).drop_duplicates(
        subset=["transaction_id"]
    )

    if candidates.empty:
        return pd.DataFrame()

    # --------------------------------------------------------
    # Date filtering
    # --------------------------------------------------------

    candidates["date_difference"] = (
        candidates["transaction_date"]
        - invoice_date
    ).abs().dt.days

    # Allow a fairly broad settlement window.
    candidates = candidates[
        candidates["date_difference"] <= 30
    ].copy()

    if candidates.empty:
        return pd.DataFrame()

    # --------------------------------------------------------
    # Calculate customer similarity
    # --------------------------------------------------------

    invoice_customer = (
        invoice["customer_normalized"]
    )

    candidates["customer_score"] = (
        candidates[
            "description_normalized"
        ].apply(
            lambda x: text_similarity(
                invoice_customer,
                x
            )
        )
    )

    # --------------------------------------------------------
    # Amount similarity
    # --------------------------------------------------------

    candidates["amount_difference"] = (
        candidates["amount"]
        - invoice_amount
    ).abs()

    candidates["amount_score"] = (
        1
        - (
            candidates["amount_difference"]
            / invoice_amount
        )
    ).clip(
        lower=0
    )

    # --------------------------------------------------------
    # Date score
    # --------------------------------------------------------

    def calculate_date_score(days):

        if days == 0:
            return 1.0

        if days <= 2:
            return 0.9

        if days <= 7:
            return 0.7

        if days <= 14:
            return 0.4

        return 0.1

    candidates["date_score"] = (
        candidates[
            "date_difference"
        ].apply(
            calculate_date_score
        )
    )

    # --------------------------------------------------------
    # Weighted confidence
    # --------------------------------------------------------

    candidates["confidence"] = (
        candidates["customer_score"] * 0.45
        +
        candidates["amount_score"] * 0.40
        +
        candidates["date_score"] * 0.15
    ) * 100

    # --------------------------------------------------------
    # Exact amount bonus
    # --------------------------------------------------------

    exact_amount_mask = (
        candidates["amount_difference"]
        <= EXACT_AMOUNT_TOLERANCE
    )

    candidates.loc[
        exact_amount_mask,
        "confidence"
    ] += 10

    candidates["confidence"] = (
        candidates["confidence"]
        .clip(upper=99)
        .round(2)
    )

    return (
        candidates
        .sort_values(
            "confidence",
            ascending=False
        )
        .head(top_k)
    )


# ============================================================
# SPLIT PAYMENT DETECTION
# ============================================================

def detect_split_payment(
    invoice,
    bank_transactions
):
    """
    Find two bank transactions whose combined value
    equals the invoice amount.
    """

    invoice_amount = float(
        invoice["amount"]
    )

    if bank_transactions.empty:
        return None

    # Only examine plausible partial payments.
    candidates = bank_transactions[
        bank_transactions["amount"].between(
            invoice_amount * 0.20,
            invoice_amount * 0.80
        )
    ].copy()

    if len(candidates) < 2:
        return None

    # Limit the search for performance.
    candidates = candidates.head(30)

    for i in range(len(candidates)):

        first = candidates.iloc[i]

        for j in range(
            i + 1,
            len(candidates)
        ):

            second = candidates.iloc[j]

            combined_amount = (
                float(first["amount"])
                +
                float(second["amount"])
            )

            if abs(
                combined_amount
                - invoice_amount
            ) <= EXACT_AMOUNT_TOLERANCE:

                return {
                    "transaction_ids":
                        (
                            f"{first['transaction_id']},"
                            f"{second['transaction_id']}"
                        ),

                    "combined_amount":
                        combined_amount
                }

    return None


# ============================================================
# DUPLICATE DETECTION
# ============================================================

def detect_duplicate(
    invoice,
    candidates
):
    """
    Detect multiple transactions that appear to represent
    the same invoice payment.
    """

    if candidates.empty:
        return None

    invoice_amount = float(
        invoice["amount"]
    )

    exact = candidates[
        candidates["amount_difference"]
        <= EXACT_AMOUNT_TOLERANCE
    ]

    if len(exact) >= 2:

        return exact

    return None


# ============================================================
# MAIN RECONCILIATION ENGINE
# ============================================================

def match_transactions(
    invoices,
    bank_transactions
):
    """
    Reconcile invoices against bank transactions.

    Returns a DataFrame containing:
        invoice
        candidate transaction
        confidence
        reconciliation status
    """

    results = []

    invoices = invoices.copy()
    bank_transactions = bank_transactions.copy()

    # --------------------------------------------------------
    # Ensure correct data types
    # --------------------------------------------------------

    invoices["invoice_date"] = pd.to_datetime(
        invoices["invoice_date"]
    )

    bank_transactions[
        "transaction_date"
    ] = pd.to_datetime(
        bank_transactions[
            "transaction_date"
        ]
    )

    invoices["amount"] = pd.to_numeric(
        invoices["amount"]
    )

    bank_transactions["amount"] = pd.to_numeric(
        bank_transactions["amount"]
    )

    # ========================================================
    # PROCESS EACH INVOICE
    # ========================================================

    for _, invoice in invoices.iterrows():

        invoice_id = invoice[
            "invoice_id"
        ]

        invoice_amount = float(
            invoice["amount"]
        )

        # ----------------------------------------------------
        # Find candidates
        # ----------------------------------------------------

        candidates = find_candidates(
            invoice,
            bank_transactions,
            top_k=10
        )

        # ----------------------------------------------------
        # No candidates
        # ----------------------------------------------------

        if candidates.empty:

            results.append(
                {
                    "invoice_id":
                        invoice_id,

                    "invoice_amount":
                        invoice_amount,

                    "matched_transaction_ids":
                        "",

                    "matched_amount":
                        0,

                    "difference":
                        invoice_amount,

                    "status":
                        "MISSING_PAYMENT",

                    "confidence":
                        100
                }
            )

            continue

        # ----------------------------------------------------
        # Detect duplicate
        # ----------------------------------------------------

        duplicate = detect_duplicate(
            invoice,
            candidates
        )

        if duplicate is not None:

            transaction_ids = ",".join(
                duplicate[
                    "transaction_id"
                ].astype(str)
            )

            total_amount = duplicate[
                "amount"
            ].sum()

            results.append(
                {
                    "invoice_id":
                        invoice_id,

                    "invoice_amount":
                        invoice_amount,

                    "matched_transaction_ids":
                        transaction_ids,

                    "matched_amount":
                        total_amount,

                    "difference":
                        total_amount
                        - invoice_amount,

                    "status":
                        "DUPLICATE",

                    "confidence":
                        99
                }
            )

            continue

        # ----------------------------------------------------
        # Split payment
        # ----------------------------------------------------

        split = detect_split_payment(
            invoice,
            candidates
        )

        if split is not None:

            results.append(
                {
                    "invoice_id":
                        invoice_id,

                    "invoice_amount":
                        invoice_amount,

                    "matched_transaction_ids":
                        split[
                            "transaction_ids"
                        ],

                    "matched_amount":
                        split[
                            "combined_amount"
                        ],

                    "difference":
                        0,

                    "status":
                        "SPLIT_PAYMENT",

                    "confidence":
                        95
                }
            )

            continue

        # ----------------------------------------------------
        # Best candidate
        # ----------------------------------------------------

        best = candidates.iloc[0]

        transaction_amount = float(
            best["amount"]
        )

        difference = (
            transaction_amount
            - invoice_amount
        )

        confidence = float(
            best["confidence"]
        )

        date_difference = int(
            best["date_difference"]
        )

        amount_is_exact = (
            abs(difference)
            <= EXACT_AMOUNT_TOLERANCE
        )

        # ====================================================
        # EXACT AMOUNT
        # ====================================================

        if amount_is_exact:

            if date_difference > TIMING_DIFFERENCE_DAYS:

                status = (
                    "TIMING_DIFFERENCE"
                )

                confidence = min(
                    confidence,
                    95
                )

            else:

                status = "MATCHED"

                confidence = max(
                    confidence,
                    90
                )

                confidence = min(
                    confidence,
                    99
                )

            results.append(
                {
                    "invoice_id":
                        invoice_id,

                    "invoice_amount":
                        invoice_amount,

                    "matched_transaction_ids":
                        best[
                            "transaction_id"
                        ],

                    "matched_amount":
                        transaction_amount,

                    "difference":
                        0,

                    "status":
                        status,

                    "confidence":
                        round(
                            confidence,
                            2
                        )
                }
            )

            continue

        # ====================================================
        # LOW CONFIDENCE
        # ====================================================

        if confidence < REVIEW_THRESHOLD:

            results.append(
                {
                    "invoice_id":
                        invoice_id,

                    "invoice_amount":
                        invoice_amount,

                    "matched_transaction_ids":
                        best[
                            "transaction_id"
                        ],

                    "matched_amount":
                        transaction_amount,

                    "difference":
                        difference,

                    "status":
                        "REVIEW_REQUIRED",

                    "confidence":
                        round(
                            confidence,
                            2
                        )
                }
            )

            continue

        # ====================================================
        # AMOUNT MISMATCH
        # ====================================================

        results.append(
            {
                "invoice_id":
                    invoice_id,

                "invoice_amount":
                    invoice_amount,

                "matched_transaction_ids":
                    best[
                        "transaction_id"
                    ],

                "matched_amount":
                    transaction_amount,

                "difference":
                    difference,

                "status":
                    "AMOUNT_MISMATCH",

                "confidence":
                    round(
                        confidence,
                        2
                    )
            }
        )

    return pd.DataFrame(
        results
    )


# ============================================================
# TEST / CLI
# ============================================================

if __name__ == "__main__":

    from src.normalizer import (
        normalize_invoices,
        normalize_bank_transactions
    )

    print("Loading financial data...")

    invoices = pd.read_csv(
        "data/generated/invoices.csv"
    )

    bank = pd.read_csv(
        "data/generated/bank_transactions.csv"
    )

    print(
        f"Invoices: {len(invoices)}"
    )

    print(
        f"Bank transactions: {len(bank)}"
    )

    print(
        "\nNormalizing data..."
    )

    invoices = normalize_invoices(
        invoices
    )

    bank = normalize_bank_transactions(
        bank
    )

    print(
        "Starting reconciliation..."
    )

    results = match_transactions(
        invoices,
        bank
    )

    print(
        "\nReconciliation Results:"
    )

    print(
        results.head(10).to_string(
            index=False
        )
    )

    print(
        "\nStatus Distribution:"
    )

    print(
        results[
            "status"
        ].value_counts()
    )

    results.to_csv(
        "data/generated/reconciliation_results.csv",
        index=False
    )

    print(
        "\nResults saved to:"
    )

    print(
        "data/generated/"
        "reconciliation_results.csv"
    )