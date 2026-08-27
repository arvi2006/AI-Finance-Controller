import pandas as pd

from src.normalizer import (
    normalize_invoices,
    normalize_bank_transactions
)

from src.reconciliation.matcher import (
    find_candidates
)

from src.agent.investigator import (
    investigate
)


def main():

    print("=" * 60)
    print("AI FINANCE CONTROLLER")
    print("Ollama Investigator Test")
    print("=" * 60)

    # --------------------------------------------------------
    # Load data
    # --------------------------------------------------------

    print("\nLoading data...")

    invoices = pd.read_csv(
        "data/generated/invoices.csv"
    )

    bank_transactions = pd.read_csv(
        "data/generated/bank_transactions.csv"
    )

    # --------------------------------------------------------
    # Normalize
    # --------------------------------------------------------

    print("Normalizing data...")

    invoices = normalize_invoices(
        invoices
    )

    bank_transactions = normalize_bank_transactions(
        bank_transactions
    )

    # --------------------------------------------------------
    # Select ONE invoice
    #
    # INV-00003 is useful because it is an
    # AMOUNT_MISMATCH case in our dataset.
    # --------------------------------------------------------

    invoice = invoices[
        invoices["invoice_id"] == "INV-00003"
    ]

    if invoice.empty:

        print(
            "\nINV-00003 was not found."
        )

        return

    invoice = invoice.iloc[0]

    # --------------------------------------------------------
    # Find candidates
    # --------------------------------------------------------

    print(
        f"\nFinding candidates for "
        f"{invoice['invoice_id']}..."
    )

    candidates = find_candidates(
        invoice,
        bank_transactions,
        top_k=5
    )

    # --------------------------------------------------------
    # Display invoice
    # --------------------------------------------------------

    print("\n" + "-" * 60)
    print("INVOICE")
    print("-" * 60)

    print(
        f"Invoice ID : {invoice['invoice_id']}"
    )

    print(
        f"Customer   : {invoice['customer']}"
    )

    print(
        f"Amount     : {invoice['amount']}"
    )

    print(
        f"Date       : {invoice['invoice_date']}"
    )

    # --------------------------------------------------------
    # Display candidates
    # --------------------------------------------------------

    print("\n" + "-" * 60)
    print("TOP BANK CANDIDATES")
    print("-" * 60)

    if candidates.empty:

        print(
            "No candidates found."
        )

    else:

        columns = [
            "transaction_id",
            "description",
            "amount",
            "transaction_date",
            "customer_score",
            "amount_score",
            "date_difference",
            "confidence"
        ]

        print(
            candidates[
                columns
            ].to_string(
                index=False
            )
        )

    # --------------------------------------------------------
    # Send to Ollama
    # --------------------------------------------------------

    print("\n" + "-" * 60)
    print("OLLAMA INVESTIGATION")
    print("-" * 60)

    result = investigate(
        invoice,
        candidates
    )

    # --------------------------------------------------------
    # Display result
    # --------------------------------------------------------

    print("\n" + "-" * 60)
    print("AI DECISION")
    print("-" * 60)

    print(
        f"Decision   : "
        f"{result['decision']}"
    )

    print(
        f"Confidence : "
        f"{result['confidence']}"
    )

    print(
        f"Reason     : "
        f"{result['reason']}"
    )

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":

    main()