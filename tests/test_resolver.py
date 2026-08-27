import pandas as pd
import pytest

from src.agent import resolver


@pytest.mark.unit
def test_resolver_caps_unique_investigations(monkeypatch):
    invoices = pd.DataFrame([{"invoice_id": f"I{i}", "customer": "C", "amount": 100, "invoice_date": "2024-01-01"} for i in range(1, 8)])
    bank = pd.DataFrame()
    reconciliation = pd.DataFrame([{"invoice_id": "I1", "status": "REVIEW_REQUIRED", "confidence": 40}] + [{"invoice_id": f"I{i}", "status": "AMOUNT_MISMATCH", "confidence": 60 + i} for i in range(1, 7)])
    calls = []
    candidates = pd.DataFrame([{"transaction_id": "T", "description": "C", "amount": 100, "transaction_date": "2024-01-01", "customer_score": 0.9, "amount_score": 1.0, "date_difference": 0, "confidence": 0.5}])
    monkeypatch.setattr(resolver, "find_candidates", lambda invoice, transactions, top_k: calls.append(("find", invoice["invoice_id"])) or candidates)
    monkeypatch.setattr(resolver, "investigate", lambda invoice, candidates: calls.append(("investigate", invoice["invoice_id"])) or {"decision": "HUMAN_REVIEW", "confidence": 0.5, "reason": "ambiguous"})
    result = resolver.resolve_exceptions(invoices, bank, reconciliation)
    investigated = [value for kind, value in calls if kind == "find"]
    assert len(investigated) == resolver.MAX_AI_CASES
    assert len(set(investigated)) == resolver.MAX_AI_CASES
    assert [value for kind, value in calls if kind == "investigate"] == investigated
    assert len(result) == len(reconciliation)
    assert (result.loc[~result.invoice_id.isin(investigated), "final_status"] == result.loc[~result.invoice_id.isin(investigated), "status"]).all()


@pytest.mark.unit
def test_resolver_auto_resolve_threshold(monkeypatch):
    invoices = pd.DataFrame([{"invoice_id": "I1", "customer": "C", "amount": 100, "invoice_date": "2024-01-01"}])
    reconciliation = pd.DataFrame([{"invoice_id": "I1", "status": "REVIEW_REQUIRED", "confidence": 40}])
    candidates = pd.DataFrame([{"transaction_id": "T", "description": "C", "amount": 100, "transaction_date": "2024-01-01", "customer_score": 0.4, "amount_score": 0.9, "date_difference": 5, "confidence": 0.5}])
    monkeypatch.setattr(resolver, "find_candidates", lambda *args, **kwargs: candidates)
    monkeypatch.setattr(resolver, "investigate", lambda *args, **kwargs: {"decision": "MATCHED", "confidence": 0.79, "reason": "not enough"})
    low = resolver.resolve_exceptions(invoices, pd.DataFrame(), reconciliation)
    assert low.loc[0, "ai_action"] == "HUMAN_REVIEW"
    monkeypatch.setattr(resolver, "investigate", lambda *args, **kwargs: {"decision": "MATCHED", "confidence": 0.80, "reason": "strong"})
    high = resolver.resolve_exceptions(invoices, pd.DataFrame(), reconciliation)
    assert high.loc[0, "ai_action"] == "AUTO_RESOLVE"
    assert high.loc[0, "final_status"] == "MATCHED"


@pytest.mark.unit
def test_resolver_failure_is_counted_only_for_investigated_case(monkeypatch, capsys):
    invoices = pd.DataFrame([{"invoice_id": "I1", "customer": "C", "amount": 100, "invoice_date": "2024-01-01"}])
    reconciliation = pd.DataFrame([{"invoice_id": "I1", "status": "REVIEW_REQUIRED", "confidence": 40}])
    candidates = pd.DataFrame([{"transaction_id": "T", "description": "C", "amount": 100, "transaction_date": "2024-01-01", "customer_score": 0.4, "amount_score": 0.9, "date_difference": 5, "confidence": 0.5}])
    monkeypatch.setattr(resolver, "find_candidates", lambda *args, **kwargs: candidates)
    monkeypatch.setattr(resolver, "investigate", lambda *args, **kwargs: {"decision": "HUMAN_REVIEW", "confidence": 0.0, "reason": "Ollama request timed out."})
    result = resolver.resolve_exceptions(invoices, pd.DataFrame(), reconciliation)
    assert result.loc[0, "ai_action"] == "HUMAN_REVIEW"
    assert "AI failed           : 1" in capsys.readouterr().out
