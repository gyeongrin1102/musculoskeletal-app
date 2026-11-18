import streamlit as st
from auth import require_admin, logout_button


st.title("🔐 관리자 로그인")

st.write(
    "관리자 대시보드, 결과보고서 및 QR 관리 기능을 "
    "사용하려면 관리자 인증이 필요합니다."
)

st.divider()

require_admin()

st.success("Supabase Auth 관리자 계정으로 로그인되어 있습니다.")
logout_button()
