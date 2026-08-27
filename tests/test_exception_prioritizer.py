import pandas as pd
import pytest

from src.evaluation.exception_prioritizer import OUTPUT_COLUMNS, prioritize_exceptions


@pytest.mark.unit
def test_priorities_and_independent_ai_flag():
    data = pd.DataFrame([
        {"invoice_id": "INV-00394", "status": "MATCHED", "final_status": "MATCHED", "expected_status": "MISSING_PAYMENT", "confidence": 90, "ai_action": "NOT_REQUIRED", "ai_confidence": 0, "ai_reason": ""},
        {"invoice_id": "I1", "status": "AMOUNT_MISMATCH", "final_status": "AMOUNT_MISMATCH", "expected_status": "MISSING_PAYMENT", "confidence": 80, "ai_action": "HUMAN_REVIEW", "ai_confidence": 0.5, "ai_reason": "ambiguous"},
        {"invoice_id": "I2", "status": "REVIEW_REQUIRED", "final_status": "REVIEW_REQUIRED", "expected_status": "REVIEW_REQUIRED", "confidence": 90, "ai_action": "NOT_REQUIRED", "ai_confidence": 0, "ai_reason": ""},
        {"invoice_id": "I3", "status": "MATCHED", "final_status": "MATCHED", "expected_status": "MATCHED", "confidence": 99, "ai_action": "NOT_REQUIRED", "ai_confidence": 0, "ai_reason": ""},
    ])
    result = prioritize_exceptions(data)
    assert list(result.columns) == OUTPUT_COLUMNS
    assert result.loc[result.invoice_id == "INV-00394", "priority"].item() == "P0_CRITICAL"
    assert result.loc[result.invoice_id == "I1", "priority"].item() == "P1_HIGH"
    assert bool(result.loc[result.invoice_id == "I1", "ai_investigated"].item())
    assert not bool(result.loc[result.invoice_id == "INV-00394", "ai_investigated"].item())
    assert "P3_AI_INVESTIGATED" not in set(result.priority)


@pytest.mark.unit
def test_not_required_is_not_ai_investigated():
    row = pd.DataFrame([{"invoice_id": "I1", "status": "AMOUNT_MISMATCH", "final_status": "AMOUNT_MISMATCH", "expected_status": "MISSING_PAYMENT", "confidence": 60, "ai_action": "NOT_REQUIRED", "ai_confidence": 0}])
    result = prioritize_exceptions(row)
    assert result.ai_investigated.item() is False
