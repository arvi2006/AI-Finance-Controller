import pandas as pd
import pytest

from src.forecasting import cash_forecast


@pytest.mark.unit
def test_current_cash_uses_numeric_bank_amounts(bank_transactions):
    expected = pd.to_numeric(bank_transactions["amount"]).sum()
    assert cash_forecast.calculate_current_cash(bank_transactions) == pytest.approx(expected)


@pytest.mark.unit
def test_forecast_rolls_cash_forward_and_has_expected_schema(monkeypatch, invoices, bank_transactions):
    monkeypatch.setattr(cash_forecast, "RECONCILIATION_PATH", cash_forecast.Path("missing.csv"))
    forecast = cash_forecast.generate_cash_forecast(invoices.iloc[:2], bank_transactions.iloc[:1], "2024-01-10", 3, 5)
    assert list(forecast.columns) == ["date", "opening_cash", "expected_inflows", "expected_outflows", "net_cash_flow", "closing_cash"]
    assert len(forecast) == 3
    assert forecast.loc[0, "opening_cash"] == pytest.approx(100.0)
    assert forecast.loc[1, "opening_cash"] == pytest.approx(forecast.loc[0, "closing_cash"])
    assert (forecast["net_cash_flow"] == forecast["expected_inflows"] - forecast["expected_outflows"]).all()
    assert (forecast["closing_cash"] == forecast["opening_cash"] + forecast["net_cash_flow"]).all()


@pytest.mark.unit
def test_expected_inflows_exclude_matched_and_schedule_overdue(monkeypatch, invoices, bank_transactions, tmp_path):
    reconciliation_path = tmp_path / "reconciliation.csv"
    pd.DataFrame({"invoice_id": ["INV-TEST-001"], "status": ["MATCHED"]}).to_csv(reconciliation_path, index=False)
    monkeypatch.setattr(cash_forecast, "RECONCILIATION_PATH", reconciliation_path)
    inflows = cash_forecast.calculate_expected_inflows(invoices.iloc[:2], bank_transactions.iloc[:1], "2024-01-10", 5)
    assert inflows.loc[pd.Timestamp("2024-01-10")] == pytest.approx(200.0)
    assert inflows.sum() == pytest.approx(200.0)


@pytest.mark.unit
def test_summary_horizons_and_row_order_independence(monkeypatch, invoices, bank_transactions):
    monkeypatch.setattr(cash_forecast, "RECONCILIATION_PATH", cash_forecast.Path("missing.csv"))
    first = cash_forecast.generate_cash_forecast(invoices, bank_transactions, "2024-01-10", 30, 10)
    second = cash_forecast.generate_cash_forecast(invoices, bank_transactions.sample(frac=1, random_state=7), "2024-01-10", 30, 10)
    pd.testing.assert_frame_equal(first, second)
    summary = cash_forecast.get_cash_summary(first)
    assert summary["current_cash"] == pytest.approx(cash_forecast.calculate_current_cash(bank_transactions))
    assert summary["7_day_cash"] == pytest.approx(first.loc[6, "closing_cash"])
    assert summary["14_day_cash"] == pytest.approx(first.loc[13, "closing_cash"])
    assert summary["30_day_cash"] == pytest.approx(first.loc[29, "closing_cash"])
    assert summary["total_expected_outflows"] == pytest.approx(300.0)
    assert summary["minimum_projected_cash"] == pytest.approx(first["closing_cash"].min())


@pytest.mark.unit
def test_empty_inputs_are_safe():
    empty = pd.DataFrame()
    assert cash_forecast.calculate_current_cash(empty) == 0.0
    forecast = cash_forecast.generate_cash_forecast(empty, empty, "2024-01-01", 2)
    assert len(forecast) == 2
    assert cash_forecast.get_cash_summary(pd.DataFrame())["current_cash"] == 0.0
