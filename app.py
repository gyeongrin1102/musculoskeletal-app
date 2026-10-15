import streamlit as st

from auth import is_admin

# =========================================================
# 앱 설정
# =========================================================

st.set_page_config(
    page_title="근골격계 증상조사",
    page_icon="🩺",
    layout="wide"
)

admin_user = is_admin()

st.markdown(
    """
    <style>
    :root {
        --ehs-navy: #16384b;
        --ehs-navy-deep: #102d3d;
        --ehs-teal: #087f80;
        --ehs-teal-soft: #e4f2f1;
        --ehs-ink: #233844;
        --ehs-muted: #657985;
        --ehs-line: #d9e4e8;
        --ehs-canvas: #f4f8f9;
        --ehs-white: #ffffff;
    }
    [data-testid="stAppViewContainer"] { background: var(--ehs-canvas); color: var(--ehs-ink); }
    [data-testid="stHeader"] { background: rgba(244, 248, 249, 0.96); }
    .block-container {
        max-width: 1680px;
        padding: 1.5rem clamp(1rem, 2.4vw, 2.5rem) 3rem;
    }
    h1, h2, h3 { color: var(--ehs-navy); }
    h1 { font-size: 1.8rem; font-weight: 700; }
    h2, h3 { font-weight: 650; }
    [data-testid="stSidebar"] { background: var(--ehs-navy-deep); }
    [data-testid="stSidebar"] * { color: #f5fbfc; }
    [data-testid="stSidebarNav"] { padding-top: 0.4rem; }
    [data-testid="stSidebarNavLink"] {
        min-height: 2.7rem;
        margin: 4px 8px;
        padding: 0.45rem 0.75rem;
        border-radius: 6px;
        transition: background-color 120ms ease;
    }
    [data-testid="stSidebarNavLink"]:hover { background: rgba(255, 255, 255, 0.12); }
    [data-testid="stSidebarNavSectionHeader"] { padding: 0.9rem 1rem 0.35rem; }
    [data-testid="stSidebarNavLink"][aria-current="page"] {
        background: #d9eeec;
        border-left: 3px solid #39b5aa;
        font-weight: 700;
    }
    [data-testid="stSidebarNavLink"][aria-current="page"] * { color: var(--ehs-navy-deep); }
    .ehs-sidebar-brand {
        margin: 0.3rem 0 1rem;
        padding: 0.9rem 0.7rem;
        border-bottom: 1px solid rgba(255, 255, 255, 0.18);
        color: #ffffff;
        font-size: 1rem;
        font-weight: 700;
    }
    .ehs-sidebar-brand span {
        display: block;
        margin-top: 0.2rem;
        color: #a9d8d5;
        font-size: 0.76rem;
        font-weight: 400;
    }
    [data-testid="stMetric"] {
        background: var(--ehs-white);
        border: 1px solid var(--ehs-line);
        border-top: 3px solid var(--ehs-teal);
        border-radius: 6px;
        padding: 0.75rem 0.9rem;
    }
    [data-testid="stMetricLabel"],
    [data-testid="stMetricLabel"] p,
    [data-testid="stMetricValue"],
    [data-testid="stMetricValue"] div {
        color: var(--ehs-navy) !important;
    }
    [data-testid="stMetricLabel"] p { font-weight: 650; }
    [data-testid="stMetricValue"] { font-weight: 750; }
    [data-baseweb="tab-list"] { gap: 0.35rem; border-bottom: 1px solid var(--ehs-line); }
    [data-baseweb="tab"] { color: var(--ehs-navy); }
    [data-baseweb="tab-highlight"] { background: var(--ehs-teal); }
    [data-testid="stExpander"] { border: 1px solid var(--ehs-line); border-radius: 6px; }
    [data-testid="stDataFrame"], [data-testid="stTable"] {
        max-width: 100%;
        border: 1px solid var(--ehs-line);
        border-radius: 6px;
    }
    .stButton > button {
        min-height: 2.65rem;
        border: 1px solid #b9cbd1;
        border-radius: 6px;
        color: var(--ehs-navy);
        font-weight: 600;
    }
    .stButton > button[kind="primary"] {
        border-color: var(--ehs-teal);
        background: var(--ehs-teal);
        color: #ffffff;
    }
    .stButton > button:hover { border-color: var(--ehs-teal); color: var(--ehs-teal); }
    .stButton > button[kind="primary"]:hover { background: #076d6e; color: #ffffff; }
    input, textarea { border-radius: 5px !important; }
    [data-baseweb="select"] > div { border-radius: 5px; }
    [data-testid="stAlert"] { border-radius: 6px; }
    @media (max-width: 720px) {
        .block-container { padding: 1rem 0.75rem 2rem; }
        h1 { font-size: 1.45rem; }
        [data-testid="stHorizontalBlock"] { flex-wrap: wrap; gap: 0.6rem; }
        [data-testid="column"] { min-width: 100% !important; }
        [data-testid="stImage"] img { max-height: 64vh; object-fit: contain; }
        [data-testid="stDataFrame"] { max-width: 100%; overflow-x: auto; }
        .stButton > button { width: 100%; }
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.sidebar.markdown(
    '<div class="ehs-sidebar-brand">근골격계 EHS<span>현장 보건관리</span></div>',
    unsafe_allow_html=True
)


# =========================================================
# 근로자 페이지
# =========================================================

survey_page = st.Page(
    "views/survey.py",
    title="근골격계 증상조사",
    icon="🩺",
    default=not admin_user
)
worker_camera_page = st.Page(
    "views/worker_camera.py",
    title="작업자세 촬영",
    icon="📷"
)

# =========================================================
# 관리자 로그인
# =========================================================

login_page = st.Page(
    "views/admin_login.py",
    title="관리자 로그인",
    icon="🔐"
)


# =========================================================
# 관리자 페이지
# =========================================================

admin_dashboard_page = st.Page(
    "pages/views/admin_dashboard.py",
    title="관리자 대시보드",
    icon="📊",
    default=admin_user
)


report_page = st.Page(
    "pages/views/report.py",
    title="결과보고서",
    icon="📄"
)


qr_page = st.Page(
    "pages/views/qr.py",
    title="QR 배포",
    icon="📱"
)


ai_reba_page = st.Page(
    "pages/views/ai_reba.py",
    title="AI 자세·REBA 평가",
    icon="🤖"
)

capture_review_page = st.Page(
    "pages/views/capture_review.py",
    title="촬영 대기자료 검토",
    icon="📥"
)

reba_improvement_page = st.Page(
    "pages/views/reba_improvement.py",
    title="REBA 개선 전·후 비교",
    icon="🔄"
)
data_management_page = st.Page(
    "pages/views/data_management.py",
    title="데이터 관리",
    icon="🗑️"
)
hazard_report_page = st.Page(
    "pages/views/hazard_report.py",
    title="유해요인조사표 자동생성",
    icon="📋"
)


# =========================================================
# 메뉴 구성
# =========================================================

if admin_user:

    pages = {
        "현장 입력": [
            survey_page,
            worker_camera_page
        ],

        "REBA 검토": [
            capture_review_page,
            ai_reba_page,
            reba_improvement_page
        ],

        "현황 및 보고": [
            admin_dashboard_page,
            hazard_report_page,
            report_page
        ],

        "운영": [
            qr_page,
            data_management_page,
        ]
    }

else:

    pages = {
        "현장 입력": [
            survey_page,
            worker_camera_page
        ],

        "관리자 접속": [
            login_page
        ]
    }


# =========================================================
# 네비게이션 실행
# =========================================================

pg = st.navigation(
    pages,
    position="sidebar"
)

pg.run()
