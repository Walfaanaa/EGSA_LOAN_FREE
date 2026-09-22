import streamlit as st
import pandas as pd
from datetime import date
from dateutil.relativedelta import relativedelta
import os


# ============================================================
# CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="EGSA2025 Loan Management App",
    page_icon="💰",
    layout="wide"
)

st.title("EGSA2025 Interest-Free Loan Management App")

DATA_FILE = "loan_free.xlsx"

# Change to 12 if the loan period should be one year
LOAN_TERM_MONTHS = 12


# ============================================================
# COLUMNS
# ============================================================

COLUMNS = [
    "Id",
    "Disbursed_date",
    "loan_amount",
    "Due_date",
    "Status"
]


# ============================================================
# LOAD EXCEL FILE
# ============================================================

def load_data():

    if os.path.exists(DATA_FILE):

        try:

            df = pd.read_excel(
                DATA_FILE,
                engine="openpyxl"
            )

        except Exception as e:

            st.error(
                f"Could not read {DATA_FILE}: {e}"
            )

            st.stop()

    else:

        df = pd.DataFrame(
            columns=COLUMNS
        )

    return df


df = load_data()


# ============================================================
# CLEAN COLUMN NAMES
# ============================================================

df.columns = (
    df.columns
    .astype(str)
    .str.strip()
)


# ============================================================
# CHECK REQUIRED COLUMNS
# ============================================================

missing_columns = [
    col
    for col in COLUMNS
    if col not in df.columns
]


if missing_columns:

    st.error(
        "The Excel file is missing these columns: "
        + ", ".join(missing_columns)
    )

    st.stop()


# ============================================================
# KEEP ONLY FIVE COLUMNS
# ============================================================

df = df[
    COLUMNS
].copy()


# ============================================================
# CLEAN DATA
# ============================================================

df["Id"] = (
    df["Id"]
    .astype(str)
    .str.replace(
        ".0",
        "",
        regex=False
    )
    .str.strip()
)


df["Disbursed_date"] = pd.to_datetime(
    df["Disbursed_date"],
    errors="coerce"
)


df["Due_date"] = pd.to_datetime(
    df["Due_date"],
    errors="coerce"
)


df["loan_amount"] = pd.to_numeric(
    df["loan_amount"],
    errors="coerce"
).fillna(0)


df["Status"] = (
    df["Status"]
    .fillna("In Progress")
    .astype(str)
    .str.strip()
)


# ============================================================
# DATE FORMAT
# ============================================================

def format_date(value):

    if pd.isna(value):

        return ""

    value = pd.to_datetime(
        value,
        errors="coerce"
    )

    if pd.isna(value):

        return ""

    return (
        f"{value.month}/"
        f"{value.day}/"
        f"{value.year}"
    )


# ============================================================
# SAVE DATA
# ============================================================

def save_data(data):

    try:

        data.to_excel(
            DATA_FILE,
            index=False,
            engine="openpyxl"
        )

        return True

    except Exception as e:

        st.error(
            f"Could not save Excel file: {e}"
        )

        return False


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.header(
    "➕ Add New Loan"
)


# ============================================================
# ADD NEW LOAN
# ============================================================

loan_amount = st.sidebar.number_input(
    "Loan Amount",
    min_value=0.0,
    step=100.0,
    format="%.0f"
)


disbursed_date = st.sidebar.date_input(
    "Disbursed Date",
    value=date.today()
)


if st.sidebar.button(
    "Save Loan",
    type="primary"
):

    if loan_amount <= 0:

        st.sidebar.error(
            "Loan amount must be greater than zero."
        )

    else:

        # -----------------------------------------------
        # Generate new ID
        # -----------------------------------------------

        numeric_ids = pd.to_numeric(
            df["Id"],
            errors="coerce"
        )


        if numeric_ids.notna().any():

            new_id = int(
                numeric_ids.max()
            ) + 1

        else:

            new_id = 1001


        # -----------------------------------------------
        # Calculate due date
        # -----------------------------------------------

        due_date = (
            disbursed_date
            +
            relativedelta(
                months=LOAN_TERM_MONTHS
            )
        )


        # -----------------------------------------------
        # Create new loan
        # -----------------------------------------------

        new_row = {

            "Id":
                str(new_id),

            "Disbursed_date":
                pd.Timestamp(
                    disbursed_date
                ),

            "loan_amount":
                float(
                    loan_amount
                ),

            "Due_date":
                pd.Timestamp(
                    due_date
                ),

            "Status":
                "In Progress"
        }


        df = pd.concat(
            [
                df,
                pd.DataFrame(
                    [new_row]
                )
            ],
            ignore_index=True
        )


        if save_data(df):

            st.sidebar.success(
                f"Loan {new_id} saved successfully!"
            )

            st.rerun()


# ============================================================
# DASHBOARD
# ============================================================

st.subheader(
    "📊 Loan Summary"
)


# Count statuses
in_progress = df[
    df["Status"]
    .str.lower()
    .eq("in progress")
]


returned = df[
    df["Status"]
    .str.lower()
    .eq("returned")
]


# Current date
today = pd.Timestamp(
    date.today()
)


# Overdue
overdue = df[
    (
        df["Status"]
        .str.lower()
        .eq("in progress")
    )
    &
    (
        df["Due_date"]
        < today
    )
]


# ============================================================
# METRICS
# ============================================================

col1, col2, col3, col4 = st.columns(4)


col1.metric(
    "Total Loans",
    f"{len(df):,}"
)


col2.metric(
    "In Progress",
    f"{len(in_progress):,}"
)


col3.metric(
    "Returned",
    f"{len(returned):,}"
)


col4.metric(
    "Overdue",
    f"{len(overdue):,}"
)


# ============================================================
# ALL LOANS
# ============================================================

st.subheader(
    "📋 All Loans"
)


display_df = df.copy()


# Format dates
display_df[
    "Disbursed_date"
] = display_df[
    "Disbursed_date"
].apply(
    format_date
)


display_df[
    "Due_date"
] = display_df[
    "Due_date"
].apply(
    format_date
)


# Format amount
display_df[
    "loan_amount"
] = display_df[
    "loan_amount"
].apply(
    lambda x:
        f"{float(x):,.0f}"
)


# Rename columns
display_df = display_df.rename(

    columns={

        "Id":
            "ID",

        "Disbursed_date":
            "Disbursed Date",

        "loan_amount":
            "Loan Amount",

        "Due_date":
            "Due Date"
    }
)


# ============================================================
# DISPLAY
# ============================================================

st.dataframe(
    display_df[
        [
            "ID",
            "Disbursed Date",
            "Loan Amount",
            "Due Date",
            "Status"
        ]
    ],
    use_container_width=True,
    hide_index=True
)


# ============================================================
# MARK LOAN AS RETURNED
# ============================================================

st.subheader(
    "✅ Mark Loan as Returned"
)


if in_progress.empty:

    st.info(
        "There are no loans in progress."
    )

else:

    # Select ID
    selected_id = st.selectbox(
        "Select Loan ID",
        in_progress["Id"].tolist()
    )


    if st.button(
        "Mark as Returned",
        type="primary"
    ):

        df.loc[
            df["Id"] == selected_id,
            "Status"
        ] = "Returned"


        if save_data(df):

            st.success(
                f"Loan {selected_id} marked as Returned."
            )

            st.rerun()


# ============================================================
# OVERDUE LOANS
# ============================================================

st.subheader(
    "⚠️ Overdue Loans"
)


overdue_display = df[
    (
        df["Status"]
        .str.lower()
        .eq("in progress")
    )
    &
    (
        df["Due_date"]
        < today
    )
].copy()


if overdue_display.empty:

    st.success(
        "No overdue loans."
    )

else:

    overdue_display[
        "Disbursed_date"
    ] = overdue_display[
        "Disbursed_date"
    ].apply(
        format_date
    )


    overdue_display[
        "Due_date"
    ] = overdue_display[
        "Due_date"
    ].apply(
        format_date
    )


    overdue_display[
        "loan_amount"
    ] = overdue_display[
        "loan_amount"
    ].apply(
        lambda x:
            f"{float(x):,.0f}"
    )


    overdue_display = overdue_display.rename(

        columns={

            "Id":
                "ID",

            "Disbursed_date":
                "Disbursed Date",

            "loan_amount":
                "Loan Amount",

            "Due_date":
                "Due Date"
        }
    )


    st.dataframe(
        overdue_display[
            [
                "ID",
                "Disbursed Date",
                "Loan Amount",
                "Due Date",
                "Status"
            ]
        ],
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# SAVE
# ============================================================

save_data(df)
