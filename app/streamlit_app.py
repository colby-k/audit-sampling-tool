# Enhanced Audit Sampling Tool with AgGrid
import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
from datetime import datetime
from st_aggrid import AgGrid, GridOptionsBuilder

st.set_page_config(page_title="Audit Sampling Tool", layout="wide", page_icon="portfolio.ico")

st.markdown("""
    <style>
        .main {
            background-color: #f9f9f9;
        }
        h1, h2, h3 {
            color: #1a4d8f;
        }
        .stButton>button {
            background-color: #1a4d8f;
            color: white;
        }
    </style>
""", unsafe_allow_html=True)

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

def calculate_statistical_sample_size(confidence_level: str, precision_pct: float, expected_error_pct: float) -> int:
    z_scores = {"90%": 1.645, "95%": 1.960, "99%": 2.576}
    Z = z_scores[confidence_level]
    p = expected_error_pct / 100.0
    E = precision_pct / 100.0
    n = (Z ** 2) * p * (1 - p) / (E ** 2)
    return int(np.ceil(n))

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

        st.sidebar.subheader("🎛️ Filter Data")
        filters = {}
        for col in df.columns:
            if df[col].dropna().empty:
                continue
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

        filtered_df = df
        for key, cond in filters.items():
            filtered_df = filtered_df[cond]

        st.subheader("🔎 Filtered Data")
        st.write(f"{len(filtered_df)} rows after filtering")
        AgGrid(filtered_df, height=250, fit_columns_on_grid_load=True)

        st.subheader("🎲 Select Sampling Method")
        method = st.radio("Method", ["Random", "Monetary Unit Sampling", "Stratified", "Statistical (Attribute or Monetary)"])
        sample_df = pd.DataFrame()

        if method == "Stratified":
            strat_col = st.selectbox("Stratify by", filtered_df.columns)
            n_per_group = st.number_input("Samples per group", min_value=1, value=5)
            if st.button("🔀 Run Stratified Sample"):
                for group in filtered_df[strat_col].dropna().unique():
                    group_df = filtered_df[filtered_df[strat_col] == group]
                    n = min(n_per_group, len(group_df))
                    sample_df = pd.concat([sample_df, group_df.sample(n=n)])
                st.success(f"✅ Stratified sample complete: {len(sample_df)} rows")

        elif method == "Statistical (Attribute or Monetary)":
            sample_type = st.selectbox("Sampling Type", ["Attribute", "Monetary"])
            confidence_level = st.selectbox("Confidence Level", ["90%", "95%", "99%"])
            precision = st.number_input("Precision (% Tolerable Deviation)", min_value=0.1, max_value=20.0, value=5.0)
            expected_error = st.number_input("Expected Error Rate (%)", min_value=0.0, max_value=100.0, value=5.0)

            if st.button("🌿 Run Statistical Sample"):
                n = calculate_statistical_sample_size(confidence_level, precision, expected_error)
                n = min(n, len(filtered_df))
                if sample_type == "Attribute":
                    sample_df = filtered_df.sample(n=n)
                else:
                    monetary_cols = filtered_df.select_dtypes(include='number').columns.tolist()
                    default_col = auto_detect_monetary_column(filtered_df)
                    col = st.selectbox("Select monetary column to use", monetary_cols, index=monetary_cols.index(default_col) if default_col in monetary_cols else 0)
                    weights = filtered_df[col]
                    probs = weights / weights.sum()
                    sample_df = filtered_df.sample(n=n, weights=probs)
                    st.info(f"💰 Using column: '{col}' for weighting")
                st.success(f"✅ Statistical sample complete: {len(sample_df)} rows")

        else:
            suggested = determine_sample_size(len(filtered_df))
            n = st.number_input("Sample size", min_value=1, max_value=len(filtered_df), value=suggested)
            if st.button("🎯 Run Sample"):
                if method == "Random":
                    sample_df = filtered_df.sample(n=n)
                else:
                    monetary_cols = filtered_df.select_dtypes(include='number').columns.tolist()
                    default_col = auto_detect_monetary_column(filtered_df)
                    col = st.selectbox("Select monetary column to use", monetary_cols, index=monetary_cols.index(default_col) if default_col in monetary_cols else 0)
                    weights = filtered_df[col]
                    probs = weights / weights.sum()
                    sample_df = filtered_df.sample(n=n, weights=probs)
                    st.info(f"💰 Using column: '{col}' for weighting")
                st.success(f"✅ Sample complete: {len(sample_df)} rows")

        if not sample_df.empty:
            st.subheader("📊 Sample Summary")
            st.info(f"Selected {len(sample_df)} items from population of {len(filtered_df)}.")

        if not sample_df.empty:
            st.subheader("📂 Export Sample + Audit Log")

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
            st.download_button("📅 Download Sample File", data=excel_data, file_name="audit_sample.xlsx")
            AgGrid(sample_df, height=250, fit_columns_on_grid_load=True)

    except Exception as e:
        st.error(f"❌ Failed to load/process file: {e}")
else:
    st.info("📂 Upload a CSV or Excel file to begin.")
