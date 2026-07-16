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
from reopen_detector.formatter import format_aggregated_table
from reopen_detector.exporter import export_to_csv, export_to_excel
from reopen_detector.metrics import calculate_metrics
from reopen_detector.weekly_analytics import (
    build_comparison_chart,
    build_trend_chart,
    build_week_catalog,
    compare_weeks,
    get_available_years,
    weekly_totals_for_year,
)

CUSTOM_CSS = """
<style>
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1200px;
    }
    .app-header {
        background: linear-gradient(135deg, #eff6ff 0%, #f8fafc 55%, #ffffff 100%);
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        padding: 1.75rem 2rem;
        margin-bottom: 1.5rem;
    }
    .app-header h1 {
        margin: 0 0 0.35rem 0;
        font-size: 2rem;
        color: #0f172a;
        letter-spacing: -0.02em;
    }
    .app-header p {
        margin: 0;
        color: #64748b;
        font-size: 1rem;
        line-height: 1.5;
    }
    .section-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 14px;
        padding: 1.25rem 1.5rem;
        margin-bottom: 1rem;
    }
    .metric-card {
        background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
        border: 1px solid #e2e8f0;
        border-radius: 14px;
        padding: 1.25rem 1.5rem;
        min-height: 120px;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    }
    .metric-label {
        color: #64748b;
        font-size: 0.9rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        margin-bottom: 0.5rem;
    }
    .metric-value {
        color: #0f172a;
        font-size: 2.25rem;
        font-weight: 700;
        line-height: 1.1;
    }
    .section-title {
        color: #0f172a;
        font-size: 1.15rem;
        font-weight: 700;
        margin: 0 0 0.75rem 0;
    }
    div[data-testid="stMetric"] {
        background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
        border: 1px solid #e2e8f0;
        border-radius: 14px;
        padding: 1rem 1.25rem;
    }
</style>
"""


def render_metric_cards(metrics: dict) -> None:
    """Render KPI cards with custom styling."""
    cols = st.columns(len(metrics))
    for col, (label, value) in zip(cols, metrics.items()):
        with col:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-label">{label}</div>
                    <div class="metric-value">{value:,}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_weekly_comparison(all_reopens) -> None:
    """Render weekly comparison selectors and charts."""
    st.markdown('<p class="section-title">Comparación por semanas</p>', unsafe_allow_html=True)
    st.caption(
        "Compara reopens entre dos semanas ISO del año usando todos los "
        "reopens detectados en el CSV."
    )

    years = get_available_years(all_reopens)
    default_year = years[-1]

    col_year, col_week_a, col_week_b = st.columns([1, 1, 1])
    with col_year:
        selected_year = st.selectbox(
            "Año",
            options=years,
            index=years.index(default_year),
            key="weekly_year",
        )

    catalog = build_week_catalog(selected_year)
    week_options = {item["week"]: item["label"] for item in catalog}
    week_numbers = list(week_options.keys())
    default_a = week_numbers[0]
    default_b = week_numbers[min(1, len(week_numbers) - 1)]

    with col_week_a:
        week_a = st.selectbox(
            "Semana A",
            options=week_numbers,
            index=week_numbers.index(default_a),
            format_func=lambda w: week_options[w],
            key="weekly_week_a",
        )
    with col_week_b:
        week_b = st.selectbox(
            "Semana B",
            options=week_numbers,
            index=week_numbers.index(default_b),
            format_func=lambda w: week_options[w],
            key="weekly_week_b",
        )

    comparison = compare_weeks(all_reopens, selected_year, week_a, week_b)
    weekly_df = weekly_totals_for_year(all_reopens, selected_year)

    delta_total = comparison["delta_total"]
    delta_sign = "+" if delta_total >= 0 else ""
    st.info(
        f"Diferencia en reopens totales: **{delta_sign}{delta_total}** "
        f"({comparison['week_a']['label']} vs {comparison['week_b']['label']})"
    )

    chart_col_a, chart_col_b = st.columns(2)
    with chart_col_a:
        st.plotly_chart(
            build_comparison_chart(comparison),
            use_container_width=True,
        )
    with chart_col_b:
        st.plotly_chart(
            build_trend_chart(weekly_df, week_a, week_b),
            use_container_width=True,
        )


# Page config
st.set_page_config(
    page_title="Detector de Casos Reopen",
    page_icon="🔍",
    layout="wide",
)

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

st.markdown(
    """
    <div class="app-header">
        <h1>Detector de Casos Reopen</h1>
        <p>
            Analiza interacciones de Salesforce y detecta casos reabiertos
            después de haber sido marcados como <strong>Resolved</strong>.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.container(border=True):
    st.markdown('<p class="section-title">1. Cargar archivo CSV</p>', unsafe_allow_html=True)
    uploaded_file = st.file_uploader(
        "Selecciona un archivo CSV",
        type=["csv"],
        help="El archivo debe contener las columnas: StartTime, NewValue, Email, case_number",
        label_visibility="collapsed",
    )

with st.container(border=True):
    st.markdown(
        '<p class="section-title">2. Seleccionar rango de fechas y horas</p>',
        unsafe_allow_html=True,
    )
    st.caption("Horario de Uruguay (UTC-3)")

    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Fecha inicio", value=None)
        start_time = st.time_input("Hora inicio", value=time(0, 0))
    with col2:
        end_date = st.date_input("Fecha fin", value=None)
        end_time = st.time_input("Hora fin", value=time(23, 59))

with st.container(border=True):
    st.markdown('<p class="section-title">3. Analizar</p>', unsafe_allow_html=True)
    analyze_clicked = st.button("Analizar", type="primary", use_container_width=True)

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
if "all_reopens" not in st.session_state:
    st.session_state.all_reopens = None

if analyze_clicked:
    if uploaded_file is None:
        st.error("Por favor, carga un archivo CSV primero.")
    else:
        with st.spinner("Procesando archivo..."):
            try:
                raw_df = load_csv(uploaded_file)

                errors = validate_dataframe(raw_df)
                if errors:
                    for err in errors:
                        st.error(err)
                    st.stop()

                normalized_df, _invalid_dates = normalize_dataframe(raw_df)

                # Full detection for weekly analytics (strategies 1 and 2)
                st.session_state.all_reopens = detect_reopens(normalized_df)

                # Detection with optional range for strategy 3 and filtered results
                range_reopens = detect_reopens(
                    normalized_df,
                    start_date=start_date if start_date else None,
                    end_date=end_date if end_date else None,
                    start_time=start_time if start_date else None,
                    end_time=end_time if end_date else None,
                )

                filtered_reopens = filter_by_reopen_date(
                    range_reopens,
                    start_date,
                    end_date,
                    start_time,
                    end_time,
                )

                st.session_state.metrics = calculate_metrics(filtered_reopens)
                st.session_state.visible_df = format_aggregated_table(filtered_reopens)
                st.session_state.technical_df = range_reopens
                st.session_state.technical_in_range = filtered_reopens
                st.session_state.results = True

            except Exception as e:
                st.error(f"Error al procesar el archivo: {str(e)}")
                st.session_state.results = False

if st.session_state.results and st.session_state.metrics:
    st.divider()

    st.markdown('<p class="section-title">Métricas del período</p>', unsafe_allow_html=True)
    render_metric_cards(st.session_state.metrics)

    if st.session_state.all_reopens is not None:
        st.divider()
        with st.container(border=True):
            render_weekly_comparison(st.session_state.all_reopens)

    st.divider()
    st.markdown('<p class="section-title">Resultados</p>', unsafe_allow_html=True)

    if st.session_state.visible_df is not None and not st.session_state.visible_df.empty:
        st.dataframe(
            st.session_state.visible_df,
            use_container_width=True,
            hide_index=True,
        )

        col_csv, col_excel = st.columns(2)
        tech_export = st.session_state.technical_in_range

        with col_csv:
            csv_data = export_to_csv(st.session_state.visible_df, tech_export)
            st.download_button(
                label="Descargar CSV",
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
                label="Descargar Excel",
                data=excel_data,
                file_name="reopens_detectados.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

        show_technical = st.checkbox("Mostrar detalles técnicos")

        if show_technical and st.session_state.technical_in_range is not None:
            st.subheader("Detalle técnico")
            st.dataframe(
                st.session_state.technical_in_range,
                use_container_width=True,
                hide_index=True,
            )
    else:
        st.info("No se encontraron reopens en el rango de fechas seleccionado.")
