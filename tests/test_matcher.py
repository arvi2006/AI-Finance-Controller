import pandas as pd
import pytest

from src.reconciliation.matcher import match_transactions


@pytest.mark.unit
def test_matcher_covers_fixture_statuses(normalized_invoices, normalized_bank_transactions):
    bank_by_invoice = {
        "INV-TEST-001": ["TXN-TEST-001"],
        "INV-TEST-002": ["TXN-TEST-002"],
        "INV-TEST-003": [],
        "INV-TEST-004": ["TXN-TEST-003"],
        "INV-TEST-005": ["TXN-TEST-004", "TXN-TEST-005"],
        "INV-TEST-006": ["TXN-TEST-006", "TXN-TEST-008"],
    }
    result_parts = []
    for _, invoice in normalized_invoices.iterrows():
        selected = normalized_bank_transactions[
            normalized_bank_transactions["transaction_id"].isin(
                bank_by_invoice[invoice["invoice_id"]]
            )
        ]
        result_parts.append(match_transactions(pd.DataFrame([invoice]), selected))
    results = pd.concat(result_parts, ignore_index=True)
    assert len(results) == len(normalized_invoices)
    assert results["invoice_id"].is_unique
    assert set(results["status"]).issubset({"MATCHED", "AMOUNT_MISMATCH", "MISSING_PAYMENT", "DUPLICATE", "TIMING_DIFFERENCE", "SPLIT_PAYMENT", "REVIEW_REQUIRED"})
    assert results["confidence"].between(0, 100).all()
    assert results.loc[results.invoice_id == "INV-TEST-001", "status"].item() == "MATCHED"
    assert results.loc[results.invoice_id == "INV-TEST-002", "status"].item() == "AMOUNT_MISMATCH"
    assert results.loc[results.invoice_id == "INV-TEST-003", "status"].item() == "MISSING_PAYMENT"
    assert results.loc[results.invoice_id == "INV-TEST-004", "status"].item() == "TIMING_DIFFERENCE"
    assert results.loc[results.invoice_id == "INV-TEST-005", "status"].item() == "SPLIT_PAYMENT"
    assert results.loc[results.invoice_id == "INV-TEST-006", "status"].item() == "DUPLICATE"


@pytest.mark.unit
def test_matched_transaction_ids_are_valid(normalized_invoices, normalized_bank_transactions):
    results = match_transactions(normalized_invoices, normalized_bank_transactions)
    valid_ids = set(normalized_bank_transactions["transaction_id"])
    for value in results["matched_transaction_ids"].fillna(""):
        assert set(filter(None, str(value).split(","))).issubset(valid_ids)
