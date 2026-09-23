import streamlit as st

from auth import is_admin


st.set_page_config(
    page_title="근골격계 증상조사",
    page_icon="🩺",
    layout="wide"
)


# =========================================================
# 근로자
# =========================================================

survey_page = st.Page(
    "views/survey.py",
    title="근골격계 증상조사",
    icon="🩺",
    default=True
)


# =========================================================
# 로그인
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
    icon="📊"
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
reba_improvement_page = st.Page(
    "pages/views/reba_improvement.py",
    title="REBA 개선 전·후 비교",
    icon="🔄"
)


# =========================================================
# 메뉴 구성
# =========================================================

if is_admin():

    pages = {
        "근로자": [
            survey_page
        ],

        "관리자": [
            admin_dashboard_page,
            report_page,
            qr_page,
            ai_reba_page,
            reba_improvement_page,
            login_page
]

else:

    pages = {
        "근로자": [
            survey_page
        ],

        "관리자": [
            login_page
        ]
    }


pg = st.navigation(
    pages,
    position="sidebar"
)

pg.run()
