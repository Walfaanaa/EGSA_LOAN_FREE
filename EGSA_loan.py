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
    page_title="EGSA2025 Loan Management App",
    page_icon="💰",
    layout="wide"
)

st.title("EGSA2025 Interest-Free Loan Management App")

DATA_FILE = "loan_free.xlsx"

# Loan period
LOAN_TERM_MONTHS = 10

# Monthly compounded penalty
MONTHLY_PENALTY_RATE = 0.10


# ============================================================
# DATA COLUMNS
# ============================================================

COLUMNS = [
    "Id",
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
# LOAD DATA
# ============================================================

def load_data():

    # --------------------------------------------------------
    # File does not exist
    # --------------------------------------------------------

    if not os.path.exists(DATA_FILE):

        return pd.DataFrame(
            columns=COLUMNS
        )

    # --------------------------------------------------------
    # Read Excel file
    # --------------------------------------------------------

    try:

        data = pd.read_excel(
            DATA_FILE,
            engine="openpyxl"
        )

        return data

    except Exception as e:

        st.error(
            f"Unable to read {DATA_FILE}."
        )

        st.error(
            f"Error: {e}"
        )

        st.stop()


df = load_data()


# ============================================================
# PREPARE REQUIRED COLUMNS
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


# ============================================================
# KEEP ONLY EXPECTED INTERNAL COLUMNS
# ============================================================

df = df[
    COLUMNS
].copy()


# ============================================================
# CLEAN ID
# ============================================================

df["Id"] = (
    df["Id"]
    .fillna("")
    .astype(str)
    .str.strip()
)

# Remove Excel-style decimal IDs such as 1001.0
df["Id"] = df["Id"].apply(

    lambda x:
        str(int(float(x)))
        if x not in ["", "nan", "None"]
        and str(x).replace(".", "", 1).isdigit()
        and float(x).is_integer()
        else x
)


# ============================================================
# CLEAN NAME
# ============================================================

df["full_name"] = (
    df["full_name"]
    .fillna("")
    .astype(str)
    .str.strip()
)


# ============================================================
# CLEAN PHONE
# ============================================================

df["phone_number"] = (
    df["phone_number"]
    .fillna("")
    .astype(str)
    .str.strip()
)


# ============================================================
# DATE COLUMNS
# ============================================================

for col in [
    "disbursed_date",
    "due_date",
    "return_date"
]:

    df[col] = pd.to_datetime(
        df[col],
        errors="coerce"
    )


# ============================================================
# NUMERIC COLUMNS
# ============================================================

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


# ============================================================
# RETURNED COLUMN
# ============================================================

if df["returned"].dtype == object:

    df["returned"] = (
        df["returned"]
        .astype(str)
        .str.strip()
        .str.lower()
        .isin(
            [
                "true",
                "1",
                "yes",
                "y",
                "returned"
            ]
        )
    )

else:

    df["returned"] = (
        df["returned"]
        .fillna(False)
        .astype(bool)
    )


# ============================================================
# GENERATE MISSING IDs
# ============================================================

existing_ids = set(
    df["Id"]
    .astype(str)
    .str.strip()
)

next_id = 1001

for index in df.index:

    current_id = str(
        df.loc[index, "Id"]
    ).strip()

    if (
        current_id == ""
        or current_id.lower() in [
            "nan",
            "none"
        ]
    ):

        while str(next_id) in existing_ids:

            next_id += 1

        df.loc[
            index,
            "Id"
        ] = str(next_id)

        existing_ids.add(
            str(next_id)
        )

        next_id += 1


# ============================================================
# PENALTY CALCULATION
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

    # No valid due date
    if pd.isna(due):

        return (
            0,
            0.0,
            amount
        )

    # Paid on or before due date
    if pay <= due:

        return (
            0,
            0.0,
            amount
        )

    # Calculate late days
    days_late = (
        pay - due
    ).days

    # Every 30 days = one month
    months_late = math.ceil(
        days_late / 30
    )

    total_due = amount
    penalty = 0.0

    # Compound 10% every month
    for _ in range(
        months_late
    ):

        monthly_penalty = (
            total_due
            *
            MONTHLY_PENALTY_RATE
        )

        penalty += (
            monthly_penalty
        )

        total_due += (
            monthly_penalty
        )

    return (
        months_late,
        penalty,
        total_due
    )


# ============================================================
# SAVE DATA
# ============================================================

def save_data(data):

    try:

        # Ensure correct column order
        data = data[
            COLUMNS
        ].copy()

        data.to_excel(
            DATA_FILE,
            index=False,
            engine="openpyxl"
        )

        return True

    except Exception as e:

        st.error(
            f"Unable to save data: {e}"
        )

        return False


# ============================================================
# CURRENT DATE
# ============================================================

today = pd.Timestamp(
    date.today()
)


# ============================================================
# UPDATE ACTIVE LOAN PENALTIES
# ============================================================

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
    step=100.0,
    format="%.0f"
)

disbursed_date = st.sidebar.date_input(
    "Disbursed Date",
    value=date.today()
)


# ============================================================
# SAVE NEW LOAN
# ============================================================

if st.sidebar.button(
    "Save Loan",
    type="primary"
):

    full_name = (
        full_name
        .strip()
    )

    phone_number = (
        phone_number
        .strip()
    )

    # --------------------------------------------------------
    # Validation
    # --------------------------------------------------------

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

    else:

        # ----------------------------------------------------
        # Check active loan
        # ----------------------------------------------------

        active_phones = set(
            df.loc[
                df["returned"] == False,
                "phone_number"
            ]
            .astype(str)
            .str.strip()
        )

        if phone_number in active_phones:

            st.sidebar.error(
                "This phone number already has an active loan."
            )

        else:

            # ------------------------------------------------
            # Generate next ID
            # ------------------------------------------------

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


            # ------------------------------------------------
            # Calculate due date
            # ------------------------------------------------

            due_date = (
                disbursed_date
                +
                relativedelta(
                    months=LOAN_TERM_MONTHS
                )
            )


            # ------------------------------------------------
            # New row
            # ------------------------------------------------

            new_row = {

                "Id":
                    str(new_id),

                "full_name":
                    full_name,

                "phone_number":
                    phone_number,

                "loan_amount":
                    float(loan_amount),

                "disbursed_date":
                    pd.Timestamp(
                        disbursed_date
                    ),

                "due_date":
                    pd.Timestamp(
                        due_date
                    ),

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
                        loan_amount
                    )
            }


            # ------------------------------------------------
            # Add row
            # ------------------------------------------------

            df = pd.concat(
                [
                    df,
                    pd.DataFrame(
                        [new_row]
                    )
                ],
                ignore_index=True
            )


            # ------------------------------------------------
            # Save
            # ------------------------------------------------

            if save_data(df):

                st.sidebar.success(
                    f"Loan {new_id} saved successfully!"
                )

                st.rerun()


# ============================================================
# UPLOAD LOANS
# ============================================================

st.sidebar.markdown(
    "---"
)

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


if uploaded_file is not None:

    try:

        # ----------------------------------------------------
        # Read uploaded file
        # ----------------------------------------------------

        if uploaded_file.name.lower().endswith(
            ".csv"
        ):

            # Try several common encodings
            upload_df = None

            for encoding in [
                "utf-8",
                "utf-8-sig",
                "cp1252",
                "latin1"
            ]:

                try:

                    upload_file = uploaded_file

                    upload_file.seek(0)

                    upload_df = pd.read_csv(
                        upload_file,
                        encoding=encoding
                    )

                    break

                except UnicodeDecodeError:

                    continue


            if upload_df is None:

                st.sidebar.error(
                    "Unable to read CSV encoding."
                )

                st.stop()

        else:

            upload_df = pd.read_excel(
                uploaded_file,
                engine="openpyxl"
            )


        # ----------------------------------------------------
        # Normalize column names
        # ----------------------------------------------------

        upload_df.columns = (
            upload_df.columns
            .astype(str)
            .str.strip()
        )


        # ----------------------------------------------------
        # Required columns
        # ----------------------------------------------------

        required_cols = {
            "full_name",
            "phone_number",
            "loan_amount",
            "disbursed_date"
        }


        missing_cols = (
            required_cols
            -
            set(upload_df.columns)
        )


        if missing_cols:

            st.sidebar.error(
                "Missing columns: "
                +
                ", ".join(
                    sorted(
                        missing_cols
                    )
                )
            )

        else:

            # ------------------------------------------------
            # Convert dates
            # ------------------------------------------------

            upload_df[
                "disbursed_date"
            ] = pd.to_datetime(
                upload_df[
                    "disbursed_date"
                ],
                errors="coerce"
            )


            # ------------------------------------------------
            # Convert loan amount
            # ------------------------------------------------

            upload_df[
                "loan_amount"
            ] = pd.to_numeric(
                upload_df[
                    "loan_amount"
                ],
                errors="coerce"
            )


            # ------------------------------------------------
            # Remove invalid rows
            # ------------------------------------------------

            upload_df = upload_df.dropna(
                subset=[
                    "full_name",
                    "phone_number",
                    "loan_amount",
                    "disbursed_date"
                ]
            )


            # ------------------------------------------------
            # Existing IDs
            # ------------------------------------------------

            existing_ids = set(
                df["Id"]
                .astype(str)
                .str.strip()
            )


            # ------------------------------------------------
            # Existing active phones
            # ------------------------------------------------

            existing_phones = set(
                df.loc[
                    df["returned"] == False,
                    "phone_number"
                ]
                .astype(str)
                .str.strip()
            )


            # ------------------------------------------------
            # Determine next ID
            # ------------------------------------------------

            numeric_ids = pd.to_numeric(
                df["Id"],
                errors="coerce"
            )


            if numeric_ids.notna().any():

                next_id = int(
                    numeric_ids.max()
                ) + 1

            else:

                next_id = 1001


            new_rows = []

            skipped_count = 0


            # ------------------------------------------------
            # Process uploaded rows
            # ------------------------------------------------

            for _, row in upload_df.iterrows():

                phone = str(
                    row[
                        "phone_number"
                    ]
                ).strip()


                full_name_upload = str(
                    row[
                        "full_name"
                    ]
                ).strip()


                amount = float(
                    row[
                        "loan_amount"
                    ]
                )


                # --------------------------------------------
                # Skip active duplicate
                # --------------------------------------------

                if phone in existing_phones:

                    skipped_count += 1

                    continue


                # --------------------------------------------
                # Find unused ID
                # --------------------------------------------

                while str(next_id) in existing_ids:

                    next_id += 1


                loan_id = str(
                    next_id
                )


                # --------------------------------------------
                # Due date
                # --------------------------------------------

                uploaded_disbursed_date = pd.to_datetime(
                    row[
                        "disbursed_date"
                    ]
                )


                due_date = (
                    uploaded_disbursed_date
                    +
                    relativedelta(
                        months=LOAN_TERM_MONTHS
                    )
                )


                # --------------------------------------------
                # Create row
                # --------------------------------------------

                new_rows.append({

                    "Id":
                        loan_id,

                    "full_name":
                        full_name_upload,

                    "phone_number":
                        phone,

                    "loan_amount":
                        amount,

                    "disbursed_date":
                        uploaded_disbursed_date,

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
                        amount
                })


                existing_ids.add(
                    loan_id
                )

                existing_phones.add(
                    phone
                )

                next_id += 1


            # ------------------------------------------------
            # Add uploaded loans
            # ------------------------------------------------

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


                if save_data(df):

                    message = (
                        f"{len(new_rows)} "
                        "loan(s) uploaded successfully."
                    )

                    if skipped_count > 0:

                        message += (
                            f" {skipped_count} "
                            "duplicate active loan(s) skipped."
                        )


                    st.sidebar.success(
                        message
                    )


                    st.rerun()


            else:

                if skipped_count > 0:

                    st.sidebar.warning(
                        f"No new loans were added. "
                        f"{skipped_count} active duplicate(s) skipped."
                    )

                else:

                    st.sidebar.warning(
                        "No valid new loans were found."
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


# Active loans
active_loans = df[
    df["returned"] == False
].copy()


# Returned loans
returned_loans = df[
    df["returned"] == True
].copy()


# Overdue
overdue_loans = active_loans[
    active_loans["due_date"] < today
].copy()


# ============================================================
# SUMMARY CARDS
# ============================================================

col1, col2, col3, col4 = st.columns(4)


col1.metric(
    "Total Loans",
    f"{len(df):,}"
)


col2.metric(
    "In Progress",
    f"{len(active_loans):,}"
)


col3.metric(
    "Returned",
    f"{len(returned_loans):,}"
)


col4.metric(
    "Overdue",
    f"{len(overdue_loans):,}"
)


# ============================================================
# DATE FORMAT FUNCTION
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
# MAIN LOAN TABLE
# ============================================================

st.subheader(
    "📋 All Loans"
)


display_df = df.copy()


# ------------------------------------------------------------
# Status
# ------------------------------------------------------------

display_df["Status"] = display_df.apply(

    lambda row:
        "Returned"
        if row["returned"]
        else "In Progress",

    axis=1
)


# ------------------------------------------------------------
# Only five columns
# ------------------------------------------------------------

display_df = display_df[
    [
        "Id",
        "disbursed_date",
        "loan_amount",
        "due_date",
        "Status"
    ]
].copy()


# ------------------------------------------------------------
# Rename
# ------------------------------------------------------------

display_df = display_df.rename(

    columns={

        "Id":
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
# Format dates
# ------------------------------------------------------------

display_df[
    "Disbursed Date"
] = display_df[
    "Disbursed Date"
].apply(
    format_date
)


display_df[
    "Due Date"
] = display_df[
    "Due Date"
].apply(
    format_date
)


# ------------------------------------------------------------
# Format amount
# ------------------------------------------------------------

display_df[
    "Loan Amount"
] = display_df[
    "Loan Amount"
].apply(
    lambda x:
        f"{float(x):,.0f}"
)


# ------------------------------------------------------------
# Display
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
        "No loans are currently in progress."
    )

else:

    # --------------------------------------------------------
    # Loan selection
    # --------------------------------------------------------

    loan_options = (
        active_loans.index
        .tolist()
    )


    selected_index = st.selectbox(

        "Select Loan",

        loan_options,

        format_func=lambda index:

            (
                f"ID {df.loc[index, 'Id']} | "
                f"{df.loc[index, 'full_name']} | "
                f"{df.loc[index, 'loan_amount']:,.0f}"
            )
    )


    # --------------------------------------------------------
    # Return date
    # --------------------------------------------------------

    return_date = st.date_input(
        "Return Date",
        value=date.today()
    )


    # --------------------------------------------------------
    # Confirm return
    # --------------------------------------------------------

    if st.button(
        "Confirm Return",
        type="primary"
    ):

        selected_row = df.loc[
            selected_index
        ]


        # ----------------------------------------------------
        # Validate return date
        # ----------------------------------------------------

        if (
            pd.Timestamp(
                return_date
            )
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

            # ------------------------------------------------
            # Calculate penalty
            # ------------------------------------------------

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


            # ------------------------------------------------
            # Update loan
            # ------------------------------------------------

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


            # ------------------------------------------------
            # Save
            # ------------------------------------------------

            if save_data(df):

                st.success(
                    f"Loan {selected_row['Id']} "
                    "returned successfully."
                )

                st.info(
                    f"Months late: {months_late}"
                )

                st.info(
                    f"Penalty: {penalty:,.2f}"
                )

                st.info(
                    f"Total Due: {total_due:,.2f}"
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

    # --------------------------------------------------------
    # Status
    # --------------------------------------------------------

    overdue_display[
        "Status"
    ] = "Overdue"


    # --------------------------------------------------------
    # Five columns
    # --------------------------------------------------------

    overdue_display = overdue_display[
        [
            "Id",
            "disbursed_date",
            "loan_amount",
            "due_date",
            "Status"
        ]
    ].copy()


    # --------------------------------------------------------
    # Rename
    # --------------------------------------------------------

    overdue_display = overdue_display.rename(

        columns={

            "Id":
                "ID",

            "disbursed_date":
                "Disbursed Date",

            "loan_amount":
                "Loan Amount",

            "due_date":
                "Due Date"
        }
    )


    # --------------------------------------------------------
    # Format dates
    # --------------------------------------------------------

    overdue_display[
        "Disbursed Date"
    ] = overdue_display[
        "Disbursed Date"
    ].apply(
        format_date
    )


    overdue_display[
        "Due Date"
    ] = overdue_display[
        "Due Date"
    ].apply(
        format_date
    )


    # --------------------------------------------------------
    # Format amount
    # --------------------------------------------------------

    overdue_display[
        "Loan Amount"
    ] = overdue_display[
        "Loan Amount"
    ].apply(
        lambda x:
            f"{float(x):,.0f}"
    )


    # --------------------------------------------------------
    # Display
    # --------------------------------------------------------

    st.dataframe(
        overdue_display,
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# SAVE LATEST DATA
# ============================================================

# Save updated penalty calculations
save_data(df)
