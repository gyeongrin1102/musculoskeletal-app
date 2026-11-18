import streamlit as st
from supabase import create_client


ACCESS_TOKEN_KEY = "supabase_access_token"
REFRESH_TOKEN_KEY = "supabase_refresh_token"


def _new_supabase_client():
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_KEY"]
    )


def _is_admin_user(user):
    app_metadata = getattr(user, "app_metadata", None) or {}
    return app_metadata.get("role") == "admin"


def _clear_admin_session():
    for key in (
        "admin_authenticated",
        ACCESS_TOKEN_KEY,
        REFRESH_TOKEN_KEY,
    ):
        st.session_state.pop(key, None)


def is_admin():
    return bool(
        st.session_state.get("admin_authenticated")
        and st.session_state.get(ACCESS_TOKEN_KEY)
        and st.session_state.get(REFRESH_TOKEN_KEY)
    )


def _login(email, password):
    try:
        client = _new_supabase_client()
        response = client.auth.sign_in_with_password(
            {
                "email": email.strip(),
                "password": password,
            }
        )
    except Exception:
        st.error("로그인에 실패했습니다. 계정과 인증 설정을 확인해주세요.")
        return False

    session = getattr(response, "session", None)
    user = getattr(response, "user", None)

    if not session or not user:
        st.error("인증 세션을 만들지 못했습니다.")
        return False

    if not _is_admin_user(user):
        try:
            client.auth.sign_out()
        except Exception:
            pass
        st.error("관리자 권한이 지정된 계정만 로그인할 수 있습니다.")
        return False

    st.session_state[ACCESS_TOKEN_KEY] = session.access_token
    st.session_state[REFRESH_TOKEN_KEY] = session.refresh_token
    st.session_state["admin_authenticated"] = True
    return True


def _render_login_form():
    with st.form("supabase_admin_login"):
        email = st.text_input(
            "관리자 이메일",
            key="supabase_admin_email"
        )
        password = st.text_input(
            "비밀번호",
            type="password",
            key="supabase_admin_password"
        )
        submitted = st.form_submit_button(
            "로그인",
            type="primary",
            width="stretch"
        )

    if submitted:
        if not email.strip() or not password:
            st.error("이메일과 비밀번호를 입력해주세요.")
        elif _login(email, password):
            st.rerun()


def require_admin():
    if is_admin():
        return True

    st.title("관리자 로그인")
    st.write("관리자 계정으로 인증해주세요.")
    _render_login_form()
    st.stop()


def get_authenticated_supabase():
    if not is_admin():
        st.error("관리자 인증이 필요합니다.")
        st.stop()

    client = _new_supabase_client()

    try:
        response = client.auth.set_session(
            st.session_state[ACCESS_TOKEN_KEY],
            st.session_state[REFRESH_TOKEN_KEY]
        )
    except Exception:
        _clear_admin_session()
        st.error("관리자 세션이 만료되었습니다. 다시 로그인해주세요.")
        st.stop()

    session = getattr(response, "session", None)
    user = getattr(response, "user", None)

    if not session or not user or not _is_admin_user(user):
        _clear_admin_session()
        st.error("관리자 권한을 확인할 수 없습니다. 다시 로그인해주세요.")
        st.stop()

    st.session_state[ACCESS_TOKEN_KEY] = session.access_token
    st.session_state[REFRESH_TOKEN_KEY] = session.refresh_token
    return client


def logout_button():
    if not is_admin():
        return

    if st.button("관리자 로그아웃"):
        try:
            client = _new_supabase_client()
            client.auth.set_session(
                st.session_state[ACCESS_TOKEN_KEY],
                st.session_state[REFRESH_TOKEN_KEY]
            )
            client.auth.sign_out()
        except Exception:
            pass

        _clear_admin_session()
        st.rerun()