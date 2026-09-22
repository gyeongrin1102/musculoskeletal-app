import streamlit as st
import qrcode

from io import BytesIO


# =========================================================
# 페이지 설정
# =========================================================

st.set_page_config(
    page_title="QR 설문 배포",
    page_icon="📱",
    layout="wide"
)


st.title("📱 근골격계 증상조사 QR 배포")

st.write(
    "근로자가 휴대폰으로 QR 코드를 촬영하여 "
    "증상조사 페이지에 바로 접속할 수 있습니다."
)

st.divider()


# =========================================================
# 설문 주소
# =========================================================

DEFAULT_URL = (
    "https://musculoskeletal-app-p9jcorltqgyt7epu7oscwy.streamlit.app"
)


survey_url = st.text_input(
    "설문조사 주소",
    value=DEFAULT_URL,
    help="근로자가 접속할 실제 설문조사 주소입니다."
)


st.caption(
    "※ 향후 앱 주소가 변경되면 위 주소만 수정하면 됩니다."
)


# =========================================================
# QR 생성 함수
# =========================================================

def create_qr(url):

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4
    )

    qr.add_data(url)

    qr.make(
        fit=True
    )

    img = qr.make_image(
        fill_color="black",
        back_color="white"
    )

    output = BytesIO()

    img.save(
        output,
        format="PNG"
    )

    output.seek(0)

    return output


# =========================================================
# QR 출력
# =========================================================

if survey_url.strip() == "":

    st.warning(
        "설문조사 주소를 입력해 주세요."
    )

else:

    qr_image = create_qr(
        survey_url
    )

    st.divider()

    st.subheader(
        "설문 참여 QR 코드"
    )

    col1, col2 = st.columns(
        [1, 2]
    )


    with col1:

        st.image(
            qr_image,
            width=320
        )


    with col2:

        st.markdown(
            """
            ### 이용 방법

            1. 휴대폰 카메라를 실행합니다.  
            2. QR 코드를 비춥니다.  
            3. 화면에 나타나는 링크를 누릅니다.  
            4. 근골격계 증상조사를 작성합니다.  
            5. 마지막의 **조사 제출** 버튼을 누릅니다.
            """
        )

        st.info(
            "QR 코드는 근로자 설문 참여용으로 사용할 수 있습니다."
        )


    # =====================================================
    # QR 다운로드
    # =====================================================

    qr_image.seek(0)

    st.download_button(
        label="📥 QR 코드 PNG 다운로드",
        data=qr_image,
        file_name="근골격계_증상조사_QR.png",
        mime="image/png",
        width="stretch"
    )


    st.divider()


    # =====================================================
    # 게시용 안내문
    # =====================================================

    st.subheader(
        "현장 게시용 안내문"
    )

    guide_text = f"""
근골격계 증상조사 참여 안내

근로자의 근골격계 증상 및 작업 관련 특성을 확인하기 위한 조사입니다.

■ 참여방법
1. 휴대폰 카메라로 QR 코드를 촬영합니다.
2. 설문 페이지에 접속합니다.
3. 문항에 응답합니다.
4. 조사 제출 버튼을 누릅니다.

설문주소:
{survey_url}
"""


    st.text_area(
        "안내문 문구",
        value=guide_text,
        height=250
    )