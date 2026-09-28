import streamlit as st
import qrcode

from io import BytesIO

from auth import require_admin, logout_button


# =========================================================
# 관리자 인증
# =========================================================

require_admin()


# =========================================================
# 화면
# =========================================================

st.title("📱 근골격계 증상조사 QR 배포")

logout_button()

st.write(
    "근로자가 휴대전화로 QR코드를 촬영하면 "
    "근골격계 증상조사 웹페이지로 바로 접속할 수 있습니다."
)

st.divider()


# =========================================================
# 앱 URL 불러오기
# =========================================================

try:

    app_url = st.secrets["APP_URL"]

except Exception:

    app_url = ""


if not app_url:

    st.error(
        "APP_URL이 설정되지 않았습니다. "
        "Streamlit Secrets에 APP_URL을 등록해주세요."
    )

    st.stop()


# =========================================================
# 웹 주소 표시
# =========================================================

st.subheader("🌐 설문 웹주소")

st.code(
    app_url,
    language=None
)


st.link_button(
    "🌐 설문 웹에서 바로 열기",
    app_url,
    type="primary",
    width="stretch"
)


st.caption(
    "위 버튼을 누르면 실제 근로자용 설문 화면이 새 창에서 열립니다."
)

st.divider()


# =========================================================
# QR 생성
# =========================================================

st.subheader("📱 설문 QR코드")


qr = qrcode.QRCode(
    version=1,
    error_correction=qrcode.constants.ERROR_CORRECT_M,
    box_size=12,
    border=4
)

qr.add_data(
    app_url
)

qr.make(
    fit=True
)


qr_image = qr.make_image(
    fill_color="black",
    back_color="white"
)


buffer = BytesIO()

qr_image.save(
    buffer,
    format="PNG"
)

buffer.seek(0)


st.image(
    buffer,
    caption="근골격계 증상조사 QR코드",
    width=350
)


st.success(
    "휴대전화 카메라로 위 QR코드를 촬영하면 "
    "근골격계 증상조사 페이지가 열립니다."
)


# =========================================================
# QR 다운로드
# =========================================================

st.download_button(
    label="⬇️ QR코드 이미지 다운로드",
    data=buffer.getvalue(),
    file_name="근골격계_증상조사_QR.png",
    mime="image/png",
    width="stretch"
)


st.divider()


# =========================================================
# 사용방법
# =========================================================

st.subheader("사용방법")

st.write(
    """
    ① 근로자가 휴대전화 카메라로 QR코드를 촬영합니다.  
    ② 화면에 표시되는 링크를 누릅니다.  
    ③ 근골격계 증상조사를 작성합니다.  
    ④ 제출된 결과는 관리자 대시보드에서 확인할 수 있습니다.
    """
)
