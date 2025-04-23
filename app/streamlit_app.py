# Enhanced Audit Sampling Tool with Sample Summary
import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
from datetime import datetime
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
import altair as alt

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

def show_grid(dataframe, monetary_col, key):
    df_display = dataframe.copy()

    gb = GridOptionsBuilder.from_dataframe(df_display)
    gb.configure_default_column(editable=True, groupable=True)

    if monetary_col:
        gb.configure_column(monetary_col, cellStyle={
            "styleConditions": [
                {
                    "condition": "params.value >= 10000",
                    "style": {"color": "white", "backgroundColor": "#d9534f"}
                }
            ]
        })

    grid_options = gb.build()
    grid_response = AgGrid(
        df_display,
        gridOptions=grid_options,
        update_mode=GridUpdateMode.NO_UPDATE,
        fit_columns_on_grid_load=True,
        height=300,
        allow_unsafe_jscode=True,
        key=key,
        reload_data=False
    )
    return grid_response['data']

def show_chart(dataframe):
    chart_col = st.selectbox("Select column to summarize", dataframe.select_dtypes(include='object').columns)
    monetary_col = auto_detect_monetary_column(dataframe)
    chart_data = dataframe.groupby(chart_col)[monetary_col].sum().reset_index()
    chart = alt.Chart(chart_data).mark_bar().encode(
        x=alt.X(chart_col, sort='-y'),
        y=alt.Y(monetary_col),
        tooltip=[chart_col, monetary_col]
    ).properties(width=700, height=300)
    st.altair_chart(chart)

# Display sampled data and summary if available
if "sample_df" in st.session_state:
    sample_df = st.session_state["sample_df"]
    st.subheader("📊 Sample Output")
    monetary_col = auto_detect_monetary_column(sample_df)
    updated_sample_df = show_grid(sample_df, monetary_col, key="sample_grid")

    st.subheader("📈 Sample Summary")
    st.info(f"Selected {len(updated_sample_df)} records from population of {len(filtered_df)} after filtering.")
    if monetary_col in updated_sample_df.columns:
        st.write(f"**Total {monetary_col}:** {updated_sample_df[monetary_col].sum():,.2f}")
        st.write(f"**Average {monetary_col}:** {updated_sample_df[monetary_col].mean():,.2f}")

    st.subheader("📥 Download Sample")
    def export_to_excel(df):
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name="Sample", index=False)
        return output.getvalue()

    excel_data = export_to_excel(updated_sample_df)
    st.download_button("📂 Download Sample File", data=excel_data, file_name="audit_sample.xlsx")
