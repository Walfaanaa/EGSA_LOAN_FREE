import streamlit as st
import pandas as pd
from datetime import date
from dateutil.relativedelta import relativedelta
import math
import os

# ---------------- CONFIG ----------------
st.set_page_config(page_title="AWO Loan App", layout="wide")
st.title("AWO Interest-Free Loan Management App")

DATA_FILE = "awo_loans.csv"

# ---------------- LOAD OR CREATE DATA ----------------
if os.path.exists(DATA_FILE):
    df = pd.read_csv(DATA_FILE, parse_dates=["disbursed_date", "due_date", "return_date"])
else:
    df = pd.DataFrame(columns=[
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
    ])

# ---------------- FUNCTIONS ----------------
def calculate_penalty(amount, due_date, pay_date):
    """Calculate cumulative penalty (10% per month, compounded each month late)"""
    due = pd.to_datetime(due_date)
    pay = pd.to_datetime(pay_date)

    if pay <= due:
        return 0, 0.0, amount

    days_late = (pay - due).days
    months_late = math.ceil(days_late / 30)

    total_due = amount
    penalty = 0.0
    for _ in range(months_late):
        month_penalty = total_due * 0.10  # 10% of current total
        penalty += month_penalty
        total_due += month_penalty

    return months_late, penalty, total_due

def has_active_loan(phone, data):
    """Check if phone has an active loan"""
    active = data[data["returned"] == False]
    return phone in active["phone_number"].astype(str).values

def normalize_date_columns(df):
    """Fix mixed date types for Streamlit dataframe"""
    date_cols = ["disbursed_date", "due_date", "return_date"]
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df

# ---------------- SIDEBAR: ADD SINGLE LOAN ----------------
st.sidebar.header("Add New Loan")
full_name = st.sidebar.text_input("Borrower Full Name")
phone_number = st.sidebar.text_input("Phone Number")
loan_amount = st.sidebar.number_input("Loan Amount", min_value=0.0, step=100.0)
disbursed_date = st.sidebar.date_input("Disbursed Date", date.today())

if st.sidebar.button("Save Loan"):
    if not full_name or not phone_number or loan_amount <= 0:
        st.sidebar.error("Please fill all fields correctly.")
    elif has_active_loan(phone_number, df):
        st.sidebar.error("This phone number already has an active loan.")
    else:
        due_date = disbursed_date + relativedelta(months=10)
        new_row = {
            "full_name": full_name,
            "phone_number": phone_number,
            "loan_amount": loan_amount,
            "disbursed_date": disbursed_date,
            "due_date": due_date,
            "returned": False,
            "return_date": pd.NaT,
            "months_late": 0,
            "penalty_amount": 0.0,
            "total_due": loan_amount
        }
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

        # Remove exact duplicates
        df = df.drop_duplicates(subset=["full_name", "phone_number", "loan_amount", "disbursed_date"], keep="last")

        df = normalize_date_columns(df)
        df.to_csv(DATA_FILE, index=False)
        st.sidebar.success("Loan saved successfully!")

# ---------------- SIDEBAR: UPLOAD LOANS ----------------
st.sidebar.header("Upload Loans (CSV / Excel)")
uploaded_file = st.sidebar.file_uploader("Upload File", type=["csv", "xlsx"])

if uploaded_file:
    if uploaded_file.name.endswith(".csv"):
        upload_df = pd.read_csv(uploaded_file)
    else:
        upload_df = pd.read_excel(uploaded_file)

    required_cols = {"full_name", "phone_number", "loan_amount", "disbursed_date"}
    if not required_cols.issubset(upload_df.columns):
        st.error("File must contain: full_name, phone_number, loan_amount, disbursed_date")
    else:
        upload_df["disbursed_date"] = pd.to_datetime(upload_df["disbursed_date"])
        upload_df["due_date"] = upload_df["disbursed_date"] + pd.DateOffset(months=10)
        upload_df["returned"] = False
        upload_df["return_date"] = pd.NaT
        upload_df["months_late"] = 0
        upload_df["penalty_amount"] = 0.0
        upload_df["total_due"] = upload_df["loan_amount"]

        # Concatenate and remove duplicates
        df = pd.concat([df, upload_df], ignore_index=True)
        df = df.drop_duplicates(subset=["full_name", "phone_number", "loan_amount", "disbursed_date"], keep="last")

        df = normalize_date_columns(df)
        df.to_csv(DATA_FILE, index=False)
        st.success("Loan data uploaded successfully!")

# ---------------- UPDATE PENALTIES ----------------
today = date.today()
for i, row in df.iterrows():
    if not row["returned"]:
        m, p, t = calculate_penalty(row["loan_amount"], row["due_date"], today)
        df.loc[i, "months_late"] = m
        df.loc[i, "penalty_amount"] = p
        df.loc[i, "total_due"] = t

df = normalize_date_columns(df)
df.to_csv(DATA_FILE, index=False)

# ---------------- DISPLAY ALL LOANS ----------------
st.subheader("All Loans")
st.dataframe(df.reset_index(drop=True), use_container_width=True)  # display consecutive row numbers

# ---------------- MARK LOAN AS RETURNED ----------------
st.subheader("Mark Loan as Returned")
active_loans = df[df["returned"] == False]

if not active_loans.empty:
    selected_index = st.selectbox(
        "Select Borrower",
        active_loans.index,
        format_func=lambda i: active_loans.loc[i, "full_name"]
    )

    return_date = st.date_input("Return Date", date.today())

    if st.button("Confirm Return"):
        m, p, t = calculate_penalty(
            df.loc[selected_index, "loan_amount"],
            df.loc[selected_index, "due_date"],
            return_date
        )

        df.loc[selected_index, "returned"] = True
        df.loc[selected_index, "return_date"] = return_date
        df.loc[selected_index, "months_late"] = m
        df.loc[selected_index, "penalty_amount"] = p
        df.loc[selected_index, "total_due"] = t

        df = normalize_date_columns(df)
        df.to_csv(DATA_FILE, index=False)
        st.success(f"Loan marked as returned! Months late: {m}, Penalty: {p:.2f}, Total due: {t:.2f}")
else:
    st.info("No active loans to return.")

# ---------------- OVERDUE LOANS ----------------
st.subheader("Overdue Loans")
overdue_df = df[(df["returned"] == False) & (pd.to_datetime(df["due_date"]) < pd.to_datetime(today))]
st.dataframe(overdue_df.reset_index(drop=True), use_container_width=True)
