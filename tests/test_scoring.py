import pandas as pd
import pytest
from sklearn.metrics import precision_score, recall_score, f1_score

from src.reconciliation.scoring import evaluate_reconciliation


@pytest.mark.unit
def test_scoring_joins_by_invoice_id(tmp_path):
    truth = pd.DataFrame({"invoice_id": ["I1", "I2", "I3", "I4"], "expected_status": ["MATCHED", "MATCHED", "MISSING_PAYMENT", "AMOUNT_MISMATCH"]})
    predictions = pd.DataFrame({"invoice_id": ["I4", "I2", "I1", "I3"], "status": ["AMOUNT_MISMATCH", "MATCHED", "MATCHED", "MATCHED"]})
    truth_path = tmp_path / "truth.csv"
    results_path = tmp_path / "results.csv"
    truth.to_csv(truth_path, index=False)
    predictions.to_csv(results_path, index=False)
    evaluation = evaluate_reconciliation(str(results_path), str(truth_path))
    assert len(evaluation) == 4
    assert int(evaluation["correct"].sum()) == 3
    assert evaluation["correct"].mean() == pytest.approx(0.75)
    truth_labels = [1, 1, 0, 0]
    prediction_labels = [1, 1, 1, 0]
    assert precision_score(truth_labels, prediction_labels) == pytest.approx(2 / 3)
    assert recall_score(truth_labels, prediction_labels) == pytest.approx(1.0)
    assert f1_score(truth_labels, prediction_labels) == pytest.approx(0.8)
