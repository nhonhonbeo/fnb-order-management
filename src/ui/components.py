"""Các component trình bày tái sử dụng cho F&B Manager."""
from html import escape

import streamlit as st


def kpi_card(icon, label, value, sublabel, color):
    """Hiển thị một card KPI theo hệ thống thiết kế của ứng dụng."""
    trend_class = ""
    if "▲" in str(sublabel):
        trend_class = " kpi-sublabel--up"
    elif "▼" in str(sublabel):
        trend_class = " kpi-sublabel--down"

    st.markdown(
        f"""
        <div class="kpi-card" style="--card-color: {escape(str(color), quote=True)};">
            <div class="kpi-card__icon">{escape(str(icon))}</div>
            <div class="kpi-card__label">{escape(str(label))}</div>
            <div class="kpi-card__value">{escape(str(value))}</div>
            <div class="kpi-card__sublabel{trend_class}">{escape(str(sublabel))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
