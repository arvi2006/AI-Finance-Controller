import pytest

from src.data_generator import generate_dataset


@pytest.mark.unit
def test_generated_dataset_contract():
    invoices, bank, truth = generate_dataset(num_records=500, seed=123)
    assert len(invoices) == 500
    assert len(truth) == 500
    assert len(bank) >= len(invoices)
    assert invoices["invoice_id"].is_unique
    assert bank["transaction_id"].is_unique
    assert set(truth["expected_status"]).issubset({"MATCHED", "AMOUNT_MISMATCH", "MISSING_PAYMENT", "DUPLICATE", "TIMING_DIFFERENCE", "SPLIT_PAYMENT"})
    assert set(truth["invoice_id"]).issubset(set(invoices["invoice_id"]))
    assert {"invoice_id", "customer", "amount", "invoice_date"}.issubset(invoices.columns)
    assert {"transaction_id", "description", "amount", "transaction_date"}.issubset(bank.columns)
