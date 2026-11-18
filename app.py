"""근골격계 증상조사·유해요인조사 웹앱 진입점.

QR 코드(APP_URL)로 접속하면 근로자용 증상조사 화면이 바로 열립니다.
관리자 메뉴는 로그인 후에만 보입니다.
"""

import streamlit as st

from auth import is_admin

st.set_page_config(
    page_title="근골격계질환 증상조사",
    page_icon="🦴",
    layout="centered",
)

worker_pages = [
    st.Page("views/survey.py", title="증상조사 참여", icon="📝", default=True,
            url_path="survey"),
    st.Page("views/worker_camera.py", title="작업자세 촬영", icon="📷",
            url_path="camera"),
]

login_page = st.Page("views/admin_login.py", title="관리자 로그인", icon="🔐",
                     url_path="admin")

admin_pages = [
    st.Page("pages/views/admin_dashboard.py", title="대시보드", icon="📊",
            url_path="dashboard"),
    st.Page("pages/views/survey_print.py", title="증상조사표 출력·보관", icon="🖨️",
            url_path="survey-print"),
    st.Page("pages/views/qr.py", title="QR 배포", icon="📱", url_path="qr"),
    st.Page("pages/views/capture_review.py", title="촬영 대기자료 검토", icon="📥",
            url_path="capture-review"),
    st.Page("pages/views/ai_reba.py", title="AI 자세·REBA 평가", icon="🤖",
            url_path="ai-reba"),
    st.Page("pages/views/hazard_report.py", title="유해요인조사표", icon="📋",
            url_path="hazard-report"),
    st.Page("pages/views/reba_improvement.py", title="개선효과", icon="🛠️",
            url_path="improvement"),
    st.Page("pages/views/report.py", title="통합 결과보고서", icon="📄",
            url_path="report"),
    st.Page("pages/views/data_management.py", title="데이터 관리", icon="🗂️",
            url_path="data"),
]

if is_admin():
    pages = {"근로자": worker_pages, "관리자": [login_page] + admin_pages}
else:
    pages = {"근로자": worker_pages, "관리자": [login_page]}

st.navigation(pages).run()
