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
# 데이터 조회
# =========================================================

def load_table(table_name):

    try:

        response = (
            supabase
            .table(table_name)
            .select("*")
            .order(
                "created_at",
                desc=True
            )
            .execute()
        )

        return response.data or []

    except Exception as e:

        st.error(
            f"{table_name} 조회 오류: {e}"
        )

        return []


# =========================================================
# 삭제
# =========================================================

def delete_row(
    table_name,
    row_id
):

    try:

        (
            supabase
            .table(table_name)
            .delete()
            .eq(
                "id",
                int(row_id)
            )
            .execute()
        )

        return True, None

    except Exception as e:

        return False, str(e)


# =========================================================
# 페이지
# =========================================================

st.title(
    "🗑️ 관리자 데이터 관리"
)

logout_button()

st.warning(
    "삭제된 데이터는 이 화면에서 복구할 수 없습니다. "
    "삭제 대상과 내용을 반드시 확인한 후 진행하세요."
)

st.divider()


# =========================================================
# 탭
# =========================================================

survey_tab, reba_tab, improvement_tab = st.tabs(
    [
        "🩺 증상조사",
        "🤖 REBA 평가",
        "🔄 개선 전·후"
    ]
)


# =========================================================
# 1. 증상조사 삭제
# =========================================================

with survey_tab:

    st.subheader(
        "근골격계 증상조사 데이터 삭제"
    )


    survey_rows = load_table(
        "survey_results"
    )


    if not survey_rows:

        st.info(
            "저장된 증상조사 데이터가 없습니다."
        )

    else:

        survey_df = pd.DataFrame(
            survey_rows
        )


        display_cols = [
            col
            for col in [
                "id",
                "created_at",
                "name",
                "department",
                "current_work",
                "symptom_exists",
                "final_judgment"
            ]
            if col in survey_df.columns
        ]


        st.dataframe(
            survey_df[
                display_cols
            ],
            hide_index=True,
            width="stretch"
        )


        survey_options = {}


        for _, row in survey_df.iterrows():

            label = (
                f"#{row.get('id', '')} | "
                f"{row.get('name', '')} | "
                f"{row.get('department', '')} | "
                f"{row.get('final_judgment', '')}"
            )

            survey_options[
                label
            ] = row.get(
                "id"
            )


        selected_survey = st.selectbox(
            "삭제할 증상조사 응답 선택",
            list(
                survey_options.keys()
            ),
            key="delete_survey_select"
        )


        confirm_survey = st.checkbox(
            "선택한 증상조사 응답을 삭제하는 것에 동의합니다.",
            key="confirm_survey_delete"
        )


        if st.button(
            "🗑️ 증상조사 응답 삭제",
            type="primary",
            disabled=not confirm_survey,
            width="stretch"
        ):

            selected_id = (
                survey_options[
                    selected_survey
                ]
            )


            success, error = delete_row(
                "survey_results",
                selected_id
            )


            if success:

                st.success(
                    "✅ 증상조사 응답이 삭제되었습니다."
                )

                st.cache_data.clear()

                st.rerun()

            else:

                st.error(
                    f"삭제 오류: {error}"
                )


# =========================================================
# 2. REBA 평가 삭제
# =========================================================

with reba_tab:

    st.subheader(
        "REBA 평가결과 삭제"
    )


    reba_rows = load_table(
        "reba_results"
    )


    if not reba_rows:

        st.info(
            "저장된 REBA 평가결과가 없습니다."
        )

    else:

        reba_df = pd.DataFrame(
            reba_rows
        )


        display_cols = [
            col
            for col in [
                "id",
                "created_at",
                "worker",
                "department",
                "task_name",
                "final_reba",
                "risk_level"
            ]
            if col in reba_df.columns
        ]


        st.dataframe(
            reba_df[
                display_cols
            ],
            hide_index=True,
            width="stretch"
        )


        reba_options = {}


        for _, row in reba_df.iterrows():

            label = (
                f"#{row.get('id', '')} | "
                f"{row.get('worker', '')} | "
                f"{row.get('task_name', '')} | "
                f"REBA {row.get('final_reba', '')}"
            )

            reba_options[
                label
            ] = row.get(
                "id"
            )


        selected_reba = st.selectbox(
            "삭제할 REBA 평가 선택",
            list(
                reba_options.keys()
            ),
            key="delete_reba_select"
        )


        confirm_reba = st.checkbox(
            "선택한 REBA 평가를 삭제하는 것에 동의합니다.",
            key="confirm_reba_delete"
        )


        if st.button(
            "🗑️ REBA 평가 삭제",
            type="primary",
            disabled=not confirm_reba,
            width="stretch"
        ):

            selected_id = (
                reba_options[
                    selected_reba
                ]
            )


            success, error = delete_row(
                "reba_results",
                selected_id
            )


            if success:

                st.success(
                    "✅ REBA 평가결과가 삭제되었습니다."
                )

                st.cache_data.clear()

                st.rerun()

            else:

                st.error(
                    f"삭제 오류: {error}"
                )


# =========================================================
# 3. 개선 전후 이력 삭제
# =========================================================

with improvement_tab:

    st.subheader(
        "REBA 개선 전·후 비교이력 삭제"
    )


    improvement_rows = load_table(
        "reba_improvements"
    )


    if not improvement_rows:

        st.info(
            "저장된 개선 전·후 비교이력이 없습니다."
        )

    else:

        improvement_df = pd.DataFrame(
            improvement_rows
        )


        display_cols = [
            col
            for col in [
                "id",
                "created_at",
                "department",
                "task_name",
                "before_reba",
                "after_reba",
                "score_reduction",
                "improvement_action"
            ]
            if col in improvement_df.columns
        ]


        st.dataframe(
            improvement_df[
                display_cols
            ],
            hide_index=True,
            width="stretch"
        )


        improvement_options = {}


        for _, row in (
            improvement_df.iterrows()
        ):

            label = (
                f"#{row.get('id', '')} | "
                f"{row.get('task_name', '')} | "
                f"{row.get('before_reba', '')}"
                f" → "
                f"{row.get('after_reba', '')}"
            )

            improvement_options[
                label
            ] = row.get(
                "id"
            )


        selected_improvement = (
            st.selectbox(
                "삭제할 개선 전·후 이력 선택",
                list(
                    improvement_options.keys()
                ),
                key="delete_improvement_select"
            )
        )


        confirm_improvement = (
            st.checkbox(
                "선택한 개선 전·후 이력을 삭제하는 것에 동의합니다.",
                key="confirm_improvement_delete"
            )
        )


        if st.button(
            "🗑️ 개선 전·후 이력 삭제",
            type="primary",
            disabled=(
                not confirm_improvement
            ),
            width="stretch"
        ):

            selected_id = (
                improvement_options[
                    selected_improvement
                ]
            )


            success, error = delete_row(
                "reba_improvements",
                selected_id
            )


            if success:

                st.success(
                    "✅ 개선 전·후 비교이력이 삭제되었습니다."
                )

                st.cache_data.clear()

                st.rerun()

            else:

                st.error(
                    f"삭제 오류: {error}"
                )
