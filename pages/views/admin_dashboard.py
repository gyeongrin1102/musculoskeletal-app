import streamlit as st
import pandas as pd

from io import BytesIO
from supabase import create_client
from auth import require_admin, logout_button


# =========================================================
# 페이지 설정
# =========================================================



require_admin()

st.title("📊 근골격계 증상조사 관리자 대시보드")

logout_button()

st.write(
    "Supabase 데이터베이스에 저장된 근골격계 증상조사 결과를 "
    "자동으로 분석합니다."
)

st.divider()


# =========================================================
# Supabase 연결
# =========================================================

try:

    supabase_url = st.secrets["SUPABASE_URL"]
    supabase_key = st.secrets["SUPABASE_KEY"]

    supabase = create_client(
        supabase_url,
        supabase_key
    )

except Exception as e:

    st.error(
        f"Supabase 연결정보를 불러오지 못했습니다: {e}"
    )

    st.stop()


# =========================================================
# DB 데이터 불러오기
# =========================================================

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

    db_rows = response.data

except Exception as e:

    st.error(
        f"데이터베이스 조회 중 오류가 발생했습니다: {e}"
    )

    st.stop()


if not db_rows:

    st.info(
        "아직 저장된 근골격계 증상조사 결과가 없습니다."
    )

    st.stop()


# =========================================================
# Supabase 데이터를 기존 설문 형식으로 변환
# =========================================================

converted_rows = []


for db_row in db_rows:

    survey_data = db_row.get(
        "survey_data",
        {}
    )

    if not isinstance(
        survey_data,
        dict
    ):
        survey_data = {}


    row = survey_data.copy()


    # -----------------------------------------------------
    # DB 기본 필드 → 기존 한글 컬럼명
    # -----------------------------------------------------

    row["DB_ID"] = db_row.get(
        "id",
        ""
    )

    row["제출일시"] = db_row.get(
        "created_at",
        row.get(
            "제출일시",
            ""
        )
    )

    row["성명"] = db_row.get(
        "name",
        row.get(
            "성명",
            ""
        )
    )

    row["성별"] = db_row.get(
        "gender",
        row.get(
            "성별",
            ""
        )
    )

    row["연령"] = db_row.get(
        "age",
        row.get(
            "연령",
            ""
        )
    )

    row["결혼여부"] = db_row.get(
        "marriage",
        row.get(
            "결혼여부",
            ""
        )
    )

    row["작업부서"] = db_row.get(
        "department",
        row.get(
            "작업부서",
            ""
        )
    )

    row["라인/세부부서"] = db_row.get(
        "sub_department",
        row.get(
            "라인/세부부서",
            ""
        )
    )

    row["현재작업"] = db_row.get(
        "current_work",
        row.get(
            "현재작업",
            ""
        )
    )

    row["근골격계증상여부"] = db_row.get(
        "symptom_exists",
        row.get(
            "근골격계증상여부",
            ""
        )
    )

    row["최종판정"] = db_row.get(
        "final_judgment",
        row.get(
            "최종판정",
            ""
        )
    )


    converted_rows.append(
        row
    )


df = pd.DataFrame(
    converted_rows
)


# =========================================================
# 기본 정리
# =========================================================

body_parts = [
    "목",
    "어깨",
    "팔/팔꿈치",
    "손/손목/손가락",
    "허리",
    "다리/발"
]


if "최종판정" not in df.columns:
    df["최종판정"] = ""


if "근골격계증상여부" not in df.columns:
    df["근골격계증상여부"] = ""


if "작업부서" not in df.columns:
    df["작업부서"] = ""


if "성명" not in df.columns:
    df["성명"] = ""


# =========================================================
# 데이터 새로고침
# =========================================================

col_refresh1, col_refresh2 = st.columns(
    [1, 5]
)

with col_refresh1:

    if st.button(
        "🔄 데이터 새로고침"
    ):

        st.rerun()


with col_refresh2:

    st.caption(
        f"현재 DB에서 총 {len(df)}건을 불러왔습니다."
    )


st.divider()


# =========================================================
# 조사 현황
# =========================================================

st.subheader("조사 현황")


total_count = len(df)


symptom_count = (
    df["근골격계증상여부"]
    .fillna("")
    .astype(str)
    .str.strip()
    .eq("예")
    .sum()
)


symptom_rate = (
    symptom_count
    / total_count
    * 100
    if total_count > 0
    else 0
)


normal_count = (
    df["최종판정"]
    .fillna("")
    .astype(str)
    .str.strip()
    .eq("정상")
    .sum()
)


manage_count = (
    df["최종판정"]
    .fillna("")
    .astype(str)
    .str.strip()
    .eq("관리대상자")
    .sum()
)


pain_count = (
    df["최종판정"]
    .fillna("")
    .astype(str)
    .str.strip()
    .eq("통증호소자")
    .sum()
)


col1, col2, col3 = st.columns(3)


with col1:

    st.metric(
        "총 응답자",
        f"{total_count}명"
    )


with col2:

    st.metric(
        "증상 경험자",
        f"{symptom_count}명"
    )


with col3:

    st.metric(
        "증상 경험률",
        f"{symptom_rate:.1f}%"
    )


st.write("")


col4, col5, col6 = st.columns(3)


with col4:

    st.metric(
        "정상",
        f"{normal_count}명"
    )


with col5:

    st.metric(
        "관리대상자",
        f"{manage_count}명"
    )


with col6:

    st.metric(
        "통증호소자",
        f"{pain_count}명"
    )


st.divider()


# =========================================================
# 조사 결과 검색
# =========================================================

st.subheader("🔎 조사 결과 검색")


department_list = (
    df["작업부서"]
    .dropna()
    .astype(str)
    .str.strip()
)

department_list = (
    department_list[
        department_list != ""
    ]
    .unique()
    .tolist()
)


col1, col2, col3 = st.columns(3)


with col1:

    selected_department = st.selectbox(
        "부서",
        [
            "전체"
        ]
        + department_list
    )


with col2:

    selected_judgment = st.selectbox(
        "최종판정",
        [
            "전체",
            "정상",
            "관리대상자",
            "통증호소자"
        ]
    )


with col3:

    search_name = st.text_input(
        "성명 검색",
        placeholder="예: 홍길동"
    )


filtered_df = df.copy()


if selected_department != "전체":

    filtered_df = filtered_df[
        filtered_df[
            "작업부서"
        ]
        == selected_department
    ]


if selected_judgment != "전체":

    filtered_df = filtered_df[
        filtered_df[
            "최종판정"
        ]
        == selected_judgment
    ]


if search_name.strip():

    filtered_df = filtered_df[
        filtered_df[
            "성명"
        ]
        .astype(str)
        .str.contains(
            search_name,
            case=False,
            na=False
        )
    ]


st.write(
    f"검색 결과: **{len(filtered_df)}명**"
)


# =========================================================
# 전체 응답 데이터
# =========================================================

st.subheader("전체 응답 데이터")


preferred_columns = [
    "제출일시",
    "성명",
    "성별",
    "연령",
    "결혼여부",
    "작업부서",
    "라인/세부부서",
    "현재작업",
    "근골격계증상여부",
    "최종판정"
]


display_columns = [
    col
    for col in preferred_columns
    if col in filtered_df.columns
]


if display_columns:

    st.dataframe(
        filtered_df[
            display_columns
        ],
        width="stretch",
        hide_index=True
    )

else:

    st.dataframe(
        filtered_df,
        width="stretch",
        hide_index=True
    )


st.divider()


# =========================================================
# 신체부위별 증상자 현황
# =========================================================

st.subheader("신체부위별 증상자 현황")


symptom_summary = []


for part in body_parts:

    symptom_col = (
        f"{part}_증상여부"
    )

    if symptom_col in df.columns:

        count = (
            df[symptom_col]
            .fillna("")
            .astype(str)
            .str.strip()
            .eq("예")
            .sum()
        )

    else:

        count = 0


    rate = (
        count
        / total_count
        * 100
        if total_count > 0
        else 0
    )


    symptom_summary.append({
        "신체부위": part,
        "증상자수": int(count),
        "증상률(%)": round(
            rate,
            1
        )
    })


symptom_summary_df = pd.DataFrame(
    symptom_summary
)


st.dataframe(
    symptom_summary_df,
    width="stretch",
    hide_index=True
)


symptom_chart_df = (
    symptom_summary_df[
        [
            "신체부위",
            "증상자수"
        ]
    ]
    .set_index(
        "신체부위"
    )
)


st.bar_chart(
    symptom_chart_df
)


st.divider()


# =========================================================
# 신체부위별 판정 현황
# =========================================================

st.subheader("신체부위별 판정 현황")


part_summary = []


for part in body_parts:

    judgment_col = (
        f"{part}_판정"
    )


    if judgment_col in df.columns:

        series = (
            df[judgment_col]
            .fillna("")
            .astype(str)
            .str.strip()
        )


        normal = (
            series
            == "정상"
        ).sum()


        manage = (
            series
            == "관리대상자"
        ).sum()


        pain = (
            series
            == "통증호소자"
        ).sum()


    else:

        normal = 0
        manage = 0
        pain = 0


    abnormal = (
        manage
        + pain
    )


    abnormal_rate = (
        abnormal
        / total_count
        * 100
        if total_count > 0
        else 0
    )


    part_summary.append({
        "신체부위": part,
        "정상": int(normal),
        "관리대상자": int(manage),
        "통증호소자": int(pain),
        "유소견계": int(abnormal),
        "유소견율(%)": round(
            abnormal_rate,
            1
        )
    })


part_summary_df = pd.DataFrame(
    part_summary
)


st.dataframe(
    part_summary_df,
    width="stretch",
    hide_index=True
)


chart_df = (
    part_summary_df[
        [
            "신체부위",
            "관리대상자",
            "통증호소자"
        ]
    ]
    .set_index(
        "신체부위"
    )
)


st.bar_chart(
    chart_df
)


st.divider()


# =========================================================
# 부서별 판정 현황
# =========================================================

st.subheader("부서별 판정 현황")


department_df = df[
    df["작업부서"]
    .notna()
].copy()


department_df = department_df[
    department_df[
        "작업부서"
    ]
    .astype(str)
    .str.strip()
    != ""
]


department_summary = []


for dept in (
    department_df[
        "작업부서"
    ]
    .unique()
):

    dept_data = (
        department_df[
            department_df[
                "작업부서"
            ]
            == dept
        ]
    )


    dept_total = len(
        dept_data
    )


    normal = (
        dept_data[
            "최종판정"
        ]
        == "정상"
    ).sum()


    manage = (
        dept_data[
            "최종판정"
        ]
        == "관리대상자"
    ).sum()


    pain = (
        dept_data[
            "최종판정"
        ]
        == "통증호소자"
    ).sum()


    abnormal = (
        manage
        + pain
    )


    abnormal_rate = (
        abnormal
        / dept_total
        * 100
        if dept_total > 0
        else 0
    )


    department_summary.append({
        "부서": dept,
        "응답자수": int(
            dept_total
        ),
        "정상": int(
            normal
        ),
        "관리대상자": int(
            manage
        ),
        "통증호소자": int(
            pain
        ),
        "유소견계": int(
            abnormal
        ),
        "유소견율(%)": round(
            abnormal_rate,
            1
        )
    })


department_summary_df = pd.DataFrame(
    department_summary
)


if len(
    department_summary_df
) > 0:

    department_summary_df = (
        department_summary_df
        .sort_values(
            by="유소견율(%)",
            ascending=False
        )
        .reset_index(
            drop=True
        )
    )


    st.dataframe(
        department_summary_df,
        width="stretch",
        hide_index=True
    )


    department_chart_df = (
        department_summary_df[
            [
                "부서",
                "정상",
                "관리대상자",
                "통증호소자"
            ]
        ]
        .set_index(
            "부서"
        )
    )


    st.bar_chart(
        department_chart_df
    )


else:

    st.info(
        "부서별 분석 가능한 데이터가 없습니다."
    )


st.divider()


# =========================================================
# 관리 대상 근로자 명단
# =========================================================

st.subheader("관리 대상 근로자 명단")


target_df = df[
    df[
        "최종판정"
    ]
    .isin(
        [
            "관리대상자",
            "통증호소자"
        ]
    )
].copy()


if len(
    target_df
) == 0:

    st.success(
        "현재 관리대상자 또는 통증호소자가 없습니다."
    )


else:

    target_detail = []


    for _, row in (
        target_df
        .iterrows()
    ):

        abnormal_parts = []


        for part in body_parts:

            judgment = row.get(
                f"{part}_판정",
                ""
            )


            if judgment in [
                "관리대상자",
                "통증호소자"
            ]:

                abnormal_parts.append(
                    f"{part}"
                    f"({judgment})"
                )


        target_detail.append({
            "성명": row.get(
                "성명",
                ""
            ),
            "부서": row.get(
                "작업부서",
                ""
            ),
            "현재작업": row.get(
                "현재작업",
                ""
            ),
            "증상부위": ", ".join(
                abnormal_parts
            ),
            "최종판정": row.get(
                "최종판정",
                ""
            )
        })


    target_detail_df = pd.DataFrame(
        target_detail
    )


    st.dataframe(
        target_detail_df,
        width="stretch",
        hide_index=True
    )


st.divider()


# =========================================================
# 개인별 상세조회
# =========================================================

st.subheader("개인별 상세조회")


name_options = (
    df["성명"]
    .dropna()
    .astype(str)
)


name_options = (
    name_options[
        name_options
        .str.strip()
        != ""
    ]
    .tolist()
)


if len(
    name_options
) == 0:

    st.info(
        "조회할 근로자 데이터가 없습니다."
    )


else:

    selected_name = st.selectbox(
        "근로자를 선택하세요.",
        name_options
    )


    selected_rows = df[
        df[
            "성명"
        ]
        .astype(str)
        == selected_name
    ]


    if len(
        selected_rows
    ) > 0:

        row = (
            selected_rows
            .iloc[0]
        )


        col1, col2, col3 = (
            st.columns(3)
        )


        with col1:

            st.write(
                "**성명**"
            )

            st.write(
                row.get(
                    "성명",
                    ""
                )
            )


        with col2:

            st.write(
                "**부서**"
            )

            st.write(
                row.get(
                    "작업부서",
                    ""
                )
            )


        with col3:

            st.write(
                "**최종판정**"
            )

            st.write(
                row.get(
                    "최종판정",
                    ""
                )
            )


        st.write(
            "**현재 작업**"
        )

        st.write(
            row.get(
                "현재작업",
                ""
            )
        )


        st.write(
            "### 신체부위별 판정"
        )


        detail_data = []


        for part in body_parts:

            detail_data.append({
                "신체부위": part,
                "판정": row.get(
                    f"{part}_판정",
                    "정상"
                ),
                "지속기간": row.get(
                    f"{part}_지속기간",
                    ""
                ),
                "증상정도": row.get(
                    f"{part}_증상정도",
                    ""
                ),
                "빈도": row.get(
                    f"{part}_빈도",
                    ""
                ),
                "최근1주증상": row.get(
                    f"{part}_최근1주증상",
                    ""
                ),
                "치료경험": row.get(
                    f"{part}_치료경험",
                    ""
                )
            })


        detail_df = pd.DataFrame(
            detail_data
        )


        st.dataframe(
            detail_df,
            width="stretch",
            hide_index=True
        )


        st.write(
            "### 증상 상세"
        )


        for part in body_parts:

            judgment = row.get(
                f"{part}_판정",
                "정상"
            )


            with st.expander(
                f"{part} - {judgment}"
            ):

                if judgment == "정상":

                    st.success(
                        "특이 증상 없음"
                    )


                else:

                    st.write(
                        "**지속기간:**",
                        row.get(
                            f"{part}_지속기간",
                            ""
                        )
                    )


                    st.write(
                        "**증상정도:**",
                        row.get(
                            f"{part}_증상정도",
                            ""
                        )
                    )


                    st.write(
                        "**발생빈도:**",
                        row.get(
                            f"{part}_빈도",
                            ""
                        )
                    )


                    st.write(
                        "**최근 1주 증상:**",
                        row.get(
                            f"{part}_최근1주증상",
                            ""
                        )
                    )


                    st.write(
                        "**치료경험:**",
                        row.get(
                            f"{part}_치료경험",
                            ""
                        )
                    )


st.divider()


# =========================================================
# Excel 다운로드
# =========================================================

st.subheader("📥 Excel 보고자료 다운로드")


def make_excel_file():

    output = BytesIO()


    with pd.ExcelWriter(
        output,
        engine="openpyxl"
    ) as writer:


        df.to_excel(
            writer,
            sheet_name="전체응답",
            index=False
        )


        symptom_summary_df.to_excel(
            writer,
            sheet_name="신체부위증상현황",
            index=False
        )


        part_summary_df.to_excel(
            writer,
            sheet_name="신체부위판정현황",
            index=False
        )


        if len(
            department_summary_df
        ) > 0:

            department_summary_df.to_excel(
                writer,
                sheet_name="부서별현황",
                index=False
            )


        if len(
            target_df
        ) > 0:

            target_df.to_excel(
                writer,
                sheet_name="관리대상자",
                index=False
            )


    output.seek(0)

    return output


try:

    excel_file = (
        make_excel_file()
    )


    st.download_button(
        label="📊 Excel 결과보고서 다운로드",
        data=excel_file,
        file_name=(
            "근골격계_증상조사_결과.xlsx"
        ),
        mime=(
            "application/vnd.openxmlformats-"
            "officedocument.spreadsheetml.sheet"
        ),
        width="stretch"
    )


except Exception as e:

    st.error(
        f"Excel 생성 중 오류가 발생했습니다: {e}"
    )
