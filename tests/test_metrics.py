import pandas as pd
import pytest

from src.evaluation.metrics import calculate_metrics, create_exception_report


@pytest.mark.unit
def test_metrics_scope_ai_failures_and_latency():
    truth = pd.DataFrame({"invoice_id": [f"I{i}" for i in range(1, 7)], "expected_status": ["MATCHED"] * 6})
    baseline = pd.DataFrame({"invoice_id": [f"I{i}" for i in range(1, 7)], "status": ["MATCHED"] * 6, "confidence": [99] * 6})
    ai = baseline.assign(final_status="MATCHED", ai_decision="", ai_confidence=0.0, ai_action="NOT_REQUIRED", ai_reason="", ai_time_seconds=0.0)
    ai.loc[0, ["ai_action", "ai_reason", "ai_time_seconds"]] = ["HUMAN_REVIEW", "Ollama request timed out.", 10.0]
    ai.loc[1, ["ai_action", "ai_confidence", "ai_time_seconds"]] = ["HUMAN_REVIEW", 0.5, 20.0]
    ai.loc[2, ["ai_action", "ai_confidence", "ai_time_seconds"]] = ["HUMAN_REVIEW", 0.5, 30.0]
    ai.loc[3, ["ai_action", "ai_confidence", "ai_time_seconds"]] = ["HUMAN_REVIEW", 0.5, 40.0]
    ai.loc[4, ["ai_action", "ai_confidence", "ai_time_seconds"]] = ["HUMAN_REVIEW", 0.5, 50.0]
    metrics = calculate_metrics(truth, baseline, ai)
    assert metrics["baseline_correct"] == 6
    assert metrics["baseline_exceptions"] == 0
    assert metrics["ai_investigations"] == 5
    assert metrics["ai_not_investigated"] == 1
    assert metrics["ai_failures"] == 1
    assert metrics["total_ai_time_seconds"] == 150.0
    assert metrics["average_ai_time_seconds"] == 30.0


@pytest.mark.unit
def test_exception_report_is_invoice_aligned():
    truth = pd.DataFrame({"invoice_id": ["I1", "I2"], "expected_status": ["MATCHED", "MISSING_PAYMENT"]})
    baseline = pd.DataFrame({"invoice_id": ["I2", "I1"], "status": ["MISSING_PAYMENT", "MATCHED"], "confidence": [50, 90]})
    ai = pd.DataFrame({"invoice_id": ["I2", "I1"], "status": ["MISSING_PAYMENT", "MATCHED"], "final_status": ["MISSING_PAYMENT", "MATCHED"], "confidence": [50, 90], "ai_action": ["NOT_REQUIRED", "NOT_REQUIRED"]})
    report = create_exception_report(truth, baseline, ai)
    assert report.empty
