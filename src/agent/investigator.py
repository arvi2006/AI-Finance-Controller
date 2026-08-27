import json
import requests


OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen2.5:1.5b"
MODEL_FALLBACK = "llama3:8b"

OLLAMA_TIMEOUT = 30

ALLOWED_DECISIONS = {
    "MATCHED",
    "AMOUNT_MISMATCH",
    "TIMING_DIFFERENCE",
    "SPLIT_PAYMENT",
    "MISSING_PAYMENT",
    "HUMAN_REVIEW",
}


def result(decision, confidence, reason):
    """Create a consistent investigator result."""
    return {
        "decision": decision,
        "confidence": float(confidence),
        "reason": reason,
    }


def investigate(invoice, candidates):
    """
    Hybrid reconciliation investigator.

    1. Python handles obvious financial cases.
    2. Ollama investigates genuinely ambiguous cases.
    """

    # ========================================================
    # NO CANDIDATES
    # ========================================================

    if candidates is None or candidates.empty:

        return result(
            "MISSING_PAYMENT",
            0.95,
            "No candidate bank transactions were found.",
        )

    # Keep only the strongest candidates.
    candidates = candidates.head(5).copy()

    # ========================================================
    # BEST CANDIDATE
    # ========================================================

    best = candidates.iloc[0]

    invoice_id = str(
        invoice["invoice_id"]
    )

    invoice_amount = float(
        invoice["amount"]
    )

    transaction_id = str(
        best["transaction_id"]
    )

    transaction_amount = float(
        best["amount"]
    )

    customer_score = float(
        best["customer_score"]
    )

    amount_score = float(
        best["amount_score"]
    )

    date_difference = int(
        best["date_difference"]
    )

    # ========================================================
    # CALCULATED EVIDENCE
    # ========================================================

    amount_difference = (
        transaction_amount
        - invoice_amount
    )

    absolute_difference = abs(
        amount_difference
    )

    exact_amount = (
        absolute_difference <= 0.01
    )

    strong_customer = (
        customer_score >= 0.60
    )

    close_date = (
        date_difference <= 2
    )

    # ========================================================
    # HYBRID RULE 1
    #
    # Strong customer + exact amount + close date
    # ========================================================

    if (
        strong_customer
        and exact_amount
        and close_date
    ):

        return result(
            "MATCHED",
            0.95,
            (
                f"Transaction {transaction_id} matches "
                f"the invoice amount and customer evidence, "
                f"with a {date_difference}-day date difference."
            ),
        )

    # ========================================================
    # HYBRID RULE 2
    #
    # Strong customer + very close amount + close date
    #
    # Example:
    # Invoice = 72482
    # Payment = 72382
    # Difference = 100
    # ========================================================

    if (
        strong_customer
        and amount_score >= 0.98
        and not exact_amount
        and close_date
    ):

        return result(
            "AMOUNT_MISMATCH",
            0.90,
            (
                f"Transaction {transaction_id} has strong "
                f"customer evidence and a close amount, "
                f"but differs from the invoice by "
                f"{absolute_difference:.0f}."
            ),
        )

    # ========================================================
    # HYBRID RULE 3
    #
    # Exact amount + strong customer + late payment
    # ========================================================

    if (
        strong_customer
        and exact_amount
        and date_difference > 2
    ):

        return result(
            "TIMING_DIFFERENCE",
            0.92,
            (
                f"Transaction {transaction_id} matches "
                f"the invoice amount and customer evidence "
                f"but was received {date_difference} days "
                f"after the invoice date."
            ),
        )

    # ========================================================
    # CHECK FOR SPLIT PAYMENT
    #
    # Python can reliably check whether two transactions
    # add up to the invoice amount.
    # ========================================================

    if len(candidates) >= 2:

        for i in range(
            len(candidates)
        ):

            for j in range(
                i + 1,
                len(candidates)
            ):

                first = candidates.iloc[i]
                second = candidates.iloc[j]

                first_amount = float(
                    first["amount"]
                )

                second_amount = float(
                    second["amount"]
                )

                combined = (
                    first_amount
                    + second_amount
                )

                combined_difference = abs(
                    combined
                    - invoice_amount
                )

                first_customer = float(
                    first["customer_score"]
                )

                second_customer = float(
                    second["customer_score"]
                )

                if (
                    combined_difference <= 0.01
                    and first_customer >= 0.60
                    and second_customer >= 0.60
                ):

                    return result(
                        "SPLIT_PAYMENT",
                        0.93,
                        (
                            f"Transactions "
                            f"{first['transaction_id']} and "
                            f"{second['transaction_id']} "
                            f"together equal the invoice amount."
                        ),
                    )

    # ========================================================
    # BUILD COMPACT LLM EVIDENCE
    # ========================================================

    candidate_lines = []

    for _, c in candidates.iterrows():

        candidate_lines.append(
            f"""
ID={c['transaction_id']}
Description={c['description']}
Amount={float(c['amount']):.0f}
CustomerScore={float(c['customer_score']):.2f}
AmountScore={float(c['amount_score']):.2f}
DateDifference={int(c['date_difference'])}
"""
        )

    candidates_text = "\n".join(
        candidate_lines
    )

    # ========================================================
    # LLM PROMPT
    # ========================================================

    prompt = f"""
You are a finance exception investigator. Classify ONE ambiguous invoice based ONLY on the supplied evidence.

INVOICE
ID={invoice_id}
Customer={invoice['customer']}
Amount={invoice_amount:.0f}
Date={invoice['invoice_date']}

BEST TRANSACTION
ID={transaction_id}
Amount={transaction_amount:.0f}
CustomerScore={customer_score:.2f}
AmountScore={amount_score:.2f}
DateDifference={date_difference}

AmountDifference={absolute_difference:.0f}

OTHER CANDIDATES
{candidates_text}

RULES (apply in order):

MATCHED: strong customer + exact amount + date <= 2 days
AMOUNT_MISMATCH: strong customer + amount differs
TIMING_DIFFERENCE: strong customer + exact amount + date > 2 days
SPLIT_PAYMENT: multiple credible payments add to invoice amount
MISSING_PAYMENT: no credible payment
HUMAN_REVIEW: evidence is genuinely unclear

Return ONLY a JSON object with three keys: "decision", "confidence", "reason".
- decision must be one of: MATCHED, AMOUNT_MISMATCH, TIMING_DIFFERENCE, SPLIT_PAYMENT, MISSING_PAYMENT, HUMAN_REVIEW
- confidence must be a number between 0.0 and 1.0
- reason should be a short 1-2 sentence explanation

Example: {{"decision":"MATCHED","confidence":0.95,"reason":"Transaction matches invoice with strong customer evidence"}}"""

    # ========================================================
    # OLLAMA
    # ========================================================

    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0,
            "num_ctx": 1024,
            "num_predict": 80,
        },
    }

    try:

        response = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=OLLAMA_TIMEOUT,
        )

        response.raise_for_status()

        data = response.json()

        raw = data.get(
            "response",
            ""
        ).strip()

        print(
            f"Raw Ollama response: {raw}"
        )

        if not raw:

            return result(
                "HUMAN_REVIEW",
                0.0,
                "Ollama returned an empty response.",
            )

        # Try parsing as JSON
        parsed = None
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            # Try extracting JSON from markdown code block
            import re
            match = re.search(r'\{.*\}', raw, re.DOTALL)
            if match:
                parsed = json.loads(match.group(0))

        if parsed is None:

            return result(
                "HUMAN_REVIEW",
                0.0,
                "Ollama returned invalid JSON.",
            )

        decision = str(
            parsed.get(
                "decision",
                "HUMAN_REVIEW",
            )
        ).upper().strip()

        if decision not in ALLOWED_DECISIONS:

            decision = "HUMAN_REVIEW"

        try:

            confidence = float(
                parsed.get(
                    "confidence",
                    0.0,
                )
            )

        except (ValueError, TypeError):

            confidence = 0.0

        confidence = max(
            0.0,
            min(
                1.0,
                confidence,
            ),
        )

        reason = str(
            parsed.get(
                "reason",
                "No explanation provided.",
            )
        ).strip()

        if confidence <= 0:

            return result(
                "HUMAN_REVIEW",
                0.0,
                (
                    "The AI could not provide "
                    "a usable confidence score."
                ),
            )

        return result(
            decision,
            confidence,
            reason,
        )

    # ========================================================
    # TIMEOUT
    # ========================================================

    except requests.exceptions.Timeout:

        return result(
            "HUMAN_REVIEW",
            0.0,
            "Ollama request timed out.",
        )

    # ========================================================
    # CONNECTION
    # ========================================================

    except requests.exceptions.ConnectionError:

        return result(
            "HUMAN_REVIEW",
            0.0,
            "Ollama server is unavailable.",
        )

    # ========================================================
    # REQUEST ERROR
    # ========================================================

    except requests.exceptions.RequestException as e:

        return result(
            "HUMAN_REVIEW",
            0.0,
            f"Ollama request failed: {e}",
        )

    # ========================================================
    # INVALID JSON
    # ========================================================

    except json.JSONDecodeError:

        return result(
            "HUMAN_REVIEW",
            0.0,
            "Ollama returned invalid JSON.",
        )

    # ========================================================
    # UNEXPECTED ERROR
    # ========================================================

    except Exception as e:

        return result(
            "HUMAN_REVIEW",
            0.0,
            f"Unexpected investigator error: {e}",
        )


if __name__ == "__main__":

    print("=" * 60)
    print("AI FINANCE CONTROLLER")
    print("Hybrid Ollama Investigator")
    print("=" * 60)

    print(
        f"Model: {MODEL}"
    )

    print(
        f"Timeout: {OLLAMA_TIMEOUT}s"
    )

    print(
        "\nInvestigator ready."
    )