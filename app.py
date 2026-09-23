import streamlit as st

from auth import is_admin


st.set_page_config(
    page_title="근골격계 증상조사",
    page_icon="🩺",
    layout="wide"
)


# =========================================================
# 페이지 정의
# =========================================================

survey_page = st.Page(
    "views/survey.py",
    title="근골격계 증상조사",
    icon="🩺",
    default=True
)

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
# 로그인 상태에 따른 메뉴
# =========================================================

if is_admin():

    pages = {
        "근로자": [
            survey_page
        ],
        "관리자": [
            admin_dashboard_page,
            report_page,
            qr_page
        ]
    }

else:

    pages = {
        "근로자": [
            survey_page
        ]
    }


# =========================================================
# 네비게이션 실행
# =========================================================

pg = st.navigation(
    pages
)

pg.run()
