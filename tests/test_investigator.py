import json

import pytest
import requests

from src.agent import investigator


def candidate_frame():
    import pandas as pd
    return pd.DataFrame([{
        "transaction_id": "TXN-TEST-001", "description": "ambiguous payment",
        "amount": 95.0, "customer_score": 0.40, "amount_score": 0.90,
        "date_difference": 5, "confidence": 60.0,
    }])


def invoice():
    return {"invoice_id": "INV-TEST-001", "customer": "Alpha", "amount": 100.0, "invoice_date": "2024-01-10"}


def mock_response(payload):
    class Response:
        def raise_for_status(self):
            return None
        def json(self):
            return {"response": json.dumps(payload)}
    return Response()


@pytest.mark.unit
def test_investigator_success_responses(monkeypatch):
    for payload in [
        {"decision": "MATCHED", "confidence": 0.95, "reason": "Exact customer and amount match."},
        {"decision": "AMOUNT_MISMATCH", "confidence": 0.90, "reason": "Customer matches but amount differs."},
        {"decision": "HUMAN_REVIEW", "confidence": 0.50, "reason": "Evidence is ambiguous."},
    ]:
        monkeypatch.setattr(investigator.requests, "post", lambda *args, payload=payload, **kwargs: mock_response(payload))
        result = investigator.investigate(invoice(), candidate_frame())
        assert result["decision"] == payload["decision"]
        assert 0 <= result["confidence"] <= 1


@pytest.mark.unit
def test_investigator_timing_and_missing_responses(monkeypatch):
    timing = candidate_frame().assign(amount=100.0, customer_score=0.9, amount_score=1.0, date_difference=5)
    assert investigator.investigate(invoice(), timing)["decision"] == "TIMING_DIFFERENCE"
    missing = investigator.investigate(invoice(), candidate_frame().iloc[0:0])
    assert missing["decision"] == "MISSING_PAYMENT"


@pytest.mark.unit
def test_investigator_invalid_decision_and_confidence(monkeypatch):
    payload = {"decision": "NOT_A_DECISION", "confidence": "invalid", "reason": "bad output"}
    monkeypatch.setattr(investigator.requests, "post", lambda *args, **kwargs: mock_response(payload))
    result = investigator.investigate(invoice(), candidate_frame())
    assert result == {"decision": "HUMAN_REVIEW", "confidence": 0.0, "reason": "The AI could not provide a usable confidence score."}


@pytest.mark.unit
def test_investigator_invalid_outputs_are_safe(monkeypatch):
    class InvalidResponse:
        def raise_for_status(self):
            return None
        def json(self):
            return {"response": "not json"}
    monkeypatch.setattr(investigator.requests, "post", lambda *args, **kwargs: InvalidResponse())
    result = investigator.investigate(invoice(), candidate_frame())
    assert result["decision"] == "HUMAN_REVIEW"
    assert result["confidence"] == 0.0

    monkeypatch.setattr(investigator.requests, "post", lambda *args, **kwargs: (_ for _ in ()).throw(requests.Timeout()))
    assert investigator.investigate(invoice(), candidate_frame())["decision"] == "HUMAN_REVIEW"

    monkeypatch.setattr(investigator.requests, "post", lambda *args, **kwargs: (_ for _ in ()).throw(requests.ConnectionError()))
    assert investigator.investigate(invoice(), candidate_frame())["decision"] == "HUMAN_REVIEW"


@pytest.mark.unit
def test_investigator_hybrid_decisions():
    import pandas as pd
    base = candidate_frame()
    exact = base.copy()
    exact.loc[0, ["amount", "customer_score", "date_difference"]] = [100.0, 0.9, 0]
    assert investigator.investigate(invoice(), exact)["decision"] == "MATCHED"
    split = pd.concat([base.assign(customer_score=0.9), base.assign(transaction_id="TXN-TEST-002", amount=5.0, customer_score=0.9)])
    assert investigator.investigate(invoice(), split)["decision"] == "SPLIT_PAYMENT"
