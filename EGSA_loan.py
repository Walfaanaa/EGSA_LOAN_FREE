import streamlit as st
import pandas as pd
from datetime import date
from dateutil.relativedelta import relativedelta
import math
import os


# ============================================================
# CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="AWO Loan Management App",
    page_icon="💰",
    layout="wide"
)

st.title("AWO Interest-Free Loan Management App")

DATA_FILE = "awo_loans.csv"

LOAN_TERM_MONTHS = 10
MONTHLY_PENALTY_RATE = 0.10


# ============================================================
# DATA COLUMNS
# ============================================================

COLUMNS = [
    "loan_id",
    "full_name",
    "phone_number",
    "loan_amount",
    "disbursed_date",
    "due_date",
    "returned",
    "return_date",
    "months_late",
    "penalty_amount",
    "total_due"
]


# ============================================================
# LOAD OR CREATE DATA
# ============================================================

if os.path.exists(DATA_FILE):

    df = pd.read_csv(
        DATA_FILE,
        keep_default_na=False
    )

else:

    df = pd.DataFrame(columns=COLUMNS)


# ============================================================
# PREPARE DATA
# ============================================================

for col in COLUMNS:

    if col not in df.columns:

        if col == "returned":
            df[col] = False

        elif col in [
            "loan_amount",
            "months_late",
            "penalty_amount",
            "total_due"
        ]:
            df[col] = 0.0

        else:
            df[col] = ""


# Date columns
for col in [
    "disbursed_date",
    "due_date",
    "return_date"
]:

    df[col] = pd.to_datetime(
        df[col],
        errors="coerce"
    )


# Numeric columns
for col in [
    "loan_amount",
    "months_late",
    "penalty_amount",
    "total_due"
]:

    df[col] = pd.to_numeric(
        df[col],
        errors="coerce"
    ).fillna(0)


# Returned column
if df["returned"].dtype == object:

    df["returned"] = (
        df["returned"]
        .astype(str)
        .str.lower()
        .isin([
            "true",
            "1",
            "yes",
            "returned"
        ])
    )

df["returned"] = (
    df["returned"]
    .fillna(False)
    .astype(bool)
)


# ============================================================
# GENERATE MISSING LOAN IDs
# ============================================================

if "loan_id" not in df.columns:

    df["loan_id"] = ""

df["loan_id"] = (
    df["loan_id"]
    .fillna("")
    .astype(str)
)

existing_ids = set(
    df["loan_id"]
)

next_id = 1001

for index in df.index:

    if (
        df.loc[index, "loan_id"] == ""
        or df.loc[index, "loan_id"] == "nan"
    ):

        while str(next_id) in existing_ids:
            next_id += 1

        df.loc[index, "loan_id"] = str(next_id)

        existing_ids.add(
            str(next_id)
        )

        next_id += 1


# ============================================================
# FUNCTIONS
# ============================================================

def calculate_penalty(
    amount,
    due_date,
    pay_date
):

    amount = float(amount)

    due = pd.to_datetime(
        due_date
    )

    pay = pd.to_datetime(
        pay_date
    )

    if pd.isna(due):

        return 0, 0.0, amount

    if pay <= due:

        return 0, 0.0, amount

    days_late = (
        pay - due
    ).days

    months_late = math.ceil(
        days_late / 30
    )

    total_due = amount
    penalty = 0.0

    for _ in range(months_late):

        month_penalty = (
            total_due *
            MONTHLY_PENALTY_RATE
        )

        penalty += month_penalty

        total_due += month_penalty

    return (
        months_late,
        penalty,
        total_due
    )


def has_active_loan(
    phone,
    data
):

    if data.empty:
        return False

    phone = str(phone).strip()

    active = data[
        data["returned"] == False
    ]

    return phone in (
        active["phone_number"]
        .astype(str)
        .str.strip()
        .values
    )


def save_data(data):

    data.to_csv(
        DATA_FILE,
        index=False
    )


# ============================================================
# UPDATE PENALTIES
# ============================================================

today = pd.Timestamp(
    date.today()
)

for index, row in df.iterrows():

    if not row["returned"]:

        months_late, penalty, total_due = (
            calculate_penalty(
                row["loan_amount"],
                row["due_date"],
                today
            )
        )

        df.loc[
            index,
            "months_late"
        ] = months_late

        df.loc[
            index,
            "penalty_amount"
        ] = penalty

        df.loc[
            index,
            "total_due"
        ] = total_due


save_data(df)


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.header(
    "➕ Add New Loan"
)


# ============================================================
# ADD NEW LOAN
# ============================================================

full_name = st.sidebar.text_input(
    "Borrower Full Name"
)

phone_number = st.sidebar.text_input(
    "Phone Number"
)

loan_amount = st.sidebar.number_input(
    "Loan Amount",
    min_value=0.0,
    step=100.0
)

disbursed_date = st.sidebar.date_input(
    "Disbursed Date",
    date.today()
)


if st.sidebar.button(
    "Save Loan"
):

    full_name = full_name.strip()

    phone_number = phone_number.strip()

    if not full_name:

        st.sidebar.error(
            "Please enter borrower name."
        )

    elif not phone_number:

        st.sidebar.error(
            "Please enter phone number."
        )

    elif loan_amount <= 0:

        st.sidebar.error(
            "Loan amount must be greater than zero."
        )

    elif has_active_loan(
        phone_number,
        df
    ):

        st.sidebar.error(
            "This phone number already has an active loan."
        )

    else:

        # Generate ID
        existing_ids = set(
            df["loan_id"]
            .astype(str)
        )

        new_id = 1001

        while str(new_id) in existing_ids:

            new_id += 1

        # Due date
        due_date = (
            disbursed_date
            + relativedelta(
                months=LOAN_TERM_MONTHS
            )
        )

        new_row = {

            "loan_id": str(new_id),

            "full_name": full_name,

            "phone_number": phone_number,

            "loan_amount": loan_amount,

            "disbursed_date": pd.Timestamp(
                disbursed_date
            ),

            "due_date": pd.Timestamp(
                due_date
            ),

            "returned": False,

            "return_date": pd.NaT,

            "months_late": 0,

            "penalty_amount": 0.0,

            "total_due": loan_amount
        }

        df = pd.concat(
            [
                df,
                pd.DataFrame([new_row])
            ],
            ignore_index=True
        )

        save_data(df)

        st.sidebar.success(
            f"Loan {new_id} saved successfully!"
        )

        st.rerun()


# ============================================================
# UPLOAD LOANS
# ============================================================

st.sidebar.markdown("---")

st.sidebar.header(
    "📤 Upload Loans"
)

uploaded_file = st.sidebar.file_uploader(
    "Upload CSV or Excel",
    type=[
        "csv",
        "xlsx"
    ]
)


if uploaded_file:

    try:

        if uploaded_file.name.lower().endswith(
            ".csv"
        ):

            upload_df = pd.read_csv(
                uploaded_file
            )

        else:

            upload_df = pd.read_excel(
                uploaded_file
            )


        required_cols = {
            "full_name",
            "phone_number",
            "loan_amount",
            "disbursed_date"
        }


        missing_cols = (
            required_cols
            - set(upload_df.columns)
        )


        if missing_cols:

            st.sidebar.error(
                "Missing columns: "
                + ", ".join(
                    missing_cols
                )
            )

        else:

            upload_df[
                "disbursed_date"
            ] = pd.to_datetime(
                upload_df[
                    "disbursed_date"
                ],
                errors="coerce"
            )


            upload_df[
                "loan_amount"
            ] = pd.to_numeric(
                upload_df[
                    "loan_amount"
                ],
                errors="coerce"
            )


            upload_df = upload_df.dropna(
                subset=[
                    "full_name",
                    "phone_number",
                    "loan_amount",
                    "disbursed_date"
                ]
            )


            # Existing IDs
            existing_ids = set(
                df["loan_id"]
                .astype(str)
            )


            # Existing active phones
            existing_phones = set(
                df.loc[
                    df["returned"] == False,
                    "phone_number"
                ]
                .astype(str)
                .str.strip()
            )


            new_rows = []

            next_id = 1001


            for _, row in upload_df.iterrows():

                phone = str(
                    row["phone_number"]
                ).strip()


                # Skip active duplicate
                if phone in existing_phones:
                    continue


                while str(next_id) in existing_ids:

                    next_id += 1


                loan_id = str(
                    next_id
                )


                due_date = (
                    row["disbursed_date"]
                    + pd.DateOffset(
                        months=LOAN_TERM_MONTHS
                    )
                )


                new_rows.append({

                    "loan_id": loan_id,

                    "full_name": str(
                        row["full_name"]
                    ).strip(),

                    "phone_number": phone,

                    "loan_amount": float(
                        row["loan_amount"]
                    ),

                    "disbursed_date":
                        row["disbursed_date"],

                    "due_date":
                        due_date,

                    "returned":
                        False,

                    "return_date":
                        pd.NaT,

                    "months_late":
                        0,

                    "penalty_amount":
                        0.0,

                    "total_due":
                        float(
                            row["loan_amount"]
                        )
                })


                existing_ids.add(
                    loan_id
                )

                existing_phones.add(
                    phone
                )

                next_id += 1


            if new_rows:

                df = pd.concat(
                    [
                        df,
                        pd.DataFrame(
                            new_rows
                        )
                    ],
                    ignore_index=True
                )


                save_data(df)


                st.sidebar.success(
                    f"{len(new_rows)} loans uploaded successfully."
                )


                st.rerun()

            else:

                st.sidebar.warning(
                    "No new loans were added."
                )


    except Exception as e:

        st.sidebar.error(
            f"Upload error: {e}"
        )


# ============================================================
# DASHBOARD
# ============================================================

st.subheader(
    "📊 Loan Summary"
)


active_loans = df[
    df["returned"] == False
]


returned_loans = df[
    df["returned"] == True
]


overdue_loans = active_loans[
    active_loans["due_date"]
    < today
]


col1, col2, col3, col4 = st.columns(4)


col1.metric(
    "Total Loans",
    len(df)
)


col2.metric(
    "In Progress",
    len(active_loans)
)


col3.metric(
    "Returned",
    len(returned_loans)
)


col4.metric(
    "Overdue",
    len(overdue_loans)
)


# ============================================================
# MAIN LOAN TABLE
# ============================================================

st.subheader(
    "📋 All Loans"
)


display_df = df.copy()


# ------------------------------------------------------------
# STATUS
# ------------------------------------------------------------

display_df["Status"] = display_df.apply(

    lambda row:

        "Returned"
        if row["returned"]

        else "In Progress",

    axis=1
)


# ------------------------------------------------------------
# ONLY FIVE COLUMNS
# ------------------------------------------------------------

display_df = display_df[
    [
        "loan_id",
        "disbursed_date",
        "loan_amount",
        "due_date",
        "Status"
    ]
].copy()


# ------------------------------------------------------------
# COLUMN NAMES
# ------------------------------------------------------------

display_df = display_df.rename(

    columns={

        "loan_id":
            "ID",

        "disbursed_date":
            "Disbursed Date",

        "loan_amount":
            "Loan Amount",

        "due_date":
            "Due Date"
    }
)


# ------------------------------------------------------------
# FORMAT DATES
# ------------------------------------------------------------

display_df[
    "Disbursed Date"
] = pd.to_datetime(
    display_df[
        "Disbursed Date"
    ]
).dt.strftime(
    "%-m/%-d/%Y"
)


display_df[
    "Due Date"
] = pd.to_datetime(
    display_df[
        "Due Date"
    ]
).dt.strftime(
    "%-m/%-d/%Y"
)


# ------------------------------------------------------------
# FORMAT AMOUNT
# ------------------------------------------------------------

display_df[
    "Loan Amount"
] = display_df[
    "Loan Amount"
].map(
    lambda x: f"{x:,.0f}"
)


# ------------------------------------------------------------
# DISPLAY
# ------------------------------------------------------------

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True
)


# ============================================================
# MARK LOAN AS RETURNED
# ============================================================

st.subheader(
    "✅ Mark Loan as Returned"
)


if active_loans.empty:

    st.info(
        "No active loans."
    )

else:

    selected_index = st.selectbox(

        "Select Loan",

        active_loans.index,

        format_func=lambda i:
            (
                f"{df.loc[i, 'loan_id']} | "
                f"{df.loc[i, 'full_name']} | "
                f"{df.loc[i, 'loan_amount']:,.0f}"
            )
    )


    return_date = st.date_input(
        "Return Date",
        date.today()
    )


    if st.button(
        "Confirm Return"
    ):

        selected_row = df.loc[
            selected_index
        ]


        if (
            pd.Timestamp(return_date)
            <
            selected_row[
                "disbursed_date"
            ]
        ):

            st.error(
                "Return date cannot be before "
                "the disbursed date."
            )

        else:

            months_late, penalty, total_due = (
                calculate_penalty(

                    selected_row[
                        "loan_amount"
                    ],

                    selected_row[
                        "due_date"
                    ],

                    return_date
                )
            )


            df.loc[
                selected_index,
                "returned"
            ] = True


            df.loc[
                selected_index,
                "return_date"
            ] = pd.Timestamp(
                return_date
            )


            df.loc[
                selected_index,
                "months_late"
            ] = months_late


            df.loc[
                selected_index,
                "penalty_amount"
            ] = penalty


            df.loc[
                selected_index,
                "total_due"
            ] = total_due


            save_data(df)


            st.success(
                f"""
                Loan {selected_row['loan_id']} returned successfully.

                Months late: {months_late}

                Penalty: {penalty:,.2f}

                Total Due: {total_due:,.2f}
                """
            )


            st.rerun()


# ============================================================
# OVERDUE LOANS
# ============================================================

st.subheader(
    "⚠️ Overdue Loans"
)


overdue_display = df[
    (df["returned"] == False)
    &
    (df["due_date"] < today)
].copy()


if overdue_display.empty:

    st.success(
        "No overdue loans."
    )

else:

    overdue_display[
        "Status"
    ] = "Overdue"


    overdue_display = overdue_display[
        [
            "loan_id",
            "disbursed_date",
            "loan_amount",
            "due_date",
            "Status"
        ]
    ]


    overdue_display = overdue_display.rename(

        columns={

            "loan_id":
                "ID",

            "disbursed_date":
                "Disbursed Date",

            "loan_amount":
                "Loan Amount",

            "due_date":
                "Due Date"
        }
    )


    overdue_display[
        "Disbursed Date"
    ] = pd.to_datetime(
        overdue_display[
            "Disbursed Date"
        ]
    ).dt.strftime(
        "%-m/%-d/%Y"
    )


    overdue_display[
        "Due Date"
    ] = pd.to_datetime(
        overdue_display[
            "Due Date"
        ]
    ).dt.strftime(
        "%-m/%-d/%Y"
    )


    overdue_display[
        "Loan Amount"
    ] = overdue_display[
        "Loan Amount"
    ].map(
        lambda x: f"{x:,.0f}"
    )


    st.dataframe(
        overdue_display,
        use_container_width=True,
        hide_index=True
    )
