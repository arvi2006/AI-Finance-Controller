import pandas as pd
import pytest


@pytest.fixture
def invoices():
    return pd.DataFrame([
        {"invoice_id": "INV-TEST-001", "customer": "Alpha Company Ltd", "amount": 100.0, "invoice_date": "2024-01-10"},
        {"invoice_id": "INV-TEST-002", "customer": "Beta Industries", "amount": 200.0, "invoice_date": "2024-01-10"},
        {"invoice_id": "INV-TEST-003", "customer": "Gamma Services", "amount": 300.0, "invoice_date": "2024-01-10"},
        {"invoice_id": "INV-TEST-004", "customer": "Delta Retail", "amount": 400.0, "invoice_date": "2024-01-10"},
        {"invoice_id": "INV-TEST-005", "customer": "Epsilon Labs", "amount": 500.0, "invoice_date": "2024-01-10"},
        {"invoice_id": "INV-TEST-006", "customer": "Zeta Consulting", "amount": 600.0, "invoice_date": "2024-01-10"},
    ])


@pytest.fixture
def bank_transactions():
    return pd.DataFrame([
        {"transaction_id": "TXN-TEST-001", "description": "PAYMENT ALPHA", "amount": 100.0, "transaction_date": "2024-01-10"},
        {"transaction_id": "TXN-TEST-002", "description": "PAYMENT BETA INDUSTRIES", "amount": 190.0, "transaction_date": "2024-01-10"},
        {"transaction_id": "TXN-TEST-003", "description": "PAYMENT DELTA RETAIL", "amount": 400.0, "transaction_date": "2024-01-20"},
        {"transaction_id": "TXN-TEST-004", "description": "PAYMENT EPSILON LABS", "amount": 250.0, "transaction_date": "2024-01-10"},
        {"transaction_id": "TXN-TEST-005", "description": "PAYMENT EPSILON LABS", "amount": 250.0, "transaction_date": "2024-01-10"},
        {"transaction_id": "TXN-TEST-006", "description": "PAYMENT ZETA CONSULTING", "amount": 600.0, "transaction_date": "2024-01-10"},
        {"transaction_id": "TXN-TEST-008", "description": "PAYMENT ZETA CONSULTING", "amount": 600.0, "transaction_date": "2024-01-10"},
        {"transaction_id": "TXN-TEST-007", "description": "UNRELATED PAYMENT", "amount": 9999.0, "transaction_date": "2024-01-10"},
    ])


@pytest.fixture
def normalized_invoices(invoices):
    from src.normalizer import normalize_invoices
    return normalize_invoices(invoices)


@pytest.fixture
def normalized_bank_transactions(bank_transactions):
    from src.normalizer import normalize_bank_transactions
    return normalize_bank_transactions(bank_transactions)


@pytest.fixture
def reconciliation_results():
    return pd.DataFrame([
        {"invoice_id": "INV-TEST-001", "status": "MATCHED", "confidence": 99.0},
        {"invoice_id": "INV-TEST-002", "status": "AMOUNT_MISMATCH", "confidence": 70.0},
        {"invoice_id": "INV-TEST-003", "status": "MISSING_PAYMENT", "confidence": 10.0},
        {"invoice_id": "INV-TEST-004", "status": "REVIEW_REQUIRED", "confidence": 60.0},
        {"invoice_id": "INV-TEST-005", "status": "SPLIT_PAYMENT", "confidence": 95.0},
        {"invoice_id": "INV-TEST-006", "status": "DUPLICATE", "confidence": 99.0},
    ])


@pytest.fixture
def ai_results():
    rows = [
        {"invoice_id": f"INV-TEST-{index:03d}", "status": "MATCHED", "final_status": "MATCHED", "confidence": 90.0, "ai_decision": "", "ai_confidence": 0.0, "ai_action": "NOT_REQUIRED", "ai_reason": "", "ai_time_seconds": 0.0}
        for index in range(1, 7)
    ]
    rows[2].update({"status": "MISSING_PAYMENT", "final_status": "MISSING_PAYMENT"})
    rows[3].update({"status": "REVIEW_REQUIRED", "final_status": "REVIEW_REQUIRED", "ai_decision": "HUMAN_REVIEW", "ai_confidence": 0.0, "ai_action": "HUMAN_REVIEW", "ai_reason": "Ollama request timed out.", "ai_time_seconds": 10.0})
    return pd.DataFrame(rows)
