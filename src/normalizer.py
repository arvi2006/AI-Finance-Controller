import re
import pandas as pd


COMMON_TERMS = [
    "private limited",
    "pvt ltd",
    "pvt",
    "limited",
    "ltd",
    "llp",
    "incorporated",
    "inc",
    "corporation",
    "corp",
    "company",
    "co",
    "payment",
    "neft",
    "imps",
    "upi",
]


def normalize_text(text):
    """
    Normalize customer/payment descriptions
    for reconciliation.
    """

    if pd.isna(text):
        return ""

    text = str(text).lower()

    # Remove punctuation
    text = re.sub(
        r"[^a-z0-9\s]",
        " ",
        text
    )

    # Remove common financial/business terms
    for term in COMMON_TERMS:
        text = re.sub(
            rf"\b{re.escape(term)}\b",
            " ",
            text
        )

    # Normalize whitespace
    text = " ".join(
        text.split()
    )

    return text.strip()


def normalize_invoices(df):
    """
    Normalize invoice data.
    """

    df = df.copy()

    df["customer_normalized"] = (
        df["customer"]
        .apply(normalize_text)
    )

    df["invoice_date"] = pd.to_datetime(
        df["invoice_date"]
    )

    df["amount"] = pd.to_numeric(
        df["amount"]
    )

    return df


def normalize_bank_transactions(df):
    """
    Normalize bank transaction descriptions.
    """

    df = df.copy()

    df["description_normalized"] = (
        df["description"]
        .apply(normalize_text)
    )

    df["transaction_date"] = pd.to_datetime(
        df["transaction_date"]
    )

    df["amount"] = pd.to_numeric(
        df["amount"]
    )

    return df