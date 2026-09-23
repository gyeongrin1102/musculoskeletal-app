import pandas as pd
import streamlit as st

from supabase import create_client
from auth import require_admin, logout_button


# =========================================================
# 관리자 인증
# =========================================================

require_admin()


# =========================================================
# Supabase 연결
# =========================================================

@st.cache_resource
def get_supabase():

    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_KEY"]
    )


supabase = get_supabase()


# =========================================================
# 데이터 불러오기
# =========================================================

@st.cache_data(ttl=30)
def load_reba_results():

    response = (
        supabase
        .table("reba_results")
        .select("*")
        .order(
            "created_at",
            desc=True
        )
        .execute()
    )

    return response.data or []


@st.cache_data(ttl=30)
def load_improvements():

    response = (
        supabase
        .table("reba_improvements")
        .select("*")
        .order(
            "created_at",
            desc=True
        )
        .execute()
    )

    return response.data or []


# =========================================================
# 위험수준 함수
# =========================================================

def classify_reba(score):

    if score <= 1:
        return "무시 가능"

    elif score <= 3:
        return "낮음"

    elif score <= 7:
        return "중간"

    elif score <= 10:
        return "높음"

    else:
        return "매우 높음"


# =========================================================
# 페이지
# =========================================================

st.title(
    "🔄 REBA 개선 전·후 비교"
)

logout_button()

st.write(
    "저장된 REBA 평가결과를 이용하여 "
    "작업개선 전·후 위험도 변화를 비교하고 "
    "개선효과를 기록합니다."
)

st.divider()


# =========================================================
# 데이터 로딩
# =========================================================

try:

    reba_rows = load_reba_results()

except Exception as e:

    st.error(
        f"REBA 평가 데이터 조회 오류: {e}"
    )

    st.stop()


if not reba_rows:

    st.warning(
        "저장된 REBA 평가결과가 없습니다."
    )

    st.stop()


reba_df = pd.DataFrame(
    reba_rows
)


# =========================================================
# 개선 전 평가 선택
# =========================================================

st.subheader(
    "1. 개선 전 평가 선택"
)


before_options = []


for _, row in reba_df.iterrows():

    label = (
        f"#{row.get('id', '')} | "
        f"{row.get('department', '')} | "
        f"{row.get('task_name', '')} | "
        f"REBA {row.get('final_reba', '')}"
    )

    before_options.append(
        label
    )


selected_before = st.selectbox(
    "개선 전 REBA 평가",
    before_options
)


before_index = (
    before_options.index(
        selected_before
    )
)


before_row = (
    reba_df.iloc[
        before_index
    ]
)


before_reba = int(
    before_row.get(
        "final_reba",
        0
    )
)


before_risk = str(
    before_row.get(
        "risk_level",
        classify_reba(
            before_reba
        )
    )
)


b1, b2, b3 = st.columns(
    3
)


with b1:

    st.metric(
        "개선 전 REBA",
        before_reba
    )


with b2:

    st.metric(
        "위험수준",
        before_risk
    )


with b3:

    st.metric(
        "작업명",
        before_row.get(
            "task_name",
            "-"
        )
    )


st.write(
    f"**공종/부서:** "
    f"{before_row.get('department', '')}"
)

st.write(
    f"**작업자/대상자:** "
    f"{before_row.get('worker', '')}"
)


st.divider()


# =========================================================
# 개선조치
# =========================================================

st.subheader(
    "2. 개선조치 입력"
)


improvement_action = st.text_area(
    "실시한 개선조치",
    placeholder=(
        "예:\n"
        "- 작업높이 조정\n"
        "- 자재 위치 변경\n"
        "- 운반 보조도구 적용\n"
        "- 2인 1조 작업으로 변경"
    ),
    height=180
)


st.divider()


# =========================================================
# 개선 후 평가 선택
# =========================================================

st.subheader(
    "3. 개선 후 평가 선택"
)


after_options = []


for _, row in reba_df.iterrows():

    label = (
        f"#{row.get('id', '')} | "
        f"{row.get('department', '')} | "
        f"{row.get('task_name', '')} | "
        f"REBA {row.get('final_reba', '')}"
    )

    after_options.append(
        label
    )


selected_after = st.selectbox(
    "개선 후 REBA 평가",
    after_options
)


after_index = (
    after_options.index(
        selected_after
    )
)


after_row = (
    reba_df.iloc[
        after_index
    ]
)


after_reba = int(
    after_row.get(
        "final_reba",
        0
    )
)


after_risk = str(
    after_row.get(
        "risk_level",
        classify_reba(
            after_reba
        )
    )
)


a1, a2, a3 = st.columns(
    3
)


with a1:

    st.metric(
        "개선 후 REBA",
        after_reba
    )


with a2:

    st.metric(
        "위험수준",
        after_risk
    )


with a3:

    score_reduction = (
        before_reba
        - after_reba
    )

    st.metric(
        "점수 변화",
        (
            f"{score_reduction}점"
        )
    )


st.divider()


# =========================================================
# 개선효과 자동판정
# =========================================================

st.subheader(
    "4. 개선효과"
)


score_reduction = (
    before_reba
    - after_reba
)


if score_reduction > 0:

    result_text = (
        f"REBA 점수가 {before_reba}점에서 "
        f"{after_reba}점으로 "
        f"{score_reduction}점 감소했습니다."
    )

    st.success(
        result_text
    )


elif score_reduction == 0:

    result_text = (
        "개선 전·후 REBA 점수 변화가 없습니다."
    )

    st.warning(
        result_text
    )


else:

    result_text = (
        f"개선 후 REBA 점수가 "
        f"{abs(score_reduction)}점 증가했습니다. "
        "작업조건 및 개선조치를 재검토할 필요가 있습니다."
    )

    st.error(
        result_text
    )


comparison_df = pd.DataFrame(
    {
        "구분": [
            "개선 전",
            "개선 후"
        ],

        "REBA 점수": [
            before_reba,
            after_reba
        ],

        "위험수준": [
            before_risk,
            after_risk
        ]
    }
)


st.dataframe(
    comparison_df,
    hide_index=True,
    width="stretch"
)


st.bar_chart(
    comparison_df.set_index(
        "구분"
    )[
        "REBA 점수"
    ]
)


st.divider()


# =========================================================
# 저장
# =========================================================

st.subheader(
    "5. 개선결과 저장"
)


same_task = (
    str(
        before_row.get(
            "task_name",
            ""
        )
    ).strip()
    ==
    str(
        after_row.get(
            "task_name",
            ""
        )
    ).strip()
)


if not same_task:

    st.warning(
        "개선 전·후 작업명이 서로 다릅니다. "
        "동일 작업의 개선 전·후 평가인지 확인해주세요."
    )


save_disabled = (
    not improvement_action.strip()
)


if st.button(
    "💾 개선 전·후 비교 저장",
    type="primary",
    width="stretch",
    disabled=save_disabled
):

    try:

        insert_data = {

            "department":
                before_row.get(
                    "department",
                    ""
                ),

            "task_name":
                before_row.get(
                    "task_name",
                    ""
                ),

            "evaluator":
                after_row.get(
                    "evaluator",
                    ""
                )
                or
                before_row.get(
                    "evaluator",
                    ""
                ),

            "before_reba":
                before_reba,

            "before_risk_level":
                before_risk,

            "improvement_action":
                improvement_action,

            "after_reba":
                after_reba,

            "after_risk_level":
                after_risk,

            "score_reduction":
                score_reduction,

            "result_text":
                result_text
        }


        supabase.table(
            "reba_improvements"
        ).insert(
            insert_data
        ).execute()


        st.cache_data.clear()


        st.success(
            "✅ 개선 전·후 비교 결과가 저장되었습니다."
        )


    except Exception as e:

        st.error(
            f"저장 중 오류가 발생했습니다: {e}"
        )


st.divider()


# =========================================================
# 기존 개선이력
# =========================================================

st.subheader(
    "📋 개선 전·후 이력"
)


try:

    improvement_rows = (
        load_improvements()
    )


    if improvement_rows:

        improvement_df = (
            pd.DataFrame(
                improvement_rows
            )
        )


        display_columns = [
            c
            for c in [
                "created_at",
                "department",
                "task_name",
                "before_reba",
                "after_reba",
                "score_reduction",
                "before_risk_level",
                "after_risk_level",
                "improvement_action"
            ]
            if c
            in improvement_df.columns
        ]


        st.dataframe(
            improvement_df[
                display_columns
            ],
            hide_index=True,
            width="stretch"
        )


    else:

        st.info(
            "아직 저장된 개선 전·후 비교 이력이 없습니다."
        )


except Exception as e:

    st.error(
        f"개선이력 조회 오류: {e}"
    )
