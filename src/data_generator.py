import os
import random
import re
from datetime import datetime, timedelta

import pandas as pd
from faker import Faker


fake = Faker()

DEFAULT_RECORDS = 500
DEFAULT_SEED = 42

ERROR_TYPES = [
    "MATCHED",
    "AMOUNT_MISMATCH",
    "MISSING_PAYMENT",
    "DUPLICATE",
    "TIMING_DIFFERENCE",
    "SPLIT_PAYMENT",
]

ERROR_WEIGHTS = [
    55,
    10,
    8,
    7,
    10,
    10,
]


def clean_company_name(name):
    """
    Create a shortened/messy bank-style company name.
    """

    name = str(name).upper()

    replacements = {
        "PRIVATE LIMITED": "PVT LTD",
        "PRIVATE": "PVT",
        "LIMITED": "LTD",
        "CORPORATION": "CORP",
        "COMPANY": "CO",
        "INCORPORATED": "INC",
    }

    for old, new in replacements.items():
        name = name.replace(old, new)

    # Remove punctuation
    name = re.sub(r"[^A-Z0-9\s]", " ", name)

    # Normalize spaces
    name = " ".join(name.split())

    words = name.split()

    # Sometimes shorten the company name
    if len(words) > 2 and random.random() < 0.5:
        words = words[:2]

    return " ".join(words)


def create_bank_description(customer):
    """
    Generate realistic bank statement descriptions.
    """

    clean_name = clean_company_name(customer)

    formats = [
        clean_name,
        f"PAYMENT {clean_name}",
        f"{clean_name} PAYMENT",
        f"NEFT-{clean_name}",
        f"IMPS {clean_name}",
        f"UPI-{clean_name}",
    ]

    return random.choice(formats)


def generate_dataset(
    num_records=DEFAULT_RECORDS,
    seed=DEFAULT_SEED
):
    random.seed(seed)
    Faker.seed(seed)

    invoices = []
    bank_transactions = []
    ground_truth = []

    base_date = datetime.today().replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0
    )

    for i in range(1, num_records + 1):

        invoice_id = f"INV-{i:05d}"

        customer = fake.company()

        amount = random.randint(
            1000,
            100000
        )

        invoice_date = (
            base_date
            - timedelta(
                days=random.randint(1, 60)
            )
        ).date()

        error_type = random.choices(
            ERROR_TYPES,
            weights=ERROR_WEIGHTS,
            k=1
        )[0]

        # ----------------------------------------------------
        # Invoice
        # ----------------------------------------------------

        invoices.append(
            {
                "invoice_id": invoice_id,
                "customer": customer,
                "amount": amount,
                "invoice_date": invoice_date,
            }
        )

        # ----------------------------------------------------
        # MATCHED
        # ----------------------------------------------------

        if error_type == "MATCHED":

            bank_transactions.append(
                {
                    "transaction_id": f"TXN-{i:05d}",
                    "description":
                        create_bank_description(customer),
                    "amount": amount,
                    "transaction_date": invoice_date,
                }
            )

        # ----------------------------------------------------
        # AMOUNT MISMATCH
        # ----------------------------------------------------

        elif error_type == "AMOUNT_MISMATCH":

            difference = random.choice(
                [
                    100,
                    250,
                    500,
                    1000,
                    2500
                ]
            )

            payment_amount = max(
                100,
                amount - difference
            )

            bank_transactions.append(
                {
                    "transaction_id": f"TXN-{i:05d}",
                    "description":
                        create_bank_description(customer),
                    "amount": payment_amount,
                    "transaction_date": invoice_date,
                }
            )

        # ----------------------------------------------------
        # MISSING PAYMENT
        # ----------------------------------------------------

        elif error_type == "MISSING_PAYMENT":

            pass

        # ----------------------------------------------------
        # DUPLICATE
        # ----------------------------------------------------

        elif error_type == "DUPLICATE":

            description = create_bank_description(
                customer
            )

            transaction = {
                "transaction_id": f"TXN-{i:05d}",
                "description": description,
                "amount": amount,
                "transaction_date": invoice_date,
            }

            bank_transactions.append(
                transaction.copy()
            )

            duplicate = transaction.copy()

            duplicate["transaction_id"] = (
                f"TXN-DUP-{i:05d}"
            )

            bank_transactions.append(
                duplicate
            )

        # ----------------------------------------------------
        # TIMING DIFFERENCE
        # ----------------------------------------------------

        elif error_type == "TIMING_DIFFERENCE":

            payment_delay = random.randint(
                3,
                7
            )

            payment_date = (
                invoice_date
                + timedelta(
                    days=payment_delay
                )
            )

            bank_transactions.append(
                {
                    "transaction_id": f"TXN-{i:05d}",
                    "description":
                        create_bank_description(customer),
                    "amount": amount,
                    "transaction_date": payment_date,
                }
            )

        # ----------------------------------------------------
        # SPLIT PAYMENT
        # ----------------------------------------------------

        elif error_type == "SPLIT_PAYMENT":

            first_payment = round(
                amount * 0.60,
                2
            )

            second_payment = round(
                amount - first_payment,
                2
            )

            description = create_bank_description(
                customer
            )

            bank_transactions.append(
                {
                    "transaction_id":
                        f"TXN-{i:05d}-A",

                    "description":
                        description,

                    "amount":
                        first_payment,

                    "transaction_date":
                        invoice_date,
                }
            )

            bank_transactions.append(
                {
                    "transaction_id":
                        f"TXN-{i:05d}-B",

                    "description":
                        description,

                    "amount":
                        second_payment,

                    "transaction_date":
                        invoice_date,
                }
            )

        # ----------------------------------------------------
        # Ground Truth
        # ----------------------------------------------------

        ground_truth.append(
            {
                "invoice_id": invoice_id,
                "customer": customer,
                "expected_status": error_type,
            }
        )

    invoices_df = pd.DataFrame(
        invoices
    )

    bank_transactions_df = pd.DataFrame(
        bank_transactions
    )

    ground_truth_df = pd.DataFrame(
        ground_truth
    )

    return (
        invoices_df,
        bank_transactions_df,
        ground_truth_df
    )


def save_dataset(
    num_records=DEFAULT_RECORDS,
    seed=DEFAULT_SEED
):

    output_directory = "data/generated"

    os.makedirs(
        output_directory,
        exist_ok=True
    )

    (
        invoices,
        bank_transactions,
        ground_truth
    ) = generate_dataset(
        num_records=num_records,
        seed=seed
    )

    invoices.to_csv(
        f"{output_directory}/invoices.csv",
        index=False
    )

    bank_transactions.to_csv(
        f"{output_directory}/bank_transactions.csv",
        index=False
    )

    ground_truth.to_csv(
        f"{output_directory}/ground_truth.csv",
        index=False
    )

    print("\n" + "=" * 60)
    print("AI FINANCE CONTROLLER")
    print("Phase 2 - Realistic Dataset")
    print("=" * 60)

    print(
        f"\nInvoices generated: "
        f"{len(invoices)}"
    )

    print(
        f"Bank transactions generated: "
        f"{len(bank_transactions)}"
    )

    print(
        f"Ground-truth records: "
        f"{len(ground_truth)}"
    )

    print("\nGround Truth Distribution:")

    print(
        ground_truth[
            "expected_status"
        ].value_counts()
    )

    print("\nBank sample:")

    print(
        bank_transactions.head(10).to_string(
            index=False
        )
    )

    print("\nFiles created:")

    print(
        f"  {output_directory}/invoices.csv"
    )

    print(
        f"  {output_directory}/bank_transactions.csv"
    )

    print(
        f"  {output_directory}/ground_truth.csv"
    )

    print("\nDataset generation complete!")


if __name__ == "__main__":

    save_dataset(
        num_records=500,
        seed=42
    )