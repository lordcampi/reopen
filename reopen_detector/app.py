"""Streamlit UI for Reopen Detector."""

import sys
from datetime import time
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent / "src"))

from reopen_detector.loader import load_csv
from reopen_detector.validator import validate_dataframe
from reopen_detector.normalizer import normalize_dataframe
from reopen_detector.detector import detect_reopens
from reopen_detector.detector_v2 import detect_reopens_v2
from reopen_detector.filters import filter_by_reopen_date
from reopen_detector.formatter import format_aggregated_table
from reopen_detector.exporter import export_to_excel
from reopen_detector.metrics import calculate_metrics
from reopen_detector.country_analytics import build_country_donut_chart
from reopen_detector.weekly_analytics import (
    build_week_catalog,
    build_weekly_comparison_donut,
    compare_weeks,
    format_delta_pct,
    get_available_years,
)

CUSTOM_CSS = """
<style>
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
        max-width: 1200px;
    }
    .app-header {
        background: linear-gradient(135deg, #111827 0%, #0a0a0a 100%);
        border: 1px solid #1f2937;
        border-radius: 16px;
        padding: 1.75rem 2rem;
        margin-bottom: 1.5rem;
    }
    .app-header h1 {
        margin: 0 0 0.35rem 0;
        font-size: 2rem;
        color: #f9fafb;
        letter-spacing: -0.02em;
    }
    .app-header p {
        margin: 0;
        color: #9ca3af;
        font-size: 1rem;
        line-height: 1.5;
    }
    .metric-card {
        background: linear-gradient(180deg, #141414 0%, #0f0f0f 100%);
        border: 1px solid #262626;
        border-radius: 14px;
        padding: 1.25rem 1.5rem;
        min-height: 110px;
    }
    .metric-label {
        color: #9ca3af;
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        margin-bottom: 0.5rem;
    }
    .metric-value {
        color: #f9fafb;
        font-size: 2rem;
        font-weight: 700;
        line-height: 1.1;
    }
    .metric-sub {
        color: #6b7280;
        font-size: 0.8rem;
        margin-top: 0.35rem;
    }
    .section-title {
        color: #f9fafb;
        font-size: 1.15rem;
        font-weight: 700;
        margin: 0 0 0.75rem 0;
    }
    div[data-testid="stTabs"] button {
        font-weight: 600;
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


def render_week_kpi_cards(comparison: dict) -> None:
    """Render comparison KPI cards outside the chart."""
    week_a = comparison["week_a"]
    week_b = comparison["week_b"]
    cols = st.columns(4)

    cards = [
        (week_a["short_label"], week_a["total"], week_a["label"]),
        (week_b["short_label"], week_b["total"], week_b["label"]),
        ("Casos únicos A", week_a["unique_cases"], week_a["label"]),
        ("Casos únicos B", week_b["unique_cases"], week_b["label"]),
    ]

    for col, (label, value, subtitle) in zip(cols, cards):
        with col:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-label">{label}</div>
                    <div class="metric-value">{value:,}</div>
                    <div class="metric-sub">{subtitle}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_weekly_comparison(all_reopens) -> None:
    """Render weekly comparison selectors and donut chart."""
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
    render_week_kpi_cards(comparison)

    delta_total = comparison["delta_total"]
    delta_sign = "+" if delta_total >= 0 else ""
    st.info(
        f"Variación: **{format_delta_pct(comparison['delta_pct'])}** "
        f"({delta_sign}{delta_total} reopens)"
    )

    st.plotly_chart(
        build_weekly_comparison_donut(comparison),
        use_container_width=True,
    )


def render_range_analysis_tab(
    *,
    widget_prefix: str,
    metrics_key: str,
    visible_df_key: str,
    technical_key: str,
    ready_key: str,
    analyze_button_key: str,
    excel_filename: str = "reopens_detectados.xlsx",
    show_v2_badge: bool = False,
    detect_reopens_fn=detect_reopens,
) -> None:
    """Render range filters, metrics, country chart, table and Excel export."""
    if show_v2_badge:
        st.info("V2 Prueba — sandbox de experimentos. Los cambios aquí no afectan Análisis por rango.")

    st.caption("Horario de Uruguay (UTC-3)")

    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(
            "Fecha inicio",
            value=None,
            key=f"{widget_prefix}start_date",
        )
        start_time = st.time_input(
            "Hora inicio",
            value=time(0, 0),
            key=f"{widget_prefix}start_time",
        )
    with col2:
        end_date = st.date_input(
            "Fecha fin",
            value=None,
            key=f"{widget_prefix}end_date",
        )
        end_time = st.time_input(
            "Hora fin",
            value=time(23, 59),
            key=f"{widget_prefix}end_time",
        )

    analyze_range = st.button(
        "Analizar rango",
        type="primary",
        use_container_width=True,
        key=analyze_button_key,
    )

    if analyze_range:
        if st.session_state.normalized_df is None:
            st.error("Primero procesa un archivo CSV.")
        else:
            with st.spinner("Analizando rango..."):
                try:
                    normalized_df = st.session_state.normalized_df
                    range_reopens = detect_reopens_fn(
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
                    st.session_state[metrics_key] = calculate_metrics(filtered_reopens)
                    st.session_state[visible_df_key] = format_aggregated_table(
                        filtered_reopens
                    )
                    st.session_state[technical_key] = filtered_reopens
                    st.session_state[ready_key] = True
                except Exception as e:
                    st.error(f"Error al analizar el rango: {str(e)}")
                    st.session_state[ready_key] = False

    if not st.session_state.get(ready_key):
        st.info("Selecciona un rango de fechas y presiona Analizar rango.")
        return

    st.markdown('<p class="section-title">Métricas del período</p>', unsafe_allow_html=True)
    render_metric_cards(st.session_state[metrics_key])

    tech_export = st.session_state[technical_key]
    country_chart = build_country_donut_chart(tech_export)

    if country_chart is not None:
        st.markdown('<p class="section-title">Reopens por país</p>', unsafe_allow_html=True)
        st.plotly_chart(country_chart, use_container_width=True)
    elif tech_export is not None and not tech_export.empty:
        st.info("No hay datos de país disponibles para el rango seleccionado.")

    st.markdown('<p class="section-title">Resultados</p>', unsafe_allow_html=True)

    visible_df = st.session_state[visible_df_key]
    if visible_df is not None and not visible_df.empty:
        st.dataframe(
            visible_df,
            use_container_width=True,
            hide_index=True,
        )

        excel_data = export_to_excel(
            visible_df,
            tech_export if tech_export is not None else visible_df,
        )
        st.download_button(
            label="Descargar Excel",
            data=excel_data,
            file_name=excel_filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            key=f"{widget_prefix}download_excel",
        )
    else:
        st.info("No se encontraron reopens en el rango de fechas seleccionado.")


def render_range_analysis() -> None:
    """Render the production range analysis tab."""
    render_range_analysis_tab(
        widget_prefix="range_",
        metrics_key="metrics",
        visible_df_key="visible_df",
        technical_key="technical_in_range",
        ready_key="range_ready",
        analyze_button_key="range_analyze",
    )


def render_range_analysis_v2() -> None:
    """Render the sandbox V2 range analysis tab."""
    render_range_analysis_tab(
        widget_prefix="range_v2_",
        metrics_key="metrics_v2",
        visible_df_key="visible_df_v2",
        technical_key="technical_in_range_v2",
        ready_key="range_ready_v2",
        analyze_button_key="range_v2_analyze",
        excel_filename="reopens_detectados_v2.xlsx",
        show_v2_badge=True,
        detect_reopens_fn=detect_reopens_v2,
    )


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
    st.markdown('<p class="section-title">Cargar archivo CSV</p>', unsafe_allow_html=True)
    uploaded_file = st.file_uploader(
        "Selecciona un archivo CSV",
        type=["csv"],
        help="El archivo debe contener las columnas: StartTime, NewValue, Email, case_number",
        label_visibility="collapsed",
    )
    process_clicked = st.button("Procesar CSV", type="primary", use_container_width=True)

if "normalized_df" not in st.session_state:
    st.session_state.normalized_df = None
if "all_reopens" not in st.session_state:
    st.session_state.all_reopens = None
if "metrics" not in st.session_state:
    st.session_state.metrics = None
if "visible_df" not in st.session_state:
    st.session_state.visible_df = None
if "technical_in_range" not in st.session_state:
    st.session_state.technical_in_range = None
if "csv_ready" not in st.session_state:
    st.session_state.csv_ready = False
if "range_ready" not in st.session_state:
    st.session_state.range_ready = False
if "metrics_v2" not in st.session_state:
    st.session_state.metrics_v2 = None
if "visible_df_v2" not in st.session_state:
    st.session_state.visible_df_v2 = None
if "technical_in_range_v2" not in st.session_state:
    st.session_state.technical_in_range_v2 = None
if "range_ready_v2" not in st.session_state:
    st.session_state.range_ready_v2 = False

if process_clicked:
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
                st.session_state.normalized_df = normalized_df
                st.session_state.all_reopens = detect_reopens(normalized_df)
                st.session_state.csv_ready = True
                st.session_state.range_ready = False
                st.session_state.metrics = None
                st.session_state.visible_df = None
                st.session_state.technical_in_range = None
                st.session_state.range_ready_v2 = False
                st.session_state.metrics_v2 = None
                st.session_state.visible_df_v2 = None
                st.session_state.technical_in_range_v2 = None
                st.success("CSV procesado. Usa las pestañas para analizar.")
            except Exception as e:
                st.error(f"Error al procesar el archivo: {str(e)}")
                st.session_state.csv_ready = False

if st.session_state.csv_ready:
    tab_range, tab_range_v2, tab_weekly = st.tabs(
        ["Análisis por rango", "Análisis por rango V2 Prueba", "Comparación semanal"]
    )

    with tab_range:
        render_range_analysis()

    with tab_range_v2:
        render_range_analysis_v2()

    with tab_weekly:
        if st.session_state.all_reopens is not None:
            render_weekly_comparison(st.session_state.all_reopens)
        else:
            st.info("No hay datos de reopens disponibles.")
