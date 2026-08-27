from pathlib import Path

import pandas as pd


RECONCILIATION_PATH = Path("data/generated/reconciliation_results.csv")
FORECAST_OUTPUT_PATH = Path("data/generated/cash_forecast.csv")
DEFAULT_DAILY_OPERATING_OUTFLOW = 5000.0
PAID_STATUS = "MATCHED"


def _numeric_series(frame, column):
	if column not in frame.columns:
		return pd.Series(0.0, index=frame.index, dtype=float)
	return pd.to_numeric(frame[column], errors="coerce").fillna(0.0)


def _forecast_start(forecast_date):
	if forecast_date is None:
		return pd.Timestamp.today().normalize()
	parsed = pd.to_datetime(forecast_date, errors="coerce")
	if pd.isna(parsed):
		return pd.Timestamp.today().normalize()
	return parsed.normalize()


def calculate_current_cash(bank_transactions):
	"""Sum observed bank transaction amounts.

	The supplied synthetic bank data contains positive payment/inflow
	transactions only. This is therefore a cash-receipts total, not a
	complete ledger balance: expenses, opening balance, and other debits
	are not represented.
	"""

	if bank_transactions is None or bank_transactions.empty:
		return 0.0
	return float(_numeric_series(bank_transactions, "amount").sum())


def _load_reconciliation():
	if not RECONCILIATION_PATH.exists():
		return pd.DataFrame()
	try:
		return pd.read_csv(RECONCILIATION_PATH)
	except (OSError, pd.errors.ParserError, ValueError):
		return pd.DataFrame()


def calculate_expected_inflows(
	invoices,
	bank_transactions,
	forecast_date,
	days,
):
	"""Return deterministic expected invoice inflows by forecast date.

	Only invoices marked MATCHED in the optional reconciliation output are
	treated as paid. Other invoices are conservatively treated as fully
	outstanding; this avoids claiming that a partial or uncertain payment
	has collected the full invoice. Overdue invoices are scheduled on the
	first forecast day, while future invoices use their invoice date.
	"""

	start = _forecast_start(forecast_date)
	horizon = max(int(days), 0)
	dates = pd.date_range(start=start, periods=horizon, freq="D")
	inflows = pd.Series(0.0, index=dates, name="expected_inflows")
	if invoices is None or invoices.empty or horizon == 0:
		return inflows

	invoice_data = invoices.copy()
	if "invoice_id" not in invoice_data.columns or "amount" not in invoice_data.columns:
		return inflows
	invoice_data["amount"] = _numeric_series(invoice_data, "amount")
	invoice_data["invoice_date"] = pd.to_datetime(
		invoice_data.get("invoice_date"),
		errors="coerce",
	)

	reconciliation = _load_reconciliation()
	if not reconciliation.empty and {"invoice_id", "status"}.issubset(reconciliation.columns):
		paid_ids = set(
			reconciliation.loc[
				reconciliation["status"].astype(str).eq(PAID_STATUS),
				"invoice_id",
			]
		)
		invoice_data = invoice_data[~invoice_data["invoice_id"].isin(paid_ids)]

	for _, invoice in invoice_data.iterrows():
		invoice_date = invoice["invoice_date"]
		if pd.isna(invoice_date):
			payment_date = start
		elif invoice_date < start:
			payment_date = start
		else:
			payment_date = invoice_date.normalize()

		if payment_date in inflows.index:
			inflows.loc[payment_date] += float(invoice["amount"])

	return inflows


def generate_cash_forecast(
	invoices,
	bank_transactions,
	forecast_date=None,
	days=30,
	daily_operating_outflow=DEFAULT_DAILY_OPERATING_OUTFLOW,
):
	"""Generate a deterministic daily cash forecast.

	``expected_outflows`` are not observed bank expenses. They use the
	explicit synthetic operating expense assumption supplied by the caller.
	"""

	horizon = max(int(days), 0)
	start = _forecast_start(forecast_date)
	dates = pd.date_range(start=start, periods=horizon, freq="D")
	inflows = calculate_expected_inflows(
		invoices,
		bank_transactions,
		start,
		horizon,
	)
	daily_outflow = float(pd.to_numeric(daily_operating_outflow, errors="coerce"))
	if pd.isna(daily_outflow):
		daily_outflow = DEFAULT_DAILY_OPERATING_OUTFLOW

	current_cash = calculate_current_cash(bank_transactions)
	rows = []
	opening_cash = current_cash
	for date in dates:
		expected_inflows = float(inflows.get(date, 0.0))
		net_cash_flow = expected_inflows - daily_outflow
		closing_cash = opening_cash + net_cash_flow
		rows.append({
			"date": date,
			"opening_cash": opening_cash,
			"expected_inflows": expected_inflows,
			"expected_outflows": daily_outflow,
			"net_cash_flow": net_cash_flow,
			"closing_cash": closing_cash,
		})
		opening_cash = closing_cash

	return pd.DataFrame(
		rows,
		columns=[
			"date",
			"opening_cash",
			"expected_inflows",
			"expected_outflows",
			"net_cash_flow",
			"closing_cash",
		],
	)


def get_cash_summary(forecast):
	"""Return key cash-position metrics from a generated forecast."""

	if forecast is None or forecast.empty:
		return {
			"current_cash": 0.0,
			"7_day_cash": 0.0,
			"14_day_cash": 0.0,
			"30_day_cash": 0.0,
			"minimum_projected_cash": 0.0,
			"minimum_cash_date": None,
			"total_expected_inflows": 0.0,
			"total_expected_outflows": 0.0,
		}

	closing = pd.to_numeric(forecast["closing_cash"], errors="coerce").fillna(0.0)
	date_values = pd.to_datetime(forecast["date"], errors="coerce")
	minimum_index = closing.idxmin()

	def cash_at(day):
		return float(closing.iloc[min(day, len(closing) - 1)])

	return {
		"current_cash": float(_numeric_series(forecast, "opening_cash").iloc[0]),
		"7_day_cash": cash_at(6),
		"14_day_cash": cash_at(13),
		"30_day_cash": cash_at(29),
		"minimum_projected_cash": float(closing.loc[minimum_index]),
		"minimum_cash_date": date_values.loc[minimum_index],
		"total_expected_inflows": float(_numeric_series(forecast, "expected_inflows").sum()),
		"total_expected_outflows": float(_numeric_series(forecast, "expected_outflows").sum()),
	}


def main():
	invoices_path = Path("data/generated/invoices.csv")
	bank_path = Path("data/generated/bank_transactions.csv")
	if not invoices_path.exists() or not bank_path.exists():
		missing = invoices_path if not invoices_path.exists() else bank_path
		print(f"ERROR: Missing input file: {missing}")
		return

	invoices = pd.read_csv(invoices_path)
	bank_transactions = pd.read_csv(bank_path)
	forecast = generate_cash_forecast(invoices, bank_transactions)
	summary = get_cash_summary(forecast)
	forecast.to_csv(FORECAST_OUTPUT_PATH, index=False)

	print("=" * 60)
	print("AI FINANCE CONTROLLER")
	print("CASH POSITION FORECAST")
	print("=" * 60)
	print(f"\nCurrent cash: {summary['current_cash']:,.2f}")
	print(f"7-day projected cash: {summary['7_day_cash']:,.2f}")
	print(f"14-day projected cash: {summary['14_day_cash']:,.2f}")
	print(f"30-day projected cash: {summary['30_day_cash']:,.2f}")
	print(f"Minimum projected cash: {summary['minimum_projected_cash']:,.2f}")
	print(f"Minimum cash date: {summary['minimum_cash_date']}")
	print(f"Expected inflows: {summary['total_expected_inflows']:,.2f}")
	print(f"Expected outflows: {summary['total_expected_outflows']:,.2f}")
	print(f"Synthetic daily operating expense assumption: {DEFAULT_DAILY_OPERATING_OUTFLOW:,.2f}")
	print("\nFirst 10 forecast rows:")
	print(forecast.head(10).to_string(index=False))
	print(f"\nForecast saved to: {FORECAST_OUTPUT_PATH}")


if __name__ == "__main__":
	main()
