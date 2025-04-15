
import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
from datetime import datetime
import matplotlib.pyplot as plt
from scipy.stats import norm

st.set_page_config(page_title="Audit Sampling Tool", layout="wide")
st.title("Audit Sampling Tool")

st.sidebar.header("📁 Upload File")
uploaded_file = st.sidebar.file_uploader("Upload CSV or Excel", type=["csv", "xlsx"])

# Utilities
def determine_sample_size(n):
    if n <= 50:
        return n
    elif n <= 250:
        return 25
    elif n <= 500:
        return 40
    else:
        return 60

def statistical_sample_size(N, confidence=0.95, margin_of_error=0.05, p=0.5):
    z = norm.ppf(1 - (1 - confidence) / 2)
    n_0 = (z**2 * p * (1 - p)) / margin_of_error**2
    n = n_0 / (1 + ((n_0 - 1) / N))  # finite population correction
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

        # Step 2: Filters
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
        st.dataframe(filtered_df)

        st.subheader("🎲 Select Sampling Method")
        method = st.radio("Method", ["Random", "Monetary Unit Sampling", "Stratified", "Statistical"])
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
                st.markdown(f"**📋 Sample Summary:** {len(sample_df)} total rows selected across all groups.")
                st.success(f"✅ Stratified sample complete: {len(sample_df)} rows")

        elif method == "Statistical":
            confidence = st.selectbox("Confidence Level", [0.90, 0.95, 0.99], index=1)
            margin = st.slider("Margin of Error (%)", min_value=1, max_value=10, value=5) / 100
            n = statistical_sample_size(len(filtered_df), confidence=confidence, margin_of_error=margin)
            st.info(f"🔢 Calculated statistical sample size: {n} rows")
            if st.button("📊 Run Statistical Sample"):
                sample_df = filtered_df.sample(n=min(n, len(filtered_df)))
                st.markdown(f"**📋 Sample Summary:** {n} items selected from {len(filtered_df)} records after filtering.")
                st.success(f"✅ Statistical sample complete: {len(sample_df)} rows")

        else:
            suggested = determine_sample_size(len(filtered_df))
            n = st.number_input("Sample size", min_value=1, max_value=len(filtered_df), value=suggested)

            amount_col = None
            if method == "Monetary Unit Sampling":
                numeric_cols = filtered_df.select_dtypes(include='number').columns.tolist()
                if numeric_cols:
                    amount_col = st.selectbox("💰 Select Amount Field for MUS", numeric_cols)
                else:
                    st.warning("⚠️ No numeric columns available for Monetary Unit Sampling.")

            if st.button("🎯 Run Sample"):
                if method == "Random":
                    sample_df = filtered_df.sample(n=n)
                    st.markdown(f"**📋 Sample Summary:** {n} items selected from {len(filtered_df)} records after filtering.")
                    st.success(f"✅ Random sample complete: {len(sample_df)} rows")
                elif method == "Monetary Unit Sampling":
                    if amount_col:
                        try:
                            weights = filtered_df[amount_col].abs()
                            total_weight = weights.sum()
                            if total_weight == 0:
                                st.error("❌ All weights are zero. Cannot perform Monetary Unit Sampling.")
                            else:
                                probs = weights / total_weight
                                sample_df = filtered_df.sample(n=n, weights=probs)
                                st.markdown(f"**📋 Sample Summary:** {n} items selected from {len(filtered_df)} records after filtering.")
                                st.success(f"✅ MUS sample complete: {len(sample_df)} rows")
                    
        # Show AICPA guide above method selector
        if st.checkbox("📖 Show AICPA sample size guide", key="aicpa_end_section"):
            aicpa_table = pd.DataFrame({
                "Population Size": ["0–50", "51–250", "251–500", "500+"],
                "Suggested Sample Size": ["All", "25", "40", "60"]
            })
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("📘 AICPA Table")
                st.table(aicpa_table)
            with col2:
                st.subheader("📈 Chart")
                x = [25, 100, 300, 1000]
                y = [25, 25, 40, 60]
                fig, ax = plt.subplots()
                ax.plot(x, y, marker='o')
                ax.set_xlabel("Population Size")
                ax.set_ylabel("Sample Size")
                ax.set_title("AICPA-Inspired Fixed Sample Sizes")
                st.pyplot(fig)


    except Exception as e:
                            st.error(f"❌ Error in MUS sampling: {e}")
                    else:
                        st.error("❌ Please select a valid amount field.")

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


        # Show AICPA guide above method selector
        if st.checkbox("📖 Show AICPA sample size guide", key="aicpa_end_section"):
            aicpa_table = pd.DataFrame({
                "Population Size": ["0–50", "51–250", "251–500", "500+"],
                "Suggested Sample Size": ["All", "25", "40", "60"]
            })
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("📘 AICPA Table")
                st.table(aicpa_table)
            with col2:
                st.subheader("📈 Chart")
                x = [25, 100, 300, 1000]
                y = [25, 25, 40, 60]
                fig, ax = plt.subplots()
                ax.plot(x, y, marker='o')
                ax.set_xlabel("Population Size")
                ax.set_ylabel("Sample Size")
                ax.set_title("AICPA-Inspired Fixed Sample Sizes")
                st.pyplot(fig)


    except Exception as e:
        st.error(f"❌ Failed to load/process file: {e}")

else:
    st.info("📂 Upload a CSV or Excel file to begin.")



    # Show AICPA guide at end of app
    if st.checkbox("📖 Show AICPA sample size guide", key="aicpa_end_section"):
        aicpa_table = pd.DataFrame({
            "Population Size": ["0–50", "51–250", "251–500", "500+"],
            "Suggested Sample Size": ["All", "25", "40", "60"]
        })
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("📘 AICPA Table")
            st.table(aicpa_table)
        with col2:
            st.subheader("📈 Chart")
            x = [25, 100, 300, 1000]
            y = [25, 25, 40, 60]
            fig, ax = plt.subplots()
            ax.plot(x, y, marker='o')
            ax.set_xlabel("Population Size")
            ax.set_ylabel("Sample Size")
            ax.set_title("AICPA-Inspired Fixed Sample Sizes")
            st.pyplot(fig)

