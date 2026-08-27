from pathlib import Path

import pandas as pd
import streamlit as st
from typing import Dict, Any


DATA_DIR = Path("data/generated")
FILES: Dict[str, Path] = {
	"invoices": DATA_DIR / "invoices.csv",
	"bank_transactions": DATA_DIR / "bank_transactions.csv",
	"reconciliation": DATA_DIR / "reconciliation_results.csv",
	"ai_results": DATA_DIR / "ai_reconciliation_results.csv",
	"metrics": DATA_DIR / "final_evaluation.csv",
	"exceptions": DATA_DIR / "exception_report.csv",
	"prioritized": DATA_DIR / "prioritized_exceptions.csv",
	"cash_forecast": DATA_DIR / "cash_forecast.csv",
}

st.set_page_config(
	page_title="AI Finance Controller",
	page_icon=":bar_chart:",
	layout="wide",
	initial_sidebar_state="expanded",
)

st.markdown(
	"""
	<style>
	@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');
	:root { --paper: #fef6ec; --ink: #0b0b0c; --muted: #6b6357; --orange: #ea580c; --lilac: #c7b8ff; --white: #fff; }
	* { box-sizing: border-box; }
	html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; color: var(--ink); }
	body { background: var(--paper); }
	h1, h2, h3 { font-family: 'Space Grotesk', sans-serif; letter-spacing: 0; color: var(--ink); }
	.hero { padding: 1.3rem 1.4rem 1.2rem; background: var(--white); border: 3px solid var(--ink); border-radius: 16px; box-shadow: 7px 7px 0 var(--ink); margin: .3rem .2rem 2rem 0; }
	.hero-head { display: flex; align-items: center; gap: .9rem; }
	.hero-mark { width: 48px; height: 48px; flex: 0 0 48px; border: 3px solid var(--ink); border-radius: 12px; background: var(--orange); box-shadow: 4px 4px 0 var(--ink); transform: rotate(-3deg); }
	.hero h1 { font-size: clamp(1.8rem, 3vw, 2.8rem); line-height: .95; text-transform: uppercase; margin: 0; }
	.hero p { color: var(--muted); margin: .6rem 0 0; font-size: .86rem; font-weight: 700; letter-spacing: .13em; text-transform: uppercase; }
	.kpi, .cash-kpi { background: var(--white); border: 3px solid var(--ink); border-radius: 15px; box-shadow: 6px 6px 0 var(--ink); min-width: 0; box-sizing: border-box; }
	.kpi { padding: 1rem 1.05rem; min-height: 112px; }
	.kpi-label, .cash-kpi-label { color: var(--muted); font-size: .7rem; font-weight: 700; text-transform: uppercase; letter-spacing: .08em; line-height: 1.25; white-space: normal; overflow-wrap: anywhere; word-break: normal; }
	.kpi-value, .cash-kpi-value { color: var(--ink); font-family: 'Space Grotesk', sans-serif; font-size: clamp(1.15rem, 1.8vw, 1.75rem); font-weight: 700; line-height: 1.2; margin-top: .5rem; white-space: normal; overflow-wrap: anywhere; word-break: normal; }
	.kpi-currency .kpi-value, .cash-kpi-value { font-size: clamp(.9rem, 1.25vw, 1.2rem); line-height: 1.3; }
	.cash-kpi { padding: 1rem; min-height: 126px; width: 100%; }
	.section-rule { border-top: 3px solid var(--ink); margin: 2.2rem 0 1.1rem; }
	[data-testid="stSidebar"] { background: var(--paper); border-right: 3px solid var(--ink); }
	[data-testid="stSidebar"] h3 { text-transform: uppercase; letter-spacing: .1em; }
	[data-testid="stSidebar"] [data-testid="stRadio"] label { border: 2px solid var(--ink); border-radius: 9px; padding: .45rem .6rem; margin: .25rem 0; font-weight: 700; background: var(--white); }
	[data-testid="stSidebar"] [data-testid="stRadio"] label:hover { background: var(--lilac); }
	[data-testid="stButton"] button, button[kind="primary"] { background: var(--orange); color: var(--white); border: 3px solid var(--ink); border-radius: 10px; box-shadow: 4px 4px 0 var(--ink); font-weight: 800; text-transform: uppercase; letter-spacing: .05em; }
	[data-testid="stButton"] button:hover { background: var(--lilac); color: var(--ink); transform: translate(-1px, -1px); box-shadow: 6px 6px 0 var(--ink); }
	[data-testid="stTextInput"] input, [data-testid="stSelectbox"] div, [data-testid="stMultiSelect"] div, [data-testid="stSlider"] { border-color: var(--ink); }
	[data-testid="stDataFrame"] { border: 3px solid var(--ink); border-radius: 12px; overflow: hidden; box-shadow: 5px 5px 0 var(--ink); }
	[data-testid="stDataFrame"] div[role="columnheader"] { background: var(--lilac); color: var(--ink); font-weight: 800; }
	[data-testid="stMetric"] { background: var(--white); border: 3px solid var(--ink); border-radius: 12px; box-shadow: 4px 4px 0 var(--ink); padding: .7rem; }
	</style>
	</style>
	""",
	unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def _read_csv(path: str) -> pd.DataFrame:
	return pd.read_csv(path)


def load_csv_safe(name: str, required: bool = True) -> pd.DataFrame:
	path = FILES[name]
	if not path.exists():
		if required:
			commands = {
				"cash_forecast": "python -m src.forecasting.cash_forecast",
				"prioritized": "python -m src.evaluation.exception_prioritizer",
				"metrics": "python -m src.evaluation.metrics",
			}
			command = commands.get(name, "the relevant pipeline module")
			st.error(f"Required data file is missing: `{path}`. Run `{command}` to generate it.")
		return pd.DataFrame()
	try:
		return _read_csv(str(path))
	except (OSError, pd.errors.ParserError, ValueError) as error:
		st.error(f"Could not read `{path}`: {error}")
		return pd.DataFrame()


load_csv = load_csv_safe


def validate_columns(frame: pd.DataFrame, required_columns: list[str], label: str) -> bool:
	missing = [column for column in required_columns if column not in frame.columns]
	if missing:
		st.error(f"{label} is missing required columns: {', '.join(missing)}")
		return False
	return True


def metric_value(metrics: dict, key: str, default: int = 0) -> Any:
	value = metrics.get(key, default)
	if pd.isna(value):
		return default
	return value


def fmt_number(value: Any, decimals: int = 0) -> str:
	if decimals:
		return f"{float(value):,.{decimals}f}"
	return f"{int(float(value)):,}"


def format_currency(value: Any) -> str:
	try:
		number = float(value)
	except (TypeError, ValueError):
		return "₹0"
	if pd.isna(number):
		return "₹0"
	sign = "-" if number < 0 else ""
	whole, fraction = f"{abs(number):.2f}".split(".")
	if len(whole) > 3:
		last_three = whole[-3:]
		remaining = whole[:-3]
		groups = []
		while remaining:
			groups.insert(0, remaining[-2:])
			remaining = remaining[:-2]
		whole = ",".join(groups + [last_three])
	return f"{sign}₹{whole}.{fraction}"


def kpi(label: str, value: Any, currency: bool = False) -> None:
	card_class = "kpi kpi-currency" if currency else "kpi"
	st.markdown(
		f'<div class="{card_class}"><div class="kpi-label">{label}</div>'
		f'<div class="kpi-value">{value}</div></div>',
		unsafe_allow_html=True,
	)


def cash_kpi(label: str, value: Any) -> None:
	st.markdown(
		f'<div class="cash-kpi"><div class="cash-kpi-label">{label}</div>'
		f'<div class="cash-kpi-value">{value}</div></div>',
		unsafe_allow_html=True,
	)


def section_title(title: str, subtitle: str | None = None) -> None:
	st.markdown('<div class="section-rule"></div>', unsafe_allow_html=True)
	section_numbers = {
		"Reconciliation overview": "01",
		"Risk prioritization": "02",
		"Top risk exceptions": "03",
		"Human review queue": "04",
		"AI investigation": "05",
		"Cash position": "06",
		"Exception detail": "07",
		"Reconciliation": "01",
		"Invoice detail": "08",
		"Buildathon summary": "09",
	}
	number = section_numbers.get(title, "00")
	st.markdown(f'<div class="section-kicker">{number} / FINANCE OPS</div>', unsafe_allow_html=True)
	st.subheader(title)
	if subtitle:
		st.caption(subtitle)


def safe_columns(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
	return frame[[column for column in columns if column in frame.columns]]


def overview(reconciliation, prioritized, metrics):
	section_title("Reconciliation overview", "Deterministic matching remains the system of record.")
	left, right = st.columns([1.2, 1])
	with left:
		overview_values = pd.DataFrame({
			"Measure": ["Baseline accuracy", "AI-assisted accuracy", "Accuracy change", "Correct classifications", "Exceptions"],
			"Value": [
				f"{float(metric_value(metrics, 'baseline_accuracy')):.2f}%",
				f"{float(metric_value(metrics, 'ai_accuracy')):.2f}%",
				f"{float(metric_value(metrics, 'accuracy_delta')):+.2f}%",
				fmt_number(metric_value(metrics, "baseline_correct")),
				fmt_number(metric_value(metrics, "baseline_exceptions")),
			],
		})
		st.dataframe(overview_values, hide_index=True, use_container_width=True)
		if float(metric_value(metrics, "accuracy_delta")) == 0:
			st.caption("AI investigation improved exception handling without changing overall measured classification accuracy.")
	with right:
		if reconciliation.empty or "status" not in reconciliation:
			st.warning("Reconciliation results are unavailable.")
		else:
			status_counts = reconciliation["status"].fillna("UNKNOWN").value_counts().rename_axis("Status").reset_index(name="Records")
			st.bar_chart(
				status_counts.set_index("Status")["Records"],
				height=310,
				use_container_width=True,
			)


def risk_section(prioritized):
	section_title("Risk prioritization", "Risk priority and AI investigation are separate operational signals.")
	if prioritized.empty:
		st.warning("Prioritized exceptions are unavailable.")
		return
	counts = prioritized["priority"].value_counts()
	cols = st.columns(4)
	for column, priority in zip(cols, ["P0_CRITICAL", "P1_HIGH", "P2_MEDIUM", "P4_NORMAL"]):
		with column:
			kpi(priority.replace("_", " "), fmt_number(counts.get(priority, 0)))
	ai = prioritized.get("ai_action", pd.Series(dtype=str)).fillna("NOT_REQUIRED")
	st.caption(
		f"AI investigated: {(prioritized.get('ai_investigated', False) == True).sum()}  |  "
		f"AI auto-resolved: {(ai == 'AUTO_RESOLVE').sum()}  |  "
		f"AI human-review: {(ai == 'HUMAN_REVIEW').sum()}"
	)


def top_exceptions(prioritized):
	section_title("Top risk exceptions", "Sorted by operational risk score, highest first.")
	if prioritized.empty:
		return
	columns = ["invoice_id", "priority", "risk_score", "status", "final_status", "expected_status", "confidence", "risk_reason", "ai_investigated", "ai_decision", "ai_confidence"]
	top = prioritized.sort_values("risk_score", ascending=False, kind="mergesort").head(10)
	top_display = safe_columns(top, columns)
	top_display = top_display.style.apply(
		lambda row: [
			"background-color: #ffe4df; color: #8f2d24; font-weight: 700"
			if row["priority"] == "P0_CRITICAL" else ""
			for _ in row
		],
		axis=1,
	)
	st.dataframe(
		top_display,
		hide_index=True,
		use_container_width=True,
		column_config={
			"risk_score": st.column_config.NumberColumn("Risk score", format="%.2f"),
			"confidence": st.column_config.NumberColumn("Confidence", format="%.2f"),
			"ai_confidence": st.column_config.NumberColumn("AI confidence", format="%.2f"),
		},
	)


def human_review(prioritized):
	section_title("Human review queue", "Review cases where automation did not reach a reliable resolution.")
	if prioritized.empty:
		st.info("No exception data is available.")
		return
	actions = prioritized.get("ai_action", pd.Series("NOT_REQUIRED", index=prioritized.index)).fillna("NOT_REQUIRED")
	queue = prioritized[(actions == "HUMAN_REVIEW") | (prioritized["status"] == "REVIEW_REQUIRED")].copy()
	if queue.empty:
		st.success("The human review queue is empty.")
		return
	a, b, c, d = st.columns(4)
	with a:
		priority_filter = st.multiselect("Priority", sorted(queue["priority"].dropna().unique()), default=list(sorted(queue["priority"].dropna().unique())))
	with b:
		status_filter = st.multiselect("Status", sorted(queue["status"].dropna().unique()), default=list(sorted(queue["status"].dropna().unique())))
	with c:
		confidence = pd.to_numeric(queue["confidence"], errors="coerce").fillna(0)
		confidence_filter = st.slider("Confidence range", 0.0, 100.0, (float(confidence.min()), float(confidence.max())))
	with d:
		ai_filter = st.selectbox("AI investigated", ["All", "Yes", "No"])
	filtered = queue[
		queue["priority"].isin(priority_filter)
		& queue["status"].isin(status_filter)
		& pd.to_numeric(queue["confidence"], errors="coerce").fillna(0).between(*confidence_filter)
	]
	if ai_filter != "All":
		filtered = filtered[filtered["ai_investigated"] == (ai_filter == "Yes")]
	columns = ["invoice_id", "status", "expected_status", "confidence", "ai_decision", "ai_confidence", "ai_reason", "ai_time_seconds"]
	st.dataframe(safe_columns(filtered, columns), hide_index=True, use_container_width=True)


def ai_investigation(prioritized, metrics):
	section_title("AI investigation", "Local AI is used for ambiguous exceptions; insufficient confidence stays in review.")
	cols = st.columns(6)
	values = [
		("Investigations", "ai_investigations"),
		("Auto-resolved", "ai_auto_resolved"),
		("Human review", "human_review"),
		("Failures", "ai_failures"),
		("Average latency", "average_ai_time_seconds"),
		("Total AI time", "total_ai_time_seconds"),
	]
	for column, (label, key) in zip(cols, values):
		with column:
			value = metric_value(metrics, key)
			kpi(label, f"{float(value):.2f}s" if "time" in key else fmt_number(value))
	investigated = prioritized[prioritized["ai_investigated"] == True] if not prioritized.empty else pd.DataFrame()
	if investigated.empty:
		st.info("No AI investigations are present in the exception report.")
		return
	columns = ["invoice_id", "ai_decision", "ai_confidence", "ai_action", "ai_reason", "ai_time_seconds"]
	st.dataframe(safe_columns(investigated, columns), hide_index=True, use_container_width=True)


def exception_detail(prioritized):
	section_title("Exception detail", "Inspect the evidence and disposition for one unresolved invoice.")
	if prioritized.empty:
		st.info("No exception data is available.")
		return
	selected_id = st.selectbox("Select Invoice", prioritized["invoice_id"].astype(str).tolist())
	row = prioritized[prioritized["invoice_id"].astype(str) == selected_id]
	if row.empty:
		st.error("Selected invoice not found in exception data.")
		return
	row = row.iloc[0]
	left, right = st.columns(2)
	details = [
		("Invoice ID", row.get("invoice_id")),
		("System Status", row.get("status")),
		("Final Status", row.get("final_status")),
		("Expected Status", row.get("expected_status")),
		("System Confidence", row.get("confidence")),
		("Risk Priority", row.get("priority")),
		("Risk Score", row.get("risk_score")),
		("Risk Reason", row.get("risk_reason")),
	]
	with left:
		for label, value in details[:4]:
			st.metric(label, "" if pd.isna(value) else str(value))
	with right:
		for label, value in details[4:]:
			st.metric(label, "" if pd.isna(value) else str(value))
	if bool(row.get("ai_investigated", False)):
		st.markdown("**AI evidence**")
		st.dataframe(pd.DataFrame([{
			"AI Decision": row.get("ai_decision", ""),
			"AI Confidence": row.get("ai_confidence", ""),
			"AI Action": row.get("ai_action", ""),
			"AI Reason": row.get("ai_reason", ""),
			"AI Latency": row.get("ai_time_seconds", ""),
		}]), hide_index=True, use_container_width=True)


def reconciliation_page(reconciliation, bank_transactions):
	section_title("Reconciliation", "Inspect deterministic invoice-to-bank matching results.")
	if reconciliation.empty:
		st.warning("Reconciliation results are unavailable.")
		return
	left, right, third, fourth = st.columns(4)
	left.metric("Total invoices", fmt_number(len(reconciliation)))
	fourth.metric("Total bank transactions", fmt_number(len(bank_transactions)))
	matched = reconciliation["status"].eq("MATCHED").sum()
	third.metric("Matched records", fmt_number(matched))
	right.metric("Operational flags", fmt_number(len(reconciliation) - matched))
	st.caption("Operational flags are all non-MATCHED reconciliation records.")
	st.metric("Match rate", f"{matched / len(reconciliation) * 100:.2f}%")
	status_options = sorted(reconciliation["status"].dropna().unique())
	selected_status = st.multiselect("Status", status_options, default=status_options, key="reconciliation_status")
	confidence = pd.to_numeric(reconciliation["confidence"], errors="coerce").fillna(0)
	confidence_range = st.slider("Confidence range", 0.0, 100.0, (float(confidence.min()), float(confidence.max())), key="reconciliation_confidence")
	filtered = reconciliation[
		reconciliation["status"].isin(selected_status)
		& confidence.between(*confidence_range)
	].sort_values("confidence", ascending=False, kind="mergesort")
	st.dataframe(safe_columns(filtered, ["invoice_id", "invoice_amount", "matched_transaction_ids", "matched_amount", "difference", "status", "confidence"]), hide_index=True, use_container_width=True)


def exception_intelligence(prioritized):
	risk_section(prioritized)
	if prioritized.empty:
		return
	critical = prioritized[prioritized["priority"] == "P0_CRITICAL"]
	if not critical.empty:
		record = critical.sort_values("risk_score", ascending=False).iloc[0]
		st.error(
			f"Critical false positive: {record['invoice_id']} | "
			f"{record['status']} expected {record['expected_status']} | "
			f"Confidence {float(record['confidence']):.0f}% | "
			f"Risk score {float(record['risk_score']):.0f}\n\n"
			f"{record['risk_reason']}"
		)
	top_exceptions(prioritized)
	exception_detail(prioritized)


def ai_page(ai_results, prioritized, metrics):
	ai_investigation(prioritized, metrics)
	st.caption("AI failures are included in human-review cases.")
	if ai_results.empty:
		st.info("AI investigation results are unavailable.")
		return
	actions = ai_results.get("ai_action", pd.Series("NOT_REQUIRED", index=ai_results.index)).fillna("NOT_REQUIRED")
	investigated = ai_results[actions != "NOT_REQUIRED"].copy()
	if investigated.empty:
		st.info("No AI investigations are present.")
		return
	decision_filter = st.multiselect("AI decision", sorted(investigated["ai_decision"].dropna().unique()), default=list(sorted(investigated["ai_decision"].dropna().unique())), key="ai_decision")
	action_filter = st.multiselect("AI action", sorted(investigated["ai_action"].dropna().unique()), default=list(sorted(investigated["ai_action"].dropna().unique())), key="ai_action")
	confidence = pd.to_numeric(investigated["ai_confidence"], errors="coerce").fillna(0)
	confidence_range = st.slider("AI confidence", 0.0, 1.0, (float(confidence.min()), float(confidence.max())), key="ai_confidence")
	filtered = investigated[investigated["ai_decision"].isin(decision_filter) & investigated["ai_action"].isin(action_filter) & confidence.between(*confidence_range)]
	st.dataframe(safe_columns(filtered, ["invoice_id", "ai_decision", "ai_confidence", "ai_action", "ai_reason", "ai_time_seconds"]), hide_index=True, use_container_width=True)
	st.caption("Low-confidence or failed AI investigations remain in human review.")


def cash_page(cash_forecast):
	section_title("Cash position", "A 30-day trajectory based on the generated forecast.")
	if cash_forecast.empty:
		st.warning("Cash forecast is unavailable. Run `python -m src.forecasting.cash_forecast` first.")
		return
	cash_forecast = cash_forecast.copy()
	cash_forecast["date"] = pd.to_datetime(cash_forecast["date"], errors="coerce")
	last = cash_forecast.iloc[-1]
	first = cash_forecast.iloc[0]
	minimum = cash_forecast.loc[pd.to_numeric(cash_forecast["closing_cash"], errors="coerce").idxmin()]
	st.markdown("**Cash Position (Projected Closing Cash)**")
	position_values = [
		("Current Cash", first["opening_cash"]),
		("7-Day Projected Cash", cash_forecast.iloc[min(6, len(cash_forecast)-1)]["closing_cash"]),
		("14-Day Projected Cash", cash_forecast.iloc[min(13, len(cash_forecast)-1)]["closing_cash"]),
		("30-Day Projected Cash", last["closing_cash"]),
		("Minimum Projected Cash", minimum["closing_cash"]),
	]
	for column, (label, value) in zip(st.columns(5), position_values):
		with column:
			cash_kpi(label, format_currency(value))
	st.markdown("**Projected Closing Cash**")
	st.line_chart(cash_forecast.set_index("date")[["closing_cash"]], height=320, use_container_width=True)
	st.markdown("**Cash Flows (Daily Average)**")
	flow_values = [
		("Expected Inflows", cash_forecast["expected_inflows"].sum()),
		("Expected Outflows", cash_forecast["expected_outflows"].sum()),
	]
	for column, (label, value) in zip(st.columns(2), flow_values):
		with column:
			cash_kpi(label, format_currency(value))
	st.markdown("**Expected Daily Cash Flows**")
	st.line_chart(cash_forecast.set_index("date")[["expected_inflows", "expected_outflows"]], height=260, use_container_width=True)
	st.caption("Expected outflows use the synthetic operating expense assumption; they are not observed historical bank expenses.")
	if float(minimum["closing_cash"]) < float(first["opening_cash"]):
		st.warning("Projected cash position falls below the current cash baseline.")
	else:
		st.success("Projected cash position remains above the current cash baseline.")


def human_review_page(prioritized, invoices, bank_transactions):
	human_review(prioritized)
	exception_detail_with_evidence(prioritized, invoices, bank_transactions)


def exception_detail_with_evidence(prioritized, invoices, bank_transactions):
	section_title("Invoice detail", "Trace the reconciliation evidence for one exception.")
	if prioritized.empty:
		return
	selected_id = st.selectbox("Select Invoice", prioritized["invoice_id"].astype(str).tolist(), key="detail_invoice")
	row = prioritized[prioritized["invoice_id"].astype(str) == selected_id].iloc[0]
	invoice_rows = invoices[invoices["invoice_id"].astype(str) == selected_id] if "invoice_id" in invoices else pd.DataFrame()
	if not invoice_rows.empty:
		invoice = invoice_rows.iloc[0]
		st.markdown("**Invoice**")
		st.dataframe(pd.DataFrame([{"Invoice ID": invoice.get("invoice_id"), "Customer": invoice.get("customer"), "Amount": format_currency(invoice.get("amount")), "Invoice Date": invoice.get("invoice_date")}]), hide_index=True, use_container_width=True)
	st.markdown("**Reconciliation and risk**")
	matched_ids = str(row.get("matched_transaction_ids", ""))
	matched_display = matched_ids if matched_ids and matched_ids != "nan" else "Bank evidence: No credible transaction found"
	st.dataframe(pd.DataFrame([{"System Status": row.get("status"), "Matched Transaction": matched_display, "Matched Amount": format_currency(row.get("matched_amount", 0)), "Difference": format_currency(row.get("difference", 0)), "Expected Status": row.get("expected_status"), "Priority": row.get("priority"), "Risk Score": row.get("risk_score"), "Risk Reason": row.get("risk_reason")}]), hide_index=True, use_container_width=True)
	if row.get("priority") in {"P0_CRITICAL", "P1_HIGH"} and row.get("status") != row.get("expected_status"):
		st.warning(
			"Why this is critical\n\n"
			f"The deterministic system classified this invoice as {row.get('status')} "
			f"with confidence {float(row.get('confidence', 0)):.0f}%, while the "
			f"evaluation ground truth identifies it as {row.get('expected_status')}."
		)
	if bool(row.get("ai_investigated", False)):
		st.markdown("**AI investigation**")
		st.dataframe(pd.DataFrame([{"AI Decision": row.get("ai_decision"), "AI Confidence": row.get("ai_confidence"), "AI Action": row.get("ai_action"), "AI Reason": row.get("ai_reason"), "AI Latency": row.get("ai_time_seconds")}]), hide_index=True, use_container_width=True)
	transaction_ids = [value for value in matched_ids.split(",") if value and value != "nan"]
	if transaction_ids and "transaction_id" in bank_transactions:
		evidence = bank_transactions[bank_transactions["transaction_id"].astype(str).isin(transaction_ids)]
		if not evidence.empty:
			st.markdown("**Bank evidence**")
			st.dataframe(safe_columns(evidence, ["transaction_id", "description", "amount", "transaction_date"]), hide_index=True, use_container_width=True)


def main():
	if st.sidebar.button("Refresh Data"):
		st.cache_data.clear()
		st.rerun()

	data = {
		"invoices": load_csv_safe("invoices"),
		"bank_transactions": load_csv_safe("bank_transactions"),
		"reconciliation": load_csv_safe("reconciliation"),
		"ai_results": load_csv_safe("ai_results", required=False),
		"metrics_frame": load_csv_safe("metrics"),
		"exceptions": load_csv_safe("exceptions", required=False),
		"prioritized": load_csv_safe("prioritized", required=False),
		"cash_forecast": load_csv_safe("cash_forecast", required=False),
	}
	metrics_frame = data["metrics_frame"]
	metrics = metrics_frame.iloc[0].to_dict() if not metrics_frame.empty else {}
	reconciliation = data["reconciliation"]
	prioritized = data["prioritized"]
	ai_results = data["ai_results"]
	invoices = data["invoices"]
	bank_transactions = data["bank_transactions"]
	cash_forecast = data["cash_forecast"]
	if not prioritized.empty and not reconciliation.empty:
		evidence_columns = ["invoice_id", "matched_transaction_ids", "matched_amount", "difference"]
		prioritized = prioritized.merge(
			reconciliation[[column for column in evidence_columns if column in reconciliation.columns]],
			on="invoice_id",
			how="left",
			validate="one_to_one",
		)
	validate_columns(metrics_frame, ["total_records", "baseline_accuracy", "ai_accuracy", "final_exceptions"], "Final evaluation")
	validate_columns(reconciliation, ["invoice_id", "status", "confidence"], "Reconciliation results")
	validate_columns(prioritized, ["invoice_id", "priority", "risk_score"], "Prioritized exceptions")

	st.markdown(
		'<div class="hero"><div class="hero-head"><div class="hero-mark"></div>'
		'<div><h1>AI Finance Controller</h1><p>Run the books and the cash position.</p></div>'
		'</div></div>',
		unsafe_allow_html=True,
	)
	with st.sidebar:
		st.markdown("### Operations")
		st.caption("LOCAL AI · FINANCE OPS")
		view = st.radio("Navigate", ["Executive Overview", "Reconciliation", "Exception Intelligence", "AI Investigation", "Cash Position", "Human Review"], label_visibility="collapsed")
		st.divider()
		st.caption("Deterministic reconciliation with measured AI exception handling.")

	kpi_values = [
		("Records Processed", fmt_number(metric_value(metrics, "total_records"))),
		("Baseline Accuracy", f"{float(metric_value(metrics, 'baseline_accuracy')):.2f}%"),
		("Final Accuracy", f"{float(metric_value(metrics, 'ai_accuracy')):.2f}%"),
		("Total Exceptions", fmt_number(metric_value(metrics, "final_exceptions"))),
		("Critical Exceptions", fmt_number(
			((prioritized.get("priority", pd.Series(dtype=str)) == "P0_CRITICAL").sum()
				if not prioritized.empty
				else 0)
		)),
		("AI Investigations", fmt_number(metric_value(metrics, "ai_investigations"))),
		("AI Auto-Resolved", fmt_number(metric_value(metrics, "ai_auto_resolved"))),
		("Human Review", fmt_number(metric_value(metrics, "human_review"))),
		("AI Failures", fmt_number(metric_value(metrics, "ai_failures"))),
		("30-Day Projected Cash", format_currency(cash_forecast.iloc[-1]["closing_cash"] if not cash_forecast.empty else 0)),
	]
	for row_start in range(0, len(kpi_values), 5):
		kpis = st.columns(5)
		for column, (label, value) in zip(kpis, kpi_values[row_start:row_start + 5]):
			with column:
				kpi(label, value, currency=label == "30-Day Projected Cash")

	if view == "Executive Overview":
		overview(reconciliation, prioritized, metrics)
		risk_section(prioritized)
		top_exceptions(prioritized)
		if not prioritized.empty:
			exception_detail_with_evidence(prioritized, invoices, bank_transactions)
	elif view == "Reconciliation":
		reconciliation_page(reconciliation, bank_transactions)
	elif view == "Exception Intelligence":
		exception_intelligence(prioritized)
	elif view == "AI Investigation":
		ai_page(ai_results, prioritized, metrics)
	elif view == "Cash Position":
		cash_page(cash_forecast)
	else:
		human_review_page(prioritized, invoices, bank_transactions)

	section_title("Buildathon summary")
	records = fmt_number(metric_value(metrics, "total_records"))
	accuracy = f"{float(metric_value(metrics, 'baseline_accuracy')):.2f}%"
	exceptions = fmt_number(metric_value(metrics, "final_exceptions"))
	investigations = fmt_number(metric_value(metrics, "ai_investigations"))
	st.info(
		f"{records} records processed through deterministic reconciliation, with "
		f"{accuracy} measured accuracy. {exceptions} exceptions remained. The "
		f"{investigations} high-uncertainty cases were investigated by the local AI "
		"agent, with unresolved cases remaining in human review. The 30-day cash "
		f"forecast is {format_currency(cash_forecast.iloc[-1]['closing_cash']) if not cash_forecast.empty else 'unavailable'}."
	)


if __name__ == "__main__":
	main()
