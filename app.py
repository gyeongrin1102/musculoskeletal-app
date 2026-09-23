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


# =========================================================
# 근로자 설문
# =========================================================

survey_page = st.Page(
    "views/survey.py",
    title="근골격계 증상조사",
    icon="🩺",
    default=True
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
# 관리자 기능
# 현재 실제 GitHub 경로 기준
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


# =========================================================
# 로그인 여부에 따른 메뉴
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
            login_page
        ]
    }


else:

    pages = {
        "근로자": [
            survey_page
        ],

        "관리자": [
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
