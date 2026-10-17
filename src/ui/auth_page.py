"""Giao diện đăng nhập và đăng ký tài khoản cho ứng dụng F&B Manager."""
import streamlit as st

from ui.login_panel import render_login_panel
from ui.registration_panel import render_registration_panel
from ui.styles import inject_css


def render():
    inject_css()

    st.markdown(
        """
        <div class="auth-brand">
            <div class="auth-brand__logo">🍜</div>
            <h1 class="auth-brand__title">F&B Order Manager</h1>
            <div class="auth-brand__subtitle">Hệ thống Quản lý Bán hàng & Bếp thông minh</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_left, col_center, col_right = st.columns([1, 2.2, 1])
    with col_center:
        login_tab, register_tab = st.tabs(["🔐 Đăng nhập", "📝 Đăng ký tài khoản"])

        with login_tab:
            render_login_panel()

        with register_tab:
            render_registration_panel()
