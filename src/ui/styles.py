"""Các quy ước trình bày dùng chung cho giao diện F&B Manager."""
import streamlit as st


def inject_css():
    """Nạp theme CSS toàn cục cho trang Streamlit hiện tại."""
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        :root {
            --primary: #E8590C;
            --success: #2F9E44;
            --warning: #F08C00;
            --danger: #E03131;
            --radius: 14px;
            --shadow: 0 6px 20px rgba(43, 43, 43, 0.08);
            --space-1: 8px;
            --space-2: 16px;
            --space-3: 24px;
            --space-4: 32px;
        }

        html, body, [class*="css"], [data-testid="stAppViewContainer"] {
            font-family: 'Inter', sans-serif;
        }
        [data-testid="stDeployButton"], #MainMenu, footer {
            display: none;
        }
        /* The collapsed-sidebar control belongs to Streamlit's header.
           Keep the header available so users can always reopen the sidebar. */
        [data-testid="stHeader"] {
            display: flex !important;
            visibility: visible !important;
            height: 3.875rem !important;
            background: transparent !important;
        }
        [data-testid="stHeader"] [data-testid="stToolbar"],
        [data-testid="stSidebarCollapsedControl"],
        button[data-testid="stSidebarCollapsedControl"] {
            display: flex !important;
            visibility: visible !important;
            opacity: 1 !important;
        }
        [data-testid="stAppViewContainer"] > .main {
            padding-top: var(--space-2);
        }
        [data-testid="stAppViewContainer"] .block-container {
            padding-top: var(--space-2);
            padding-bottom: var(--space-4);
        }

        h1, [data-testid="stHeadingWithActionElements"] h1 {
            font-size: 28px !important;
            font-weight: 700 !important;
            letter-spacing: -0.03em;
        }
        h2, [data-testid="stHeadingWithActionElements"] h2 {
            font-size: 20px !important;
            font-weight: 600 !important;
        }
        [data-testid="stCaptionContainer"], .stCaption {
            color: #6B7280 !important;
            font-size: 13px !important;
        }
        [data-testid="stMetricLabel"] {
            color: #6B7280 !important;
            font-size: 13px !important;
        }
        [data-testid="stMetricValue"] {
            font-size: 32px !important;
            font-weight: 700 !important;
            color: #2B2B2B;
        }
        [data-testid="stMetric"] {
            padding: var(--space-2);
            border-radius: var(--radius);
            background: #FFFFFF;
            box-shadow: var(--shadow);
        }
        .kpi-card {
            position: relative;
            min-height: 158px;
            padding: var(--space-3);
            overflow: hidden;
            background: #FFFFFF;
            border-left: 4px solid var(--card-color);
            border-radius: var(--radius);
            box-shadow: var(--shadow);
            transition: transform 180ms ease, box-shadow 180ms ease;
        }
        .kpi-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 24px rgba(43, 43, 43, 0.12);
        }
        .kpi-card__icon {
            position: absolute;
            top: var(--space-2);
            right: var(--space-2);
            display: grid;
            width: 42px;
            height: 42px;
            place-items: center;
            border-radius: 50%;
            background: color-mix(in srgb, var(--card-color) 14%, white);
            font-size: 20px;
        }
        .kpi-card__label, .kpi-card__sublabel {
            color: #6B7280;
            font-size: 13px;
            line-height: 1.4;
        }
        .kpi-card__label { font-weight: 600; }
        .kpi-card__value {
            margin: var(--space-2) 0 var(--space-2);
            color: #2B2B2B;
            font-size: 32px;
            font-weight: 700;
            line-height: 1;
            letter-spacing: -0.04em;
        }
        .kpi-sublabel--up { color: var(--success); }
        .kpi-sublabel--down { color: var(--danger); }
        .table-legend {
            display: flex;
            flex-wrap: wrap;
            gap: var(--space-2);
            margin: var(--space-1) 0 var(--space-2);
            color: #6B7280;
            font-size: 13px;
        }
        .table-legend__item { display: inline-flex; align-items: center; gap: var(--space-1); }
        .table-legend__dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
        }
        .table-card {
            min-height: 146px;
            padding: var(--space-2);
            border: 1px solid transparent;
            border-radius: var(--radius);
        }
        .table-card--available { background: #EBFBEE; border-color: #B2F2BB; }
        .table-card--serving { background: #FFF4E6; border-color: #FFD8A8; }
        .table-card--payment { background: #FFF9DB; border-color: #FFEC99; }
        .table-card--cleaning { background: #F1F3F5; border-color: #DEE2E6; }
        .table-card__name { color: #2B2B2B; font-size: 16px; font-weight: 700; }
        .table-card__seats, .table-card__meta { color: #6B7280; font-size: 13px; }
        .table-card__status { margin: var(--space-1) 0; color: #2B2B2B; font-size: 13px; font-weight: 600; }
        .table-select-button button {
            margin-top: var(--space-1);
            border: 0;
            background: transparent;
            color: var(--primary);
            font-size: 13px;
            font-weight: 600;
            text-align: left;
        }
        .empty-state {
            padding: 40px var(--space-3);
            border: 1px dashed #D0D5DD;
            border-radius: var(--radius);
            background: #FFFFFF;
            text-align: center;
        }
        .empty-state__icon { font-size: 42px; line-height: 1; }
        .empty-state__title { margin-top: var(--space-2); color: #2B2B2B; font-size: 18px; font-weight: 700; }
        .empty-state__description { margin-top: var(--space-1); color: #6B7280; font-size: 13px; }
        .order-card {
            display: grid;
            grid-template-columns: 1.3fr 0.8fr 0.7fr 1fr 0.9fr auto;
            align-items: center;
            gap: var(--space-2);
            margin-bottom: var(--space-1);
            padding: var(--space-2);
            border-radius: var(--radius);
            background: #FFFFFF;
            box-shadow: var(--shadow);
        }
        .order-card__label { color: #6B7280; font-size: 12px; }
        .order-card__value { margin-top: 0; color: #2B2B2B; font-size: 14px; font-weight: 600; }
        .status-badge {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            padding: var(--space-1) var(--space-2);
            border-radius: 999px;
            font-size: 12px;
            font-weight: 600;
            white-space: nowrap;
        }
        .status-badge--new { color: #8A4200; background: #FFF4E6; }
        .status-badge--cooking { color: #7A5200; background: #FFF9DB; }
        .status-badge--ready { color: #1B6E2E; background: #EBFBEE; }
        .status-badge--paid { color: #1C5D99; background: #E7F5FF; }
        .best-seller {
            margin-bottom: var(--space-1);
            padding: var(--space-2);
            border-radius: 12px;
            background: #FFFFFF;
            box-shadow: var(--shadow);
        }
        .best-seller__line { display: flex; justify-content: space-between; gap: var(--space-1); color: #2B2B2B; font-size: 13px; font-weight: 600; }
        .best-seller__bar { height: 7px; margin-top: 8px; overflow: hidden; border-radius: 999px; background: #F1F3F5; }
        .best-seller__fill { height: 100%; border-radius: inherit; background: var(--primary); }
        .dashboard-date { color: #6B7280; font-size: 13px; }
        .alert-banner {
            display: flex;
            align-items: center;
            gap: var(--space-1);
            margin: var(--space-1) 0 var(--space-2);
            padding: var(--space-1) var(--space-2);
            border: 1px solid #FFEC99;
            border-radius: 10px;
            background: #FFF9DB;
            color: #7A5200;
            font-size: 13px;
            font-weight: 500;
        }
        @media (max-width: 768px) {
            [data-testid="stAppViewContainer"] .block-container {
                padding: var(--space-2);
            }
            [data-testid="stHorizontalBlock"]:has(.stButton) {
                flex-wrap: wrap;
                gap: var(--space-1);
            }
            [data-testid="stHorizontalBlock"]:has(.stButton) > [data-testid="stColumn"] {
                flex: 1 1 calc(50% - 4px);
                min-width: calc(50% - 4px);
            }
            .order-card { grid-template-columns: repeat(2, 1fr); }
        }
        @media (max-width: 900px) {
            [data-testid="stHorizontalBlock"]:has(.kpi-card) {
                flex-wrap: wrap;
                gap: 1rem;
            }
            [data-testid="stHorizontalBlock"]:has(.kpi-card) > [data-testid="stColumn"] {
                flex: 0 0 calc(50% - 0.5rem);
                min-width: calc(50% - 0.5rem);
            }
            [data-testid="stHorizontalBlock"]:has(.table-card) {
                flex-wrap: wrap;
                gap: 1rem;
            }
            [data-testid="stHorizontalBlock"]:has(.table-card) > [data-testid="stColumn"] {
                flex: 0 0 calc(50% - 0.5rem);
                min-width: calc(50% - 0.5rem);
            }
        }
        .stButton > button, [data-testid="stFormSubmitButton"] > button {
            min-height: 44px;
            padding: var(--space-1) var(--space-2);
            border-radius: var(--radius);
            font-weight: 600;
        }
        [data-testid="stSidebar"] {
            background: #FFFFFF;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
