import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
from datetime import datetime

st.set_page_config(page_title="Audit Sampling Tool", layout="wide")
st.title("Audit Sampling Tool")

st.sidebar.header("📁 Upload File")
uploaded_file = st.sidebar.file_uploader("Upload CSV or Excel", type=["csv", "xlsx"])

# Utilities
def auto_detect_monetary_column(df):
    numeric_cols = df.select_dtypes(include='number').columns.tolist()
    keywords = ['amount', 'total', 'value', 'payment', 'invoice', 'price', 'cost', 'fee']
    for col in numeric_cols:
        if any(k in col.lower() for k in keywords):
            return col
    return numeric_cols[0] if numeric_cols else None

def determine_sample_size(n):
    if n <= 50:
        return n
    elif n <= 250:
        return 25
    elif n <= 500:
        return 40
    else:
        return 60

# Step 1: Upload + Clean
if uploaded_file:
    try:
        filename = uploaded_file.name
        if filename.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        df = df.copy()
        for col in df.select_dtypes(include='object').columns:
            df[col] = df[col].astype(str).str.strip().str.title()

        st.success(f"✅ Loaded {filename} with {len(df)} rows")

        # Step 2: Filters
        st.sidebar.subheader("🎛️ Filter Data")
        filters = {}
        for col in df.columns:
            if df[col].dropna().empty:
                continue  # skip empty columns

            if np.issubdtype(df[col].dtype, np.number):
                min_val, max_val = float(df[col].min()), float(df[col].max())
                if min_val == max_val:
                    st.sidebar.info(f"ℹ️ '{col}' has constant value: {min_val}")
                    filters[col] = df[col] == min_val
                else:
                    selected_range = st.sidebar.slider(f"{col} range", min_val, max_val, (min_val, max_val))
                    filters[col] = df[col].between(*selected_range)

            elif np.issubdtype(df[col].dtype, np.datetime64):
                min_date, max_date = df[col].min(), df[col].max()
                selected = st.sidebar.date_input(f"{col} range", (min_date, max_date))
                if isinstance(selected, tuple):
                    filters[col] = df[col].between(pd.to_datetime(selected[0]), pd.to_datetime(selected[1]))

            else:
                unique = df[col].dropna().unique().tolist()
                selected = st.sidebar.multiselect(f"{col}", unique)
                if selected:
                    filters[col] = df[col].isin(selected)

        # Apply filters
        filtered_df = df
        for key, cond in filters.items():
            filtered_df = filtered_df[cond]

        st.subheader("🔎 Filtered Data")
        st.write(f"{len(filtered_df)} rows after filtering")
        st.dataframe(filtered_df)

        # Step 3: Sampling
        st.subheader("🎲 Select Sampling Method")
        method = st.radio("Method", ["Random", "Monetary Unit Sampling", "Stratified"])
        sample_df = pd.DataFrame()

        if method == "Stratified":
            strat_col = st.selectbox("Stratify by", filtered_df.columns)
            n_per_group = st.number_input("Samples per group", min_value=1, value=5)
            if st.button("🔀 Run Stratified Sample"):
                sample_df = pd.DataFrame()
                for group in filtered_df[strat_col].dropna().unique():
                    group_df = filtered_df[filtered_df[strat_col] == group]
                    n = min(n_per_group, len(group_df))
                    sample_df = pd.concat([sample_df, group_df.sample(n=n)])
                st.success(f"✅ Stratified sample complete: {len(sample_df)} rows")

        else:
            suggested = determine_sample_size(len(filtered_df))
            n = st.number_input("Sample size", min_value=1, max_value=len(filtered_df), value=suggested)

            if st.button("🎯 Run Sample"):
                if method == "Random":
                    sample_df = filtered_df.sample(n=n)
                else:
                    col = auto_detect_monetary_column(filtered_df)
                    weights = filtered_df[col]
                    probs = weights / weights.sum()
                    sample_df = filtered_df.sample(n=n, weights=probs)
                    st.info(f"💰 Using column: '{col}' for weighting")
                st.success(f"✅ Sample complete: {len(sample_df)} rows")

        # Step 4: Export
        if not sample_df.empty:
            st.subheader("💾 Export Sample + Audit Log")

            def export_to_excel(sample_df, filters):
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    sample_df.to_excel(writer, sheet_name="Sample", index=False)
                    audit_log = {
                        "Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "Rows in Population": len(df),
                        "Rows After Filter": len(filtered_df),
                        "Sample Size": len(sample_df),
                        "Filters Applied": str({k: str(v) for k, v in filters.items()})
                    }
                    pd.DataFrame.from_dict(audit_log, orient='index').to_excel(writer, sheet_name="AuditLog")
                return output.getvalue()

            excel_data = export_to_excel(sample_df, filters)
            st.download_button("📥 Download Sample File", data=excel_data, file_name="audit_sample.xlsx")

            st.dataframe(sample_df)

    except Exception as e:
        st.error(f"❌ Failed to load/process file: {e}")
else:
    st.info("📂 Upload a CSV or Excel file to begin.")
