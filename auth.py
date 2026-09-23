import streamlit as st


def is_admin():
    return st.session_state.get(
        "admin_authenticated",
        False
    )


def require_admin():

    if is_admin():
        return True

    st.title("🔐 관리자 로그인")

    st.write(
        "이 페이지는 관리자 전용입니다."
    )

    st.divider()

    password = st.text_input(
        "관리자 비밀번호",
        type="password",
        placeholder="비밀번호를 입력하세요."
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

    st.stop()


def logout_button():

    if is_admin():

        if st.button(
            "🚪 관리자 로그아웃"
        ):

            st.session_state[
                "admin_authenticated"
            ] = False

            st.rerun()
