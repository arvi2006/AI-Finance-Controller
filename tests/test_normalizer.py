import pandas as pd
import pytest

from src.normalizer import normalize_bank_transactions, normalize_invoices, normalize_text


@pytest.mark.unit
def test_normalize_text_rules():
    assert normalize_text("Rodriguez Figueroa Pvt Ltd") == "rodriguez figueroa"
    assert normalize_text("PAYMENT RODRIGUEZ FIGUEROA") == "rodriguez figueroa"
    assert normalize_text("  Alpha,   Co.  ") == "alpha"
    assert normalize_text(None) == ""
    assert normalize_text(float("nan")) == ""


@pytest.mark.unit
def test_normalize_frames(invoices, bank_transactions):
    normalized_invoices = normalize_invoices(invoices)
    normalized_bank = normalize_bank_transactions(bank_transactions)
    assert {"customer_normalized", "invoice_date", "amount"}.issubset(normalized_invoices.columns)
    assert {"description_normalized", "transaction_date", "amount"}.issubset(normalized_bank.columns)
    assert pd.api.types.is_datetime64_any_dtype(normalized_invoices["invoice_date"])
    assert pd.api.types.is_datetime64_any_dtype(normalized_bank["transaction_date"])
