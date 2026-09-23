import streamlit as st


st.title("🔐 관리자 로그인")

st.write(
    "관리자 대시보드, 결과보고서 및 QR 관리 기능을 "
    "사용하려면 관리자 인증이 필요합니다."
)

st.divider()


# 이미 로그인한 경우
if st.session_state.get(
    "admin_authenticated",
    False
):

    st.success(
        "현재 관리자 로그인 상태입니다."
    )

    if st.button(
        "🚪 로그아웃",
        width="stretch"
    ):

        st.session_state[
            "admin_authenticated"
        ] = False

        st.rerun()

    st.stop()


# 로그인 입력
password = st.text_input(
    "관리자 비밀번호",
    type="password",
    placeholder="관리자 비밀번호를 입력하세요."
)


if st.button(
    "로그인",
    type="primary",
    width="stretch"
):

    try:

        correct_password = (
            st.secrets[
                "ADMIN_PASSWORD"
            ]
        )

    except Exception:

        st.error(
            "관리자 비밀번호 설정을 "
            "불러올 수 없습니다."
        )

        st.stop()


    if password == correct_password:

        st.session_state[
            "admin_authenticated"
        ] = True

        st.success(
            "관리자 인증이 완료되었습니다."
        )

        st.rerun()


    else:

        st.error(
            "비밀번호가 올바르지 않습니다."
        )
