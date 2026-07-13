"""Streamlit UI for Reopen Detector."""

import sys
from datetime import time
from pathlib import Path

import streamlit as st

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from reopen_detector.loader import load_csv
from reopen_detector.validator import validate_dataframe
from reopen_detector.normalizer import normalize_dataframe
from reopen_detector.detector import detect_reopens
from reopen_detector.filters import filter_by_reopen_date
from reopen_detector.formatter import format_aggregated_table, format_visible_table
from reopen_detector.exporter import export_to_csv, export_to_excel
from reopen_detector.metrics import calculate_metrics

# Page config
st.set_page_config(
    page_title="Detector de Casos Reopen",
    page_icon="🔍",
    layout="wide",
)

st.title("🔍 Detector de Casos Reopen")

st.markdown(
    """
Analiza un archivo CSV de interacciones de Salesforce y detecta casos que fueron reabiertos
después de haber sido marcados como **Resolved**.
"""
)

# Step 1: Upload CSV
st.header("1. Cargar archivo CSV")
uploaded_file = st.file_uploader(
    "Selecciona un archivo CSV",
    type=["csv"],
    help="El archivo debe contener las columnas: StartTime, NewValue, Email, case_number",
)

# Step 2: Date range
st.header("2. Seleccionar rango de fechas y horas")
st.caption("Horario de Uruguay (UTC-3)")

col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("Fecha inicio", value=None)
    start_time = st.time_input("Hora inicio", value=time(0, 0))
with col2:
    end_date = st.date_input("Fecha fin", value=None)
    end_time = st.time_input("Hora fin", value=time(23, 59))

# Step 3: Analyze button
st.header("3. Analizar")
analyze_clicked = st.button("🔎 Analizar", type="primary", use_container_width=True)

# Session state for results
if "results" not in st.session_state:
    st.session_state.results = None
if "technical_df" not in st.session_state:
    st.session_state.technical_df = None
if "metrics" not in st.session_state:
    st.session_state.metrics = None
if "visible_df" not in st.session_state:
    st.session_state.visible_df = None
if "technical_in_range" not in st.session_state:
    st.session_state.technical_in_range = None

if analyze_clicked:
    if uploaded_file is None:
        st.error("Por favor, carga un archivo CSV primero.")
    else:
        with st.spinner("Procesando archivo..."):
            try:
                # Load CSV
                raw_df = load_csv(uploaded_file)
                raw_row_count = len(raw_df)

                # Validate structure
                errors = validate_dataframe(raw_df)
                if errors:
                    for err in errors:
                        st.error(err)
                    st.stop()

                # Normalize
                normalized_df, invalid_dates = normalize_dataframe(raw_df)
                unique_cases = normalized_df["case_number"].nunique()

                # Detect reopens (with optional date/time range for
                # reopen_por_resolved_en_rango strategy)
                all_reopens = detect_reopens(
                    normalized_df,
                    start_date=start_date if start_date else None,
                    end_date=end_date if end_date else None,
                    start_time=start_time if start_date else None,
                    end_time=end_time if end_date else None,
                )
                total_reopens = len(all_reopens)

                # Filter by date range and time
                filtered_reopens = filter_by_reopen_date(
                    all_reopens,
                    start_date,
                    end_date,
                    start_time,
                    end_time,
                )
                reopens_in_range = len(filtered_reopens)

                # Calculate metrics
                st.session_state.metrics = calculate_metrics(
                    raw_row_count=raw_row_count,
                    unique_cases=unique_cases,
                    invalid_dates=invalid_dates,
                    total_reopens=total_reopens,
                    reopens_in_range=reopens_in_range,
                )

                # Add the unique cases with reopen metric separately
                # (avoids caching issues with stale module imports)
                cases_with_reopen = (
                    all_reopens["case_number"].nunique()
                    if not all_reopens.empty
                    else 0
                )
                st.session_state.metrics["Casos con reopen"] = cases_with_reopen

                # Format for display (aggregated: one row per case)
                st.session_state.visible_df = format_aggregated_table(filtered_reopens)
                st.session_state.technical_df = all_reopens
                st.session_state.technical_in_range = filtered_reopens
                st.session_state.results = True

            except Exception as e:
                st.error(f"Error al procesar el archivo: {str(e)}")
                st.session_state.results = False

# Display results if available
if st.session_state.results and st.session_state.metrics:
    st.header("📊 Métricas")

    metric_data = st.session_state.metrics
    cols = st.columns(len(metric_data))
    for i, (name, value) in enumerate(metric_data.items()):
        with cols[i]:
            st.metric(label=name, value=value)

    st.header("📋 Resultados")

    if st.session_state.visible_df is not None and not st.session_state.visible_df.empty:
        st.dataframe(
            st.session_state.visible_df,
            use_container_width=True,
            hide_index=True,
        )

        # Download buttons
        col_csv, col_excel = st.columns(2)

        # Technical details for export
        tech_export = st.session_state.technical_in_range

        with col_csv:
            csv_data = export_to_csv(
                st.session_state.visible_df, tech_export
            )
            st.download_button(
                label="📥 Descargar CSV",
                data=csv_data,
                file_name="reopens_detectados.csv",
                mime="text/csv",
                use_container_width=True,
            )

        with col_excel:
            excel_data = export_to_excel(
                st.session_state.visible_df,
                tech_export if tech_export is not None else st.session_state.visible_df,
            )
            st.download_button(
                label="📥 Descargar Excel",
                data=excel_data,
                file_name="reopens_detectados.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

        # Show technical details checkbox
        show_technical = st.checkbox("🔧 Mostrar detalles técnicos")

        if show_technical and st.session_state.technical_in_range is not None:
            st.subheader("Detalle técnico")
            st.dataframe(
                st.session_state.technical_in_range,
                use_container_width=True,
                hide_index=True,
            )
    else:
        st.info("No se encontraron reopens en el rango de fechas seleccionado.")