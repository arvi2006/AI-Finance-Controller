import pandas as pd
import pytest

from src.evaluation.exception_prioritizer import prioritize_exceptions
from src.evaluation.metrics import calculate_metrics, create_exception_report
from src.normalizer import normalize_bank_transactions, normalize_invoices
from src.reconciliation.matcher import match_transactions


@pytest.mark.integration
def test_small_pipeline_integrity(invoices, bank_transactions):
    normalized_invoices = normalize_invoices(invoices)
    normalized_bank = normalize_bank_transactions(bank_transactions)
    baseline = match_transactions(normalized_invoices, normalized_bank)
    truth = pd.DataFrame({"invoice_id": baseline["invoice_id"], "expected_status": baseline["status"]})
    ai = baseline.assign(final_status=baseline["status"], ai_decision="", ai_confidence=0.0, ai_action="NOT_REQUIRED", ai_reason="", ai_time_seconds=0.0)
    metrics = calculate_metrics(truth, baseline, ai)
    report = create_exception_report(truth, baseline, ai)
    prioritized = prioritize_exceptions(report)
    assert len(baseline) == len(invoices) == len(ai)
    assert baseline.invoice_id.is_unique
    assert metrics["total_records"] == len(invoices)
    assert report.empty
    assert prioritized.empty
