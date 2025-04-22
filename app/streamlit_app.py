# Enhanced Audit Sampling Tool with AgGrid, Conditional Formatting, Row Tagging, and Chart Toggle
import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
from datetime import datetime
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode
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

def show_grid(dataframe, monetary_col):
    df_display = dataframe.copy()
    df_display["Flag"] = False

    gb = GridOptionsBuilder.from_dataframe(df_display)
    gb.configure_default_column(editable=True, groupable=True)
    gb.configure_column("Flag", editable=True, checkbox=True)

    if monetary_col:
        cell_style_jscode = JsCode("""
            function(params) {
                if (params.value >= 10000) {
                    return { 'color': 'white', 'backgroundColor': '#d9534f' }
                }
            }
        """)
        gb.configure_column(monetary_col, cellStyle=cell_style_jscode)

    grid_options = gb.build()
    grid_response = AgGrid(df_display, gridOptions=grid_options, update_mode=GridUpdateMode.MANUAL, fit_columns_on_grid_load=True, height=300)
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
        view_mode = st.radio("View Mode", ["Table", "Chart"], horizontal=True, key="filtered_view")
        if view_mode == "Table":
            monetary_col = auto_detect_monetary_column(filtered_df)
            filtered_df = show_grid(filtered_df, monetary_col)
        else:
            show_chart(filtered_df)

    except Exception as e:
        st.error(f"❌ Failed to load/process file: {e}")
else:
    st.info("📂 Upload a CSV or Excel file to begin.")
