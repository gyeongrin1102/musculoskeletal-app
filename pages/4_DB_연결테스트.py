import streamlit as st
from supabase import create_client, Client


# =========================================================
# 페이지 설정
# =========================================================

st.set_page_config(
    page_title="DB 연결 테스트",
    page_icon="🗄️",
    layout="wide"
)

st.title("🗄️ Supabase DB 연결 테스트")

st.write(
    "Streamlit Cloud와 Supabase 데이터베이스가 "
    "정상적으로 연결되는지 확인합니다."
)

st.divider()


# =========================================================
# Supabase 연결
# =========================================================

try:

    supabase_url = st.secrets["SUPABASE_URL"]
    supabase_key = st.secrets["SUPABASE_KEY"]

    supabase: Client = create_client(
        supabase_url,
        supabase_key
    )

    st.success("Supabase 연결정보를 정상적으로 불러왔습니다.")

except Exception as e:

    st.error(
        f"Supabase 연결정보를 불러오지 못했습니다: {e}"
    )

    st.stop()


# =========================================================
# 테스트 데이터 입력
# =========================================================

st.subheader("1. 테스트 데이터 저장")

test_name = st.text_input(
    "테스트 성명",
    value="테스트 근로자"
)

test_department = st.text_input(
    "테스트 부서",
    value="테스트부서"
)

test_work = st.text_input(
    "테스트 작업",
    value="테스트작업"
)


if st.button(
    "테스트 데이터 저장",
    type="primary"
):

    test_data = {
        "name": test_name,
        "gender": "테스트",
        "age": 30,
        "marriage": "테스트",
        "department": test_department,
        "sub_department": "",
        "current_work": test_work,
        "symptom_exists": "아니오",
        "final_judgment": "정상",

        "survey_data": {
            "테스트여부": "예",
            "목_증상여부": "아니오",
            "허리_증상여부": "아니오"
        }
    }

    try:

        response = (
            supabase
            .table("survey_results")
            .insert(test_data)
            .execute()
        )

        st.success(
            "테스트 데이터가 Supabase에 저장되었습니다."
        )

        st.write(response.data)

    except Exception as e:

        st.error(
            f"저장 중 오류가 발생했습니다: {e}"
        )


st.divider()


# =========================================================
# 데이터 조회
# =========================================================

st.subheader("2. 저장된 데이터 조회")


if st.button(
    "DB 데이터 불러오기"
):

    try:

        response = (
            supabase
            .table("survey_results")
            .select("*")
            .order(
                "created_at",
                desc=True
            )
            .execute()
        )

        data = response.data

        if len(data) == 0:

            st.info(
                "아직 저장된 데이터가 없습니다."
            )

        else:

            st.success(
                f"총 {len(data)}건의 데이터를 불러왔습니다."
            )

            st.dataframe(
                data,
                use_container_width=True
            )

    except Exception as e:

        st.error(
            f"조회 중 오류가 발생했습니다: {e}"
        )